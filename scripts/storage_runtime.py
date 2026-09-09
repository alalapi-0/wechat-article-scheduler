"""Guarded external mock profile; never load the legacy .env or database."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
VOLUME = Path('/Volumes/AI_WORK_SSD')
GUARD = Path('/Users/alalapi/.config/storage-governance/guard.sh')
RUNTIME = VOLUME / 'Runtimes/wechat-article-scheduler'
DATA = VOLUME / 'ProjectData/wechat-article-scheduler'
CACHE = VOLUME / 'Caches/wechat-article-scheduler'
TEMP = VOLUME / 'Temp/wechat-article-scheduler'
BASE_PYTHON = VOLUME / 'Runtimes/uv-managed/data/python/cpython-3.11.15-macos-aarch64-none/bin/python3'
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
    return path


def check(require_python: bool = True) -> None:
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C'}
    # The common guard itself rejects unsupported fixture injection.
    for key in ('STORAGE_GOVERNANCE_BOOTSTRAP_FILE', 'STORAGE_GOVERNANCE_TEST_FIXTURE_DIR'):
        if key in os.environ:
            env[key] = os.environ[key]
    result = subprocess.run(['/bin/zsh', '-f', str(GUARD), '--check'], env=env,
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('external disk identity guard refused access')
    for root in (RUNTIME, DATA, CACHE, TEMP):
        physical(root)
        if not root.is_dir():
            raise RuntimeError('registered external root missing')
    if require_python:
        physical(RUNTIME / '.venv')
        physical(RUNTIME / '.venv/lib/python3.11/site-packages')
        if not PYTHON.is_file() or PYTHON.resolve() != BASE_PYTHON.resolve():
            raise RuntimeError('external interpreter missing or changed')


def environment() -> dict[str, str]:
    return {
        'PATH': f'{PYTHON.parent}:/usr/bin:/bin:/usr/sbin:/sbin',
        'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'PYTHONPATH': str(REPO / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'TMPDIR': str(TEMP), 'XDG_CACHE_HOME': str(CACHE),
        'PIP_CACHE_DIR': str(CACHE / 'pip'), 'UV_CACHE_DIR': str(VOLUME / 'Caches/uv'),
        'UV_OFFLINE': 'true', 'UV_PYTHON_DOWNLOADS': 'never',
        'WECHAT_MODE': 'mock', 'WEB_AUTO_RUN_DUE': 'false',
    }


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
        external_agent_task_outbox=root / 'outbox/wechat_agent_tasks',
    )


def rebuild() -> int:
    """Reconstruct an absent environment from the recorded local wheel payloads."""
    if (RUNTIME / '.venv').exists():
        raise RuntimeError('environment exists; refusing to overwrite it')
    manifest = json.loads((RUNTIME / 'offline_components.json').read_text())
    if manifest['python'] != str(BASE_PYTHON):
        raise RuntimeError('unexpected interpreter descriptor')
    sources = []
    for component in manifest['components']:
        source = physical(Path(component['source']))
        source.relative_to(VOLUME / 'Caches/uv/archive-v0')
        if not source.is_dir():
            raise RuntimeError('offline wheel payload missing; no download fallback')
        sources.append(source)
    subprocess.run([str(BASE_PYTHON), '-I', '-B', '-m', 'venv', '--without-pip',
                    str(RUNTIME / '.venv')], env=environment(), check=True)
    destination = RUNTIME / '.venv/lib/python3.11/site-packages'
    for source in sources:
        for child in source.iterdir():
            target = destination / child.name
            if target.exists():
                raise RuntimeError('overlapping offline package')
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)
    return 0


def main(args: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if args is None else args)
    action = args[0] if args else 'check'
    try:
        check(require_python=action != 'rebuild')
        if action == 'check':
            print(json.dumps({'status': 'PASS', 'profile': 'external_mock',
                              'runtime': str(PYTHON), 'legacy_state': 'untouched'}))
            return 0
        if action == 'rebuild':
            return rebuild()
        if action not in ('cli', 'test', 'contract'):
            raise RuntimeError('use check, cli, test, contract, or rebuild')
        if sys.prefix != str(RUNTIME / '.venv') or os.environ.get('PYTHONPATH') != str(REPO / 'src'):
            os.execve(str(PYTHON), [str(PYTHON), '-B', str(Path(__file__).resolve()), *args], environment())
        sys.path.insert(0, str(REPO / 'src'))
        if action == 'cli':
            from wechat_article_scheduler.cli import main as cli_main
            return cli_main(args[1:], config=external_config())
        if action == 'contract':
            return subprocess.call([str(PYTHON), '-B', str(REPO / 'scripts/check_repo_contract.py')],
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
