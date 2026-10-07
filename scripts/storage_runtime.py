"""Guarded Linux fixed-root mock profile; never load the legacy .env or database."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
REPO = Path('/home/alalapi/Projects/wechat-article-scheduler')
sys.path.insert(0, str(REPO / 'scripts'))
from linux_runtime_guard import verify, BASE as BASE_PYTHON
VOLUME = Path('/home/alalapi')
RUNTIME = VOLUME / 'Runtimes/wechat-article-scheduler'
DATA = VOLUME / 'ProjectData/wechat-article-scheduler/linux-local-profile'
CACHE = VOLUME / 'Caches/wechat-article-scheduler'
TEMP = VOLUME / 'Temp/wechat-article-scheduler'
PYTHON = RUNTIME / '.venv/bin/python'
SAFE_TESTS = [
    'tests/test_storage_runtime.py', 'tests/test_mock_adapter.py',
    'tests/test_migrations.py', 'tests/test_web_app.py::test_status_endpoint',
    'tests/test_web_app.py::test_articles_empty', 'tests/test_web_app.py::test_index_html',
]


def physical(path: Path) -> Path:
    """Reject aliases/foreign devices before using any registered external path."""
    path = Path(os.path.abspath(path))
    relative = path.relative_to(VOLUME)
    current = VOLUME
    device = VOLUME.stat().st_dev
    if VOLUME.is_symlink():
        raise RuntimeError('volume is a symlink')
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise RuntimeError('external path is a symlink')
        if current.exists() and current.stat().st_dev != device:
            raise RuntimeError('external path changed device')
        if current.is_file() and current.stat().st_nlink != 1:
            raise RuntimeError('external file is a hardlink')
    return path


def check(require_python: bool = True) -> None:
    for key in ('STORAGE_GOVERNANCE_BOOTSTRAP_FILE', 'STORAGE_GOVERNANCE_TEST_FIXTURE_DIR'):
        if key in os.environ:
            raise RuntimeError('Linux identity guard refused access: legacy fixture injection')
    verify(require_python=require_python)


def environment() -> dict[str, str]:
    return {
        'PATH': f'{PYTHON.parent}:/usr/bin:/bin:/usr/sbin:/sbin',
        'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'PYTHONPATH': str(REPO / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'TMPDIR': str(TEMP), 'XDG_CACHE_HOME': str(CACHE),
        'PIP_CACHE_DIR': str(CACHE / 'pip'), 'UV_CACHE_DIR': str(CACHE / 'uv'),
        'UV_OFFLINE': 'true', 'UV_PYTHON_DOWNLOADS': 'never',
        'WECHAT_MODE': 'mock', 'WEB_AUTO_RUN_DUE': 'false',
    }


def package_output_root() -> Path:
    from wechat_article_scheduler.external_agent.task_package import data_task_outbox_root
    return data_task_outbox_root()


def external_config():
    from wechat_article_scheduler.config import AppConfig
    root = physical(DATA / 'mock')
    # Only this new, explicitly selected profile is visited, not legacy state.
    if root.exists():
        for parent, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                physical(Path(parent) / name)
    root.mkdir(exist_ok=True)
    return AppConfig(
        root=root, database_path=root / 'data/app.sqlite3',
        inbox_dir=root / 'articles/inbox', rules_path=root / 'config/rules.yaml',
        wechat_mode='mock', schedule_window_days=7, scheduler_poll_seconds=60,
        max_articles_per_day=2, log_file=root / 'data/logs/app.log',
        log_max_bytes=1048576, log_backup_count=1, log_level='INFO', dry_run=True,
        max_job_retries=3, scheduler_claim_timeout_seconds=900,
        scheduler_lock_ttl_seconds=300, scheduler_misfire_grace_minutes=60,
        wechat_app_id='', wechat_app_secret='', wechat_default_thumb_path='',
        web_auto_run_due=False, web_host='127.0.0.1', web_port=8080, rules={},
        external_agent_task_export_enabled=False,
        external_agent_task_outbox=package_output_root(),
    )


def rebuild() -> int:
    """Reconstruct only an absent environment from registered compatible wheels."""
    if os.path.lexists(RUNTIME / '.venv'):
        raise RuntimeError('environment exists; refusing to overwrite it')
    import hashlib
    manifest = verify(require_python=False)
    wheels = []
    for name, digest in manifest['wheels'].items():
        if not name.endswith('.whl') or Path(name).name != name or '/' in name or '\\' in name:
            raise RuntimeError('invalid registered wheel name')
        source = physical(CACHE / 'wheels' / name)
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise RuntimeError('registered compatible wheel changed or missing')
        wheels.append(str(source))
    subprocess.run([str(BASE_PYTHON), '-I', '-B', '-m', 'venv',
                    str(RUNTIME / '.venv')], env=environment(), check=True)
    subprocess.run([str(PYTHON), '-I', '-B', '-m', 'pip', '--isolated', 'install',
                    '--no-index', '--no-cache-dir', *wheels], env=environment(), check=True)
    subprocess.run([str(PYTHON), '-I', '-B', '-m', 'pip', '--isolated', 'check'], env=environment(), check=True)
    # Re-registration after an explicit rebuild is local to this fixed manifest.
    from linux_runtime_guard import MANIFEST, chain
    manifest['venv_chain'] = chain(RUNTIME / '.venv')
    manifest['pyvenv_sha256'] = hashlib.sha256((RUNTIME / '.venv/pyvenv.cfg').read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
    verify()
    return 0


def main(args: list[str] | None = None) -> int:
    os.umask(0o077)
    args = list(sys.argv[1:] if args is None else args)
    action = args[0] if args else 'check'
    try:
        if os.environ.get('WECHAT_MODE', 'mock').strip().lower() != 'mock':
            raise RuntimeError('Linux profile permits mock mode only')
        check(require_python=action != 'rebuild')
        clean = environment()
        os.environ.clear()
        os.environ.update(clean)
        if action == 'check':
            print(json.dumps({'status': 'PASS', 'profile': 'linux_mock_no_legacy_state_load',
                              'runtime': str(PYTHON), 'legacy_state': 'untouched'}))
            return 0
        if action == 'rebuild':
            return rebuild()
        if action not in ('cli', 'test', 'contract'):
            raise RuntimeError('use check, cli, test, contract, or rebuild')
        if sys.prefix != str(RUNTIME / '.venv') or not sys.flags.isolated:
            os.execve(str(PYTHON), [str(PYTHON), '-I', '-B', str(REPO / 'scripts/storage_runtime.py'), *args], environment())
        sys.path.insert(0, str(REPO / 'src'))
        if action == 'cli':
            from wechat_article_scheduler.cli import main as cli_main
            return cli_main(args[1:], config=external_config())
        if action == 'contract':
            return subprocess.call([str(PYTHON), '-I', '-B', str(REPO / 'scripts/check_repo_contract.py')],
                                   cwd=REPO, env=environment())
        if len(args) != 1:
            raise RuntimeError('test runs the isolated storage/core selection only')
        with tempfile.TemporaryDirectory(prefix='pytest-', dir=TEMP) as temporary:
            return subprocess.call([str(PYTHON), '-B', '-m', 'pytest', '-q',
                                    '-p', 'no:cacheprovider', '--basetemp', temporary + '/run',
                                    *SAFE_TESTS], cwd=REPO, env=environment())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'wechat external runtime: {error}', file=sys.stderr)
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
