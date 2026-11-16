"""Bounded Linux RR candidate check and manifest export; never starts a formal service."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PYTHON = '/home/alalapi/Runtimes/wechat-article-scheduler/.venv/bin/python'
BROWSER_TEMP = Path('/home/alalapi/Temp/rr-was-ui-20261022')


def main():
    if ROOT.name != 'rr-source-candidate-20261022' or ROOT.parent.name != 'artifacts':
        raise SystemExit('Use the explicitly registered isolated candidate, not the shared source tree.')
    os.umask(0o077)
    evidence = ROOT / 'evidence'
    evidence.mkdir(exist_ok=True)
    if sys.executable != PYTHON:
        os.execve(PYTHON, [PYTHON, '-I', '-B', str(Path(__file__).resolve())], {
            'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
    assert BROWSER_TEMP.is_dir() and not BROWSER_TEMP.is_symlink()
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                   'TMPDIR': str(BROWSER_TEMP)}
    with tempfile.TemporaryDirectory(prefix='rr-was-', dir='/tmp') as temporary:
        command = [PYTHON, '-I', '-B', '-c',
                   'import sys,pytest;sys.path.insert(0,"src");raise SystemExit(pytest.main(sys.argv[1:]))',
                   '-q', '-p', 'no:cacheprovider', '--basetemp=' + temporary + '/checks',
                   '--junitxml=evidence/final-check.xml',
                   'tests/test_rr_review.py::test_same_process_http_b_parser_and_agent_cli',
                   'tests/test_rr_feedback_browser.py', 'tests/test_rr_agent_binding.py']
        result = subprocess.run(command, cwd=ROOT, env=environment, timeout=90)
        size = sum(p.stat().st_size for p in Path(temporary).rglob('*') if p.is_file())
        print(json.dumps({'test_exit': result.returncode, 'temporary_fixture_bytes': size,
                          'tmpfs_purpose': 'bounded small SQLite fixtures and Unix sockets; deleted on exit'}))
        if result.returncode:
            return result.returncode
        assert size < 5 * 1024 * 1024
    sys.path.insert(0, str(ROOT / 'src'))
    from wechat_article_scheduler.rr_review.fixture import create_fixture
    from wechat_article_scheduler.rr_review.protocol import canonical
    with tempfile.TemporaryDirectory(prefix='rr-manifest-', dir=evidence) as temporary:
        _, snapshot = create_fixture(Path(temporary) / 'public', ROOT)
        snapshot.current()
        (evidence / 'manifest.json').write_bytes(canonical(snapshot.manifest) + b'\n')
        (evidence / 'source-inputs.json').write_bytes(canonical(snapshot.inputs) + b'\n')
        for _, (_, _, data) in snapshot.output.items():
            assert len(data) < 65536
        print(json.dumps({'source': snapshot.source, 'resources': len(snapshot.output),
                          'manifest': str(evidence / 'manifest.json')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
