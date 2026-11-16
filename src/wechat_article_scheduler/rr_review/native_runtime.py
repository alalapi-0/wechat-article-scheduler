"""Current-instance RR launch preparation. No fixtures, migrations or secret output.

inspect reads schema metadata only. serve is for a later explicit serialized
handoff after native installation, schema adoption and article selection.
"""
import asyncio
import fcntl
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
import subprocess
import sys
import time

from .identity import AGENT_SOCKET, BROWSER_SOCKET, KEY_SOCKET, NativeKey, SupplyNotReady, physical
from .protocol import PROJECT, ORIGIN, Refused, canonical, exact, loads, need

ROOT = Path('/home/alalapi/Projects/wechat-article-scheduler')
DATABASE = Path('/home/alalapi/ProjectData/wechat-article-scheduler/linux-local-profile/mock/data/app.sqlite3')
PREPARATION = ROOT / 'artifacts/rr-native-preparation'
SELECTION = PREPARATION / 'selection.json'
REQUIRED = {
    'rr_feedback': {'feedback_id', 'device', 'client_request_id', 'revision', 'payload_json', 'payload_sha256',
                    'body_sha256', 'accepted_at', 'status', 'ack_json', 'result_json'},
    'rr_feedback_attachment': {'feedback_id', 'attachment_id', 'content_type', 'sha256', 'data'},
}
STARTUP_DELAYS = (1, 2, 4, 8)  # Five total attempts in one process; no service restart loop.


class ClockGuard:
    """Supplement provider leases; bracket reads with only 1us clock quantization allowance."""
    def __init__(self, wall=time.time, monotonic=time.monotonic):
        self.wall, self.monotonic = wall, monotonic
        self.previous = self.sample()

    def sample(self):
        before = self.monotonic()
        wall = self.wall()
        return wall, before, self.monotonic()

    def check(self):
        wall, before, after = self.sample()
        previous_wall, _, previous_after = self.previous
        need(after >= before >= previous_after and wall >= previous_wall and
             wall - previous_wall + 0.000001 >= before - previous_after, 503, 'clock_rollback')
        self.previous = wall, before, after


async def acquire_startup(*, inspect_fn=None, key_factory=None, sleep=asyncio.sleep, clock=None):
    """No listeners, write DB handles or key retries after the first valid identity."""
    inspect_fn = inspect if inspect_fn is None else inspect_fn
    key_factory = NativeKey if key_factory is None else key_factory
    clock = ClockGuard() if clock is None else clock
    for attempt in range(len(STARTUP_DELAYS) + 1):
        clock.check()
        report = inspect_fn()  # Config/schema/handoff/source failures are never transient.
        permanent = set(report['remaining']) - {'native_batch_not_ready'}
        need(not permanent, 503, 'native_or_schema_or_selection_not_ready')
        try:
            unready = [item for item in report['native'].values() if not item['ready']]
            if unready:
                need(all(item.get('transient') is True for item in unready), 503, 'native_identity_invalid')
                raise SupplyNotReady()
            key = key_factory()  # Only SupplyNotReady can be retried; invalid peer/FD/EOF/timeout cannot.
            try:
                clock.check()
            except BaseException:
                key.close()
                raise
            return report, key
        except SupplyNotReady:
            if attempt == len(STARTUP_DELAYS):
                raise Refused(503, 'startup_supply_attempts_exhausted') from None
            await sleep(STARTUP_DELAYS[attempt])


async def guard_running(snapshot, key, expected_source, server, clock, *, sleep=asyncio.sleep, source_fn=None):
    """Extend the existing source guard; any live failure closes, never reacquires/retries."""
    source_fn = source_identity if source_fn is None else source_fn
    while not server.should_exit:
        await sleep(1)
        if server.should_exit:
            return
        try:
            snapshot.current()
            clock.check()
            key.value()
            need(source_fn() == expected_source, 503, 'source_identity_changed')
        except Exception:
            server.should_exit = True
            return


def source_identity():
    physical(ROOT)
    info = ROOT.stat()
    need(info.st_uid == 1000 and not stat.S_IMODE(info.st_mode) & 0o022, 503, 'source_root_invalid')
    git_environment = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    try:
        commit = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True, timeout=3,
                                         env=git_environment).strip()
        dirty = bool(subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'status', '--porcelain'], text=True, timeout=3,
                                             env=git_environment))
    except subprocess.TimeoutExpired:
        raise Refused(503, 'source_git_timeout') from None
    return {'commit': commit, 'dirty': dirty}


def schema_metadata(path=DATABASE):
    physical(path)
    info = path.stat()
    need(info.st_uid == 1000 and info.st_nlink == 1 and stat.S_ISREG(info.st_mode), 503, 'database_identity')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
    try:
        versions = [r[0] for r in connection.execute('SELECT version FROM schema_migrations ORDER BY version')]
        columns = {name: [r[1] for r in connection.execute('PRAGMA table_info(' + name + ')')] for name in REQUIRED}
        expected_versions = [p.stem.split('_', 1)[0] for p in sorted((ROOT / 'migrations').glob('*.sql'))]
        # Candidate 016 is adopted separately; inspection never applies it.
        expected_versions.append('016')
        ready = '016' in versions and versions == expected_versions and all(set(columns[n]) == REQUIRED[n] for n in REQUIRED)
        return {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
                'mode': oct(stat.S_IMODE(info.st_mode)), 'size': info.st_size,
                'migration_versions': versions, 'rr_columns': columns, 'rr_schema_ready': ready}
    finally:
        connection.close()


def selected_ids(metadata):
    physical(SELECTION)
    parent = SELECTION.parent.stat()
    info = SELECTION.stat()
    need(parent.st_uid == 1000 and stat.S_IMODE(parent.st_mode) == 0o700 and
         info.st_uid == 1000 and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600 and
         0 < info.st_size <= 4096, 503, 'selection_identity')
    value = loads(SELECTION.read_bytes())
    exact(value, ('schema', 'project_id', 'database', 'device', 'inode', 'article_ids', 'process_handoff_confirmed'))
    ids = value['article_ids']
    need(type(value['schema']) is int and value['schema'] == 1 and value['project_id'] == PROJECT and
         value['database'] == str(DATABASE) and type(value['device']) is int and type(value['inode']) is int and
         (value['device'], value['inode']) == (metadata['device'], metadata['inode']) and
         type(value['process_handoff_confirmed']) is bool and type(ids) is list and 0 <= len(ids) <= 20 and
         all(type(i) is int and i > 0 for i in ids) and len(set(ids)) == len(ids), 503, 'explicit_selection_required')
    return tuple(ids)


def native_metadata():
    result = {}
    for label, path, uid, gid, mode in (
        ('provider_directory', str(Path(KEY_SOCKET).parent), 996, 984, 0o750),
        ('provider_socket', KEY_SOCKET, 996, 984, 0o660),
        ('project_directory', str(Path(BROWSER_SOCKET).parent), 1000, 984, 0o2750),
    ):
        try:
            p = physical(path); item = p.lstat()
            valid_kind = stat.S_ISSOCK(item.st_mode) if label.endswith('socket') else stat.S_ISDIR(item.st_mode)
            result[label] = {'ready': valid_kind and (item.st_uid, item.st_gid, stat.S_IMODE(item.st_mode)) == (uid, gid, mode),
                             'uid': item.st_uid, 'gid': item.st_gid, 'mode': oct(stat.S_IMODE(item.st_mode))}
        except FileNotFoundError:
            result[label] = {'ready': False, 'reason': 'not_yet_present', 'transient': True}
        except (OSError, Refused):
            result[label] = {'ready': False, 'reason': 'identity_or_access_refused', 'transient': False}
    return result


def inspect():
    need(os.getuid() == 1000 and Path(__file__).resolve().parents[3] == ROOT, 503, 'owner_source_binding')
    source = source_identity()
    metadata = schema_metadata()
    native = native_metadata()
    reasons = []
    if not metadata['rr_schema_ready']: reasons.append('current_database_missing_rr_schema_016')
    try:
        ids = selected_ids(metadata)
        selected = {'ready': True, 'article_ids': list(ids),
                    'process_handoff_confirmed': loads(SELECTION.read_bytes())['process_handoff_confirmed']}
        if not selected['process_handoff_confirmed']: reasons.append('original_process_handoff_pending')
    except (OSError, Refused):
        selected = {'ready': False, 'path': str(SELECTION)}
        reasons.append('explicit_current_article_selection_and_process_handoff_missing')
    if not all(x['ready'] for x in native.values()): reasons.append('native_batch_not_ready')
    if os.path.lexists(BROWSER_SOCKET) or os.path.lexists(AGENT_SOCKET): reasons.append('existing_rr_socket_requires_owner_reconciliation')
    return {'schema': 1, 'project_id': PROJECT, 'origin': ORIGIN, 'source': source, 'database': metadata,
            'selection': selected, 'native': native, 'ready': not reasons, 'remaining': reasons,
            'credential_values_read': False, 'business_rows_read': False, 'effects': False}


def current_config():
    from wechat_article_scheduler.config import AppConfig
    profile = DATABASE.parents[1]
    return AppConfig(root=profile, database_path=DATABASE, inbox_dir=profile / 'articles/inbox',
        rules_path=profile / 'config/rules.yaml', wechat_mode='mock', schedule_window_days=7,
        scheduler_poll_seconds=60, max_articles_per_day=2, log_file=None, log_max_bytes=1048576,
        log_backup_count=1, log_level='INFO', dry_run=True, max_job_retries=3,
        scheduler_claim_timeout_seconds=900, scheduler_lock_ttl_seconds=300, scheduler_misfire_grace_minutes=60,
        wechat_app_id='', wechat_app_secret='', wechat_default_thumb_path='', web_auto_run_due=False,
        web_host='127.0.0.1', web_port=8080, rules={}, external_agent_task_export_enabled=False)


def prepare_manifest():
    """Read only the explicitly selected current instance; no app startup or schema writes."""
    from .projection import Snapshot
    metadata = schema_metadata()
    identity = source_identity()
    ids = selected_ids(metadata)
    connection = sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        snapshot = Snapshot(current_config(), connection, source_root=ROOT, commit=identity['commit'],
                            selected_article_ids=ids, synthetic_instance=None, current_profile=True)
    finally:
        connection.close()
    snapshot.source['dirty'] = identity['dirty']
    snapshot.current()
    return snapshot


async def serve():
    # Existing workbench ownership must first be handed off by its maintainer.
    # Reserve its exact loopback endpoint before opening a write connection.
    listener = None
    key = None
    lock = -1
    try:
        clock = ClockGuard()
        report, key = await acquire_startup(clock=clock)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('127.0.0.1', 8080)); listener.listen(128); listener.setblocking(False)
        lock = os.open(PREPARATION / 'process.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ids = selected_ids(report['database'])
        from .projection import Snapshot
        from .integration import attach_review
        from wechat_article_scheduler.web.app import create_app
        connection = sqlite3.connect(DATABASE.as_uri() + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            snapshot = Snapshot(current_config(), connection, source_root=ROOT, commit=report['source']['commit'],
                                selected_article_ids=ids, synthetic_instance=None, current_profile=True)
        finally:
            connection.close()
        snapshot.source['dirty'] = report['source']['dirty']
        key.value()  # Revalidate before any App initialization; no retries after acquisition.
        target = PREPARATION / 'last-prepared-manifest.json'
        if os.path.lexists(target):
            physical(target)
            need(target.stat().st_uid == 1000 and target.stat().st_nlink == 1 and
                 loads(target.read_bytes()).get('project_id') == PROJECT, 503, 'manifest_target_identity')
        target.write_bytes(canonical(snapshot.manifest) + b'\n')
        app = create_app(current_config())  # All versions, including 016, must already be present.
        attach_review(app, snapshot, key)
        # This is the original FastAPI process, also serving the local workbench.
        # The RR gateway still receives only its fixed Unix allowlist, never 8080.
        import uvicorn
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8080, access_log=False, log_level='warning'))
        task = asyncio.create_task(guard_running(snapshot, key, report['source'], server, clock))
        try:
            await server.serve(sockets=[listener])
        finally:
            server.should_exit = True
            await task
    finally:
        if listener is not None: listener.close()
        if key is not None: key.close()
        if lock >= 0: os.close(lock)


def main(argv=None):
    os.umask(0o077)
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ['inspect']:
            print(canonical(inspect()).decode()); return 0
        if args[:1] == ['agent']:
            from .agent_cli import main as agent_main
            return agent_main(args[1:])
        if args == ['manifest']:
            print(canonical(prepare_manifest().manifest).decode()); return 0
        if args == ['serve']:
            asyncio.run(serve()); return 0
        raise Refused(400, 'use_inspect_manifest_serve_or_agent')
    except (OSError, Refused, sqlite3.Error):
        print('{"error":"rr_current_instance_not_ready"}'); return 78


if __name__ == '__main__':
    raise SystemExit(main())
