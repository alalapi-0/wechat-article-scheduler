"""Faithful source-only test view; never copies user data or credentials."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

REPO = Path('/home/alalapi/Projects/wechat-article-scheduler')
TEMP = Path('/home/alalapi/Temp/wechat-article-scheduler')
CACHE = Path('/home/alalapi/Caches/wechat-article-scheduler')
PYTHON = Path('/home/alalapi/Runtimes/wechat-article-scheduler/.venv/bin/python')
CODE_DIRS = {'src', 'tests', 'scripts', 'docs', 'fixtures', 'migrations', 'deploy'}
FILES = {'AGENTS.md', 'README.md', 'project.yaml', 'hub.connection.yaml',
         'pyproject.toml', '.gitignore', '.env.example', 'config/rules.example.yaml',
         'configs/linux-runtime.json'}
PRIVATE_PLANS = {'docs/pch-rebuild-20261020/PLAN.md', 'docs/pch-rebuild-20261020/TASKS.json'}
CANDIDATE_SQL_MOVE = ('migrations/016_rr_feedback.sql',
                      'src/wechat_article_scheduler/rr_review/candidate_migrations/016_rr_feedback.sql')
EXPLICIT_SOURCE_FILES = ('scripts/linux_runtime_guard.py', 'configs/linux-runtime.json',
                        'scripts/test_linux_profile.py', CANDIDATE_SQL_MOVE[1],
                        'tests/test_rr_migration_isolation.py')
GATE = '''import socket, ipaddress, os
def local(address):
    host = address[0] if isinstance(address, tuple) else None
    if host == 'localhost': return True
    try: return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError): return False
def deny():
    with open(os.environ['TEST_NETWORK_DENIAL'], 'a') as f: f.write('denied\\n')
    raise PermissionError('test execution permits loopback connections only')
_connect, _connect_ex, _dns = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
def connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6) and not local(address): deny()
    return _connect(self, address)
def connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6) and not local(address): deny()
    return _connect_ex(self, address)
def dns(host, port, *a, **k):
    if host is not None and not local((host, port)): deny()
    return _dns(host, port, *a, **k)
socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, dns
'''

def run(label):
    from linux_runtime_guard import regular_bytes
    os.umask(0o077)
    git_env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=REPO, env=git_env).decode().split('\0')
    rows = []
    with tempfile.TemporaryDirectory(prefix='suite-', dir=TEMP) as directory:
        base = Path(directory); view = base / 'source'; view.mkdir()
        for name in tracked:
            if not name: continue
            if name in PRIVATE_PLANS: continue
            relative = Path(name)
            if relative.parts[0] not in CODE_DIRS and name not in FILES: continue
            source = REPO / relative
            if name == CANDIDATE_SQL_MOVE[0] and not os.path.lexists(source):
                # Admit this exact source relocation while the original private
                # index is retained. A missing published migration still fails.
                candidate = regular_bytes(REPO / CANDIDATE_SQL_MOVE[1])
                original = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=REPO, env=git_env)
                if candidate != original:
                    raise RuntimeError('candidate migration move changed the original SQL bytes')
                continue
            if not stat.S_ISREG(source.lstat().st_mode):
                raise RuntimeError('test view accepts regular code files only')
            target = view / relative; target.parent.mkdir(parents=True, exist_ok=True)
            payload = regular_bytes(source)
            target.write_bytes(payload); target.chmod(stat.S_IMODE(source.stat().st_mode))
            digest = hashlib.sha256(payload).hexdigest()
            assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
            rows.append([name, digest])
        # New task-owned code is explicitly admitted, never via repository traversal.
        for name in EXPLICIT_SOURCE_FILES:
            source = REPO / name
            if name not in tracked and source.is_file():
                target = view / name; target.parent.mkdir(parents=True, exist_ok=True)
                payload = regular_bytes(source)
                target.write_bytes(payload)
                rows.append([name, hashlib.sha256(payload).hexdigest()])
        bootstrap = base / 'bootstrap'; bootstrap.mkdir()
        (bootstrap / 'sitecustomize.py').write_text(GATE)
        denial = TEMP / (label + '-network-denials.txt')
        if denial.exists(): denial.unlink()
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
               'PYTHONPATH': str(bootstrap) + ':' + str(view / 'src'),
               'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'TMPDIR': str(base),
               'XDG_CACHE_HOME': str(CACHE), 'PLAYWRIGHT_BROWSERS_PATH': str(CACHE / 'browsers'),
               'TEST_NETWORK_DENIAL': str(denial)}
        report = TEMP / (label + '-pytest.xml'); log = TEMP / (label + '-pytest.txt')
        args = [str(PYTHON), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                '--basetemp', str(base / 'pytest'), '--junitxml', str(report)]
        with log.open('w') as output:
            result = subprocess.run(args, cwd=view, env=env, stdout=output, stderr=subprocess.STDOUT)
        (TEMP / (label + '-source-view.json')).write_text(json.dumps({
            'files': sorted(rows), 'environment': env, 'protected_files_copied': 0,
            'excluded_private_plans': sorted(PRIVATE_PLANS),
            'source_view': 'disposable; exact allowed source bytes; no original .env/rules/db/articles/storage',
            'network_gate': 'test-only Python loopback guard, inherited ordinary Python children; not kernel sandbox',
            'exit': result.returncode}, ensure_ascii=False, indent=2))
        print(json.dumps({'label': label, 'exit': result.returncode, 'files': len(rows),
                          'report': str(report), 'log': str(log),
                          'outward_attempts': len(denial.read_text().splitlines()) if denial.exists() else 0}))
        return result.returncode

if __name__ == '__main__':
    if sys.argv[1:] != ['current']:
        raise SystemExit('use: python3 -I -B scripts/test_linux_profile.py current')
    sys.path.insert(0, str(REPO / 'scripts'))
    from linux_runtime_guard import verify
    verify()
    raise SystemExit(run('current'))
