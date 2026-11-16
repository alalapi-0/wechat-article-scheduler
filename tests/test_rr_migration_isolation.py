"""Real SQLite regressions in new synthetic roots only; no native DB or service."""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.rr_review import fixture, native_runtime
from wechat_article_scheduler.rr_review.projection import PUBLIC_ARTICLES
from wechat_article_scheduler.rr_review.protocol import Refused


SOURCE = Path(__file__).resolve().parents[1]
PUBLISHED_VERSIONS = [f'{number:03d}' for number in range(1, 16)]
CANDIDATE_SHA256 = 'cd6f88bd1686036c82992bd069595b2eb1ce55c366c0fbd89e7d40171917c02a'


def track_connections(monkeypatch):
    original = db.connect
    opened = []

    def connect(path):
        connection = original(path)
        opened.append(connection)
        return connection

    monkeypatch.setattr(db, 'connect', connect)
    return opened, original


def assert_closed(connections):
    assert connections
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match='closed database'):
            connection.execute('SELECT 1')


def test_ordinary_init_keeps_candidate_schema_out_and_closes_connection(tmp_path, monkeypatch):
    opened, connect = track_connections(monkeypatch)
    path = tmp_path / 'ordinary.sqlite3'
    db.init_db(path)
    assert len(opened) == 1
    assert_closed(opened)
    with closing(connect(path)) as connection:
        versions = [row[0] for row in connection.execute('SELECT version FROM schema_migrations ORDER BY version')]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert versions == PUBLISHED_VERSIONS
    assert not tables & {'rr_feedback', 'rr_feedback_attachment'}


def test_ordinary_init_closes_connection_on_real_migration_failure(tmp_path, monkeypatch):
    migrations = tmp_path / 'invalid-migrations'
    migrations.mkdir()
    (migrations / '001_invalid.sql').write_text('CREATE TABLE incomplete(', encoding='utf-8')
    monkeypatch.setattr(db, 'MIGRATIONS_DIR', migrations)
    opened, _ = track_connections(monkeypatch)
    with pytest.raises(sqlite3.OperationalError):
        db.init_db(tmp_path / 'failed.sqlite3')
    assert len(opened) == 1
    assert_closed(opened)


def test_exclusive_fixture_explicitly_applies_candidate_and_closes_connections(tmp_path, monkeypatch):
    opened, connect = track_connections(monkeypatch)
    config, snapshot = fixture.create_fixture(tmp_path / 'public', SOURCE)
    assert len(opened) == 2
    assert_closed(opened)
    with closing(connect(config.database_path)) as connection:
        versions = [row[0] for row in connection.execute('SELECT version FROM schema_migrations ORDER BY version')]
        articles = [dict(row) for row in connection.execute('SELECT id,title,summary,body,status FROM articles ORDER BY id')]
        rr_tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE name LIKE 'rr_feedback%'")}
    assert versions == PUBLISHED_VERSIONS + ['016']
    assert rr_tables == {'rr_feedback', 'rr_feedback_attachment'}
    assert articles == PUBLIC_ARTICLES
    assert hashlib.sha256(fixture.CANDIDATE_MIGRATION.read_bytes()).hexdigest() == CANDIDATE_SHA256
    assert snapshot.inputs['src/wechat_article_scheduler/rr_review/candidate_migrations/016_rr_feedback.sql'] == CANDIDATE_SHA256


def test_repeated_fixture_root_is_refused_without_changing_contents(tmp_path, monkeypatch):
    root = tmp_path / 'public'
    config, _ = fixture.create_fixture(root, SOURCE)
    before = {path.name: (path.stat().st_ino, path.read_bytes()) for path in root.iterdir()}

    def forbidden_connect(_):
        pytest.fail('an existing root must be refused before opening its database')

    monkeypatch.setattr(db, 'connect', forbidden_connect)
    with pytest.raises(Refused) as error:
        fixture.create_fixture(root, SOURCE)
    assert error.value.code == 'new_fixture_required'
    assert {path.name: (path.stat().st_ino, path.read_bytes()) for path in root.iterdir()} == before
    assert config.database_path.name == 'synthetic.sqlite3'


def test_fixture_closes_connections_when_candidate_sql_fails(tmp_path, monkeypatch):
    candidate = tmp_path / 'invalid-candidate.sql'
    candidate.write_text('CREATE TABLE incomplete(', encoding='utf-8')
    monkeypatch.setattr(fixture, 'CANDIDATE_MIGRATION', candidate)
    opened, _ = track_connections(monkeypatch)
    with pytest.raises(sqlite3.OperationalError):
        fixture.create_fixture(tmp_path / 'public', SOURCE)
    assert len(opened) == 2
    assert_closed(opened)


def test_fixture_closes_connections_when_public_seed_is_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr(fixture, 'PUBLIC_ARTICLES', [PUBLIC_ARTICLES[0], PUBLIC_ARTICLES[0]])
    opened, _ = track_connections(monkeypatch)
    with pytest.raises(sqlite3.IntegrityError):
        fixture.create_fixture(tmp_path / 'public', SOURCE)
    assert len(opened) == 2
    assert_closed(opened)


def test_fixture_closes_connections_when_snapshot_source_is_missing(tmp_path, monkeypatch):
    opened, _ = track_connections(monkeypatch)
    with pytest.raises(FileNotFoundError):
        fixture.create_fixture(tmp_path / 'public', tmp_path / 'absent-source')
    assert len(opened) == 2
    assert_closed(opened)


def test_native_schema_readiness_requires_separate_candidate_adoption(tmp_path, monkeypatch):
    # Only these new test databases are read; never the native DATABASE default.
    monkeypatch.setattr(native_runtime, 'ROOT', SOURCE)
    ordinary = tmp_path / 'ordinary.sqlite3'
    db.init_db(ordinary)
    before = ordinary.read_bytes()
    assert native_runtime.schema_metadata(ordinary)['rr_schema_ready'] is False
    assert ordinary.read_bytes() == before
    config, _ = fixture.create_fixture(tmp_path / 'public', SOURCE)
    before = config.database_path.read_bytes()
    assert native_runtime.schema_metadata(config.database_path)['rr_schema_ready'] is True
    assert config.database_path.read_bytes() == before


def test_source_identity_disables_optional_git_locks_without_changing_caller_env(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    monkeypatch.setattr(native_runtime, 'ROOT', source)
    monkeypatch.setenv('GIT_OPTIONAL_LOCKS', '1')
    calls = []

    def git(args, **kwargs):
        calls.append((args, kwargs))
        return 'a' * 40 + '\n' if args[-2:] == ['rev-parse', 'HEAD'] else ''

    monkeypatch.setattr(native_runtime.subprocess, 'check_output', git)
    assert native_runtime.source_identity() == {'commit': 'a' * 40, 'dirty': False}
    assert len(calls) == 2
    assert all(kwargs['env']['GIT_OPTIONAL_LOCKS'] == '0' and kwargs['timeout'] == 3
               for _, kwargs in calls)
    assert os.environ['GIT_OPTIONAL_LOCKS'] == '1'
