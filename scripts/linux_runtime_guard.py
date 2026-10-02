"""Fixed-host Linux storage/toolchain admission; no user-data discovery."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess

REPO = Path('/home/alalapi/Projects/wechat-article-scheduler')
ROOTS = {key: Path('/home/alalapi') / key / 'wechat-article-scheduler'
         for key in ('Runtimes', 'Caches', 'Temp')}
ROOTS['ProjectData'] = Path('/home/alalapi/ProjectData/wechat-article-scheduler/linux-local-profile')
BASE = Path('/usr/bin/python3.12')
PYTHON = ROOTS['Runtimes'] / '.venv/bin/python'
MANIFEST = REPO / 'configs/linux-runtime.json'
FILESYSTEM = {'target': '/', 'source': '/dev/nvme0n1p3', 'fstype': 'ext4',
              'uuid': '9d258b70-f313-4a5d-9cf6-c715c5edca3d'}

def chain(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise RuntimeError('noncanonical path')
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY)
    result = []
    try:
        for part in ('/', *path.parts[1:]):
            if part != '/':
                new = os.open(part, os.O_PATH | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=fd)
                os.close(fd); fd = new
            s = os.fstat(fd)
            result.append([s.st_dev, s.st_ino, s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode)])
    finally:
        os.close(fd)
    return result

def regular_bytes(path):
    chain(Path(path).parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
            raise RuntimeError('nonregular or aliased toolchain file')
        with os.fdopen(fd, 'rb', closefd=False) as source:
            return source.read()
    finally:
        os.close(fd)

def verify(require_python=True):
    try:
        chain(REPO)
        data = json.loads(regular_bytes(MANIFEST))
        if data['version'] != 1 or data['repo'] != str(REPO):
            raise RuntimeError('unsupported repository binding')
        if data['roots'] != {k: str(p) for k, p in ROOTS.items()} or data['filesystem'] != FILESYSTEM:
            raise RuntimeError('unexpected root or filesystem declaration')
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
        for key, root in {'repo': REPO, **ROOTS}.items():
            if chain(root) != data['chains'][key]:
                raise RuntimeError('root identity changed: ' + key)
            actual = json.loads(subprocess.check_output(
                ['/usr/bin/findmnt', '--json', '--target', str(root), '--output',
                 'TARGET,SOURCE,FSTYPE,UUID'], env=env, text=True))['filesystems']
            if actual != [FILESYSTEM]:
                raise RuntimeError('unexpected mount: ' + key)
        if hashlib.sha256(regular_bytes(BASE)).hexdigest() != data['base_python_sha256']:
            raise RuntimeError('system interpreter changed')
        if require_python:
            venv = ROOTS['Runtimes'] / '.venv'
            if chain(venv) != data['venv_chain']:
                raise RuntimeError('virtual environment identity changed')
            chain(venv / 'bin'); chain(venv / 'lib/python3.12/site-packages')
            for name, target in data['python_links'].items():
                if os.readlink(venv / 'bin' / name) != target:
                    raise RuntimeError('interpreter link changed')
            if hashlib.sha256(regular_bytes(venv / 'pyvenv.cfg')).hexdigest() != data['pyvenv_sha256']:
                raise RuntimeError('virtual environment configuration changed')
            query = 'import importlib.metadata as m,json;print(json.dumps({x.metadata["Name"].lower().replace("_","-"):x.version for x in m.distributions()}))'
            packages = json.loads(subprocess.check_output([str(PYTHON), '-I', '-B', '-c', query], env=env, text=True))
            if packages != data['packages']:
                raise RuntimeError('dependency versions changed')
        return data
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, RuntimeError) as error:
        raise RuntimeError('Linux identity guard refused access: ' + str(error)) from error
