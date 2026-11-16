"""Public fixture factory. Exclusive new directory only; never loads environment/config."""
import os
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from .projection import PUBLIC_ARTICLES, Snapshot
from .protocol import need, sha

BASE_COMMIT = '844d37da80fd60cd6c1b62914f24070b4fef4f80'
PUBLIC_KEY = b'rr-public-fixture-key-never-production-20261022'
CANDIDATE_MIGRATION = Path(__file__).parent / 'candidate_migrations/016_rr_feedback.sql'


class PublicFixtureKey:
    def value(self):
        return PUBLIC_KEY

    def close(self):
        pass


def create_fixture(root, source_root):
    root = Path(root)
    need(root.is_absolute() and not os.path.lexists(root), 503, 'new_fixture_required')
    root.mkdir(mode=0o700)
    config = AppConfig(
        root=root, database_path=root / 'synthetic.sqlite3', inbox_dir=root / 'unused-inbox',
        rules_path=root / 'unused-rules.yaml', wechat_mode='mock', schedule_window_days=7,
        scheduler_poll_seconds=60, max_articles_per_day=2, log_file=None, log_max_bytes=1048576,
        log_backup_count=1, log_level='INFO', dry_run=True, max_job_retries=3,
        scheduler_claim_timeout_seconds=900, scheduler_lock_ttl_seconds=300, scheduler_misfire_grace_minutes=60,
        wechat_app_id='', wechat_app_secret='', wechat_default_thumb_path='', web_auto_run_due=False,
        web_host='127.0.0.1', web_port=8080, rules={}, external_agent_task_export_enabled=False)
    db.init_db(config.database_path)  # Ordinary published migrations, on a new synthetic DB only.
    connection = db.connect(config.database_path)
    try:
        # This exclusive fixture root is the only automatic candidate-schema entry.
        # Ordinary application initialization never discovers this SQL under src/.
        with connection:
            connection.executescript(CANDIDATE_MIGRATION.read_text(encoding='utf-8'))
            connection.execute('INSERT INTO schema_migrations(version) VALUES (?)', ('016',))
            for row in PUBLIC_ARTICLES:
                connection.execute('INSERT INTO articles(id,source_path,title,summary,body,status,content_hash) '
                                   'VALUES(?,?,?,?,?,?,?)', (row['id'], 'public-fixture-' + str(row['id']) + '.md',
                                                            row['title'], row['summary'], row['body'], row['status'], sha(row['body'].encode())))
            connection.execute("INSERT INTO publish_jobs(id,article_id,scheduled_at,status,adapter_mode) VALUES"
                               "(1,1,'2099-01-01T09:00:00','pending','mock'),(2,2,'2026-01-01T09:00:00','done','mock')")
            connection.execute("INSERT INTO wechat_drafts(article_id,media_id,status) VALUES(2,'mock_public_fixture','created')")
        snapshot = Snapshot(config, connection, source_root=source_root, commit=BASE_COMMIT,
                            selected_article_ids=(1, 2), synthetic_instance='rr-public-fixture-v1')
    finally:
        connection.close()
    return config, snapshot
