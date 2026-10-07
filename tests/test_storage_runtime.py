"""Storage entry tests: no legacy data, credentials, or real WeChat API."""
import importlib.util
from pathlib import Path
import subprocess
import sys


def runtime():
    path = Path(__file__).resolve().parents[1] / 'scripts/storage_runtime.py'
    spec = importlib.util.spec_from_file_location('wechat_storage_runtime_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_config_never_loads_legacy(monkeypatch, tmp_path):
    module = runtime()
    from wechat_article_scheduler import config
    monkeypatch.setattr(config, 'load_config', lambda *a, **k: (_ for _ in ()).throw(AssertionError('legacy')))
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, 'physical', lambda p: p)
    monkeypatch.setattr(module, 'package_output_root', lambda: tmp_path / 'task-packages')
    cfg = module.external_config()
    assert cfg.root == tmp_path / 'mock'
    assert cfg.database_path.is_relative_to(cfg.root)
    assert cfg.external_agent_task_outbox == tmp_path / 'task-packages'
    assert cfg.wechat_mode == 'mock' and cfg.dry_run
    assert not cfg.wechat_app_secret and not cfg.web_auto_run_due


def test_cli_accepts_injected_config_without_loader(monkeypatch, tmp_path, capsys):
    module = runtime()
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, 'physical', lambda p: p)
    monkeypatch.setattr(module, 'package_output_root', lambda: tmp_path / 'task-packages')
    from wechat_article_scheduler import cli
    monkeypatch.setattr(cli, 'load_config', lambda: (_ for _ in ()).throw(AssertionError('legacy')))
    assert cli.main(['init-db'], config=module.external_config()) == 0
    assert (tmp_path / 'mock/data/app.sqlite3').is_file()


def test_environment_does_not_inherit_secrets(monkeypatch):
    module = runtime()
    monkeypatch.setenv('WECHAT_APP_SECRET', 'synthetic-test-value')
    monkeypatch.setenv('WECHAT_MODE', 'real')
    env = module.environment()
    assert 'WECHAT_APP_SECRET' not in env and env['WECHAT_MODE'] == 'mock'
    assert env['TMPDIR'].startswith(str(module.VOLUME))


def test_missing_bootstrap_fails_before_runtime(tmp_path):
    module = runtime()
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
           'STORAGE_GOVERNANCE_BOOTSTRAP_FILE': str(tmp_path / 'missing.json')}
    result = subprocess.run([sys.executable, '-B', str(module.__file__), 'cli', '--help'],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 78
    assert 'identity guard refused' in result.stderr


def test_physical_rejects_symlink_and_escape(tmp_path, monkeypatch):
    module = runtime()
    monkeypatch.setattr(module, 'VOLUME', tmp_path)
    link = tmp_path / 'link'
    link.symlink_to(tmp_path / 'target')
    import pytest
    with pytest.raises(RuntimeError, match='symlink'):
        module.physical(link / 'data')
    with pytest.raises(ValueError):
        module.physical(tmp_path.parent / 'outside')


def test_linux_guard_rejects_real_alias_and_hardlink(tmp_path):
    module = runtime()
    import linux_runtime_guard as guard
    import pytest
    guard.verify()
    target = tmp_path / 'directory'
    target.mkdir()
    link = tmp_path / 'alias'
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError):
        guard.chain(link)
    source = tmp_path / 'single'
    source.write_bytes(b'synthetic')
    import os
    os.link(source, tmp_path / 'second-name')
    with pytest.raises(RuntimeError, match='aliased'):
        guard.regular_bytes(source)


def test_linux_guard_checks_actual_mount_and_rejects_wrong_identity(monkeypatch):
    module = runtime()
    import linux_runtime_guard as guard
    import pytest
    import json
    original = guard.subprocess.check_output
    guard.verify()
    assert module.package_output_root() == Path('/data/ProjectOutputs/wechat-article-scheduler/task-packages')
    def wrong_mount(args, **kwargs):
        if args[0] == '/usr/bin/findmnt':
            return json.dumps({'filesystems': [{**guard.FILESYSTEM, 'target': '/foreign'}]})
        return original(args, **kwargs)
    monkeypatch.setattr(guard.subprocess, 'check_output', wrong_mount)
    with pytest.raises(RuntimeError, match='unexpected mount'):
        guard.verify()
    with pytest.raises(RuntimeError, match='DATA output volume'):
        module.package_output_root()


def test_linux_entry_refuses_existing_rebuild_and_real_mode():
    module = runtime()
    script = module.REPO / 'scripts/storage_runtime.py'
    env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': '/nonexistent', 'WECHAT_MODE': 'mock'}
    result = subprocess.run([sys.executable, '-I', '-B', str(script), 'rebuild'],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 78 and 'refusing to overwrite' in result.stderr
    result = subprocess.run([sys.executable, '-I', '-B', str(script), 'cli', '--help'],
                            env={**env, 'WECHAT_MODE': 'real'}, capture_output=True, text=True)
    assert result.returncode == 78 and 'mock mode only' in result.stderr


def test_real_http_restart_external_fixture(tmp_path, monkeypatch):
    """Actual loopback server twice; persistent fixture DB, no browser or network API."""
    import json
    import socket
    import sqlite3
    import threading
    import time
    from urllib.request import urlopen
    import uvicorn
    from wechat_article_scheduler.web import create_app
    module = runtime()
    assert str(tmp_path).startswith(str(module.TEMP))
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, 'package_output_root', lambda: tmp_path / 'task-packages')
    cfg = module.external_config()
    for cycle in range(2):
        app = create_app(cfg)
        with sqlite3.connect(cfg.database_path) as connection:
            if cycle == 0:
                connection.execute('CREATE TABLE storage_restart_marker (value INTEGER)')
                connection.execute('INSERT INTO storage_restart_marker VALUES (42)')
            assert connection.execute('SELECT value FROM storage_restart_marker').fetchone() == (42,)
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', log_level='error'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]})
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started
            with urlopen(f'http://127.0.0.1:{port}/', timeout=5) as response:
                assert response.status == 200 and b'<html' in response.read().lower()
            with urlopen(f'http://127.0.0.1:{port}/api/status', timeout=5) as response:
                status = json.load(response)
                assert response.status == 200
                assert status['wechat_mode'] == 'mock'
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()
            assert not thread.is_alive()
