"""Bounded public-fixture checks. No native role, production DB or real Agent claim."""
import array
import asyncio
import base64
import copy
from dataclasses import replace
import fcntl
import io
import json
import os
from pathlib import Path
import socket
import stat
import sys
import threading
import time
import uuid

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.rr_review.fixture import create_fixture, PublicFixtureKey, PUBLIC_KEY
from wechat_article_scheduler.rr_review.identity import receive_key
from wechat_article_scheduler.rr_review.integration import attach_review
from wechat_article_scheduler.rr_review.projection import INDEX
from wechat_article_scheduler.rr_review.protocol import (ORIGIN, PROJECT, Refused, canonical, loads,
                                                        multipart, sha, validate)
from wechat_article_scheduler.rr_review.store import FeedbackStore
from wechat_article_scheduler.web.app import create_app

SOURCE = Path(__file__).resolve().parents[1]
B_ROOT = Path('/home/alalapi/Projects/desktop-tool/remote-project-review')


def submission(snapshot):
    resource = next(r for r in snapshot.manifest['resources'] if r['id'] == 'workbench')
    blob = '公开合成附件；不是用户文章或截图。'.encode()
    value = {'schema': 1, 'project_id': PROJECT, 'client_request_id': str(uuid.uuid4()), 'page_path': INDEX,
             'source': snapshot.source, 'resource': {k: resource[k] for k in ('id', 'sha256', 'mode', 'preview_version')},
             'description': '合成反馈：检查排期提示', 'expected': '显示演练说明', 'actual': '合成测试上下文',
             'steps': '进入工作台并查看队列', 'submitted_at': '2026-10-22T00:00:00Z',
             'attachments': [{'attachment_id': 'public-note', 'size': len(blob), 'sha256': sha(blob)}]}
    return value, blob


def encode(value, blob):
    body = (b'--rrfixture\r\nContent-Disposition: form-data; name="feedback"\r\n'
            b'Content-Type: application/json\r\n\r\n' + canonical(value) +
            b'\r\n--rrfixture\r\nContent-Disposition: form-data; name="attachment.0"; filename="note.txt"\r\n'
            b'Content-Type: text/plain\r\n\r\n' + blob + b'\r\n--rrfixture--\r\n')
    return body, 'multipart/form-data; boundary=rrfixture'


def test_schema_and_atomic_store(tmp_path):
    cfg, snapshot = create_fixture(tmp_path / 'public', SOURCE)
    value, blob = submission(snapshot)
    body, mime = encode(value, blob)
    parsed, parts = multipart(body, mime)
    attachments = validate(parsed, parts, snapshot.manifest)
    with db.connect(cfg.database_path) as connection:
        store = FeedbackStore(connection)
        status, receipt = store.submit('a' * 64, value, attachments)
        assert status == 201 and receipt['status'] == 'pending'
        assert store.submit('a' * 64, value, attachments)[0] == 200
        changed = dict(value, description='不同正文')
        with pytest.raises(Refused) as error:
            store.submit('a' * 64, changed, attachments)
        assert error.value.status == 409
        # Deliberate mid-transaction duplicate attachment PK failure must roll back the whole feedback.
        fresh = dict(value, client_request_id=str(uuid.uuid4()))
        with pytest.raises(Exception):
            store.submit('a' * 64, fresh, attachments + attachments)
        assert connection.execute('SELECT COUNT(*) FROM rr_feedback').fetchone()[0] == 1
        fid = receipt['feedback_id']
        with pytest.raises(Refused):
            store.get(fid, device='b' * 64)
        with pytest.raises(Refused):
            store.result(fid, {'revision': 1, 'description': 'premature', 'reference': ''})
    with db.connect(cfg.database_path) as connection:
        store = FeedbackStore(connection)
        assert store.by_request('a' * 64, value['client_request_id'])['feedback_id'] == fid
        assert store.attachment(fid, 'public-note')[0] == blob
        proof = {'revision': 1, 'body_sha256': receipt['body_sha256'],
                 'attachments': [{'attachment_id': 'public-note', 'sha256': sha(blob)}]}
        with pytest.raises(Refused):
            store.ack(fid, dict(proof, revision=2))
        assert store.ack(fid, proof)['status'] == 'agent_read'
        result = {'revision': 1, 'description': '合成验证完成，未执行业务指令', 'reference': 'synthetic-check'}
        done = store.result(fid, result)
        assert done['status'] == 'processed'
        assert store.ack(fid, proof)['status'] == 'processed'
        assert store.result(fid, result)['result'] == done['result']
    for invalid in (b'{"x":1,"x":2}', b'{"x":1.1}', b'{"x":NaN}', b'{"x":"\\ud800"}', b'\xff'):
        with pytest.raises(Refused):
            loads(invalid)
    for mutated in (dict(value, source=dict(snapshot.source, build_id='0'*64)),
                    dict(value, page_path='/api/articles'), dict(value, extra='unknown')):
        with pytest.raises(Refused):
            validate(mutated, {'attachment.0': (blob, 'text/plain')}, snapshot.manifest)
    with pytest.raises(Refused):
        multipart(body.replace(b'name="attachment.0"', b'name="attachment.1"') + body, mime)
    with pytest.raises(Refused) as error:
        multipart(b'x' * (2 * 1024 * 1024 + 32769), mime)
    assert error.value.status == 413
    with pytest.raises(Refused) as error:
        validate(value, {'attachment.0': (blob, 'image/png')}, snapshot.manifest)
    assert error.value.status == 415


def test_sealed_fd_public_provider(tmp_path, rr_socket_dir):
    directory = rr_socket_dir / 'p'
    directory.mkdir(mode=0o750)
    directory.chmod(0o750)
    owned_directory = directory.lstat()
    path = directory / 'key.sock'
    errors = []
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    thread = None
    owned_socket = None
    def provider():
        fd = readonly = -1
        try:
            client, _ = listener.accept()
            with client:
                assert client.recv(512) == canonical({'schema': 1, 'project_id': PROJECT, 'recipient_uid': 1000}) + b'\n'
                fd = os.memfd_create('rr-project-browser-key', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
                os.fchmod(fd, 0o400)
                os.write(fd, PUBLIC_KEY)
                fcntl.fcntl(fd, fcntl.F_ADD_SEALS, fcntl.F_SEAL_SEAL | fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK)
                readonly = os.open('/proc/self/fd/' + str(fd), os.O_RDONLY | os.O_CLOEXEC)
                client.sendmsg([canonical({'schema': 1, 'project_id': PROJECT, 'key_fd': True}) + b'\n'],
                               [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [readonly]))])
        except BaseException as error:
            errors.append(error)
        finally:
            for item in (fd, readonly):
                if item >= 0: os.close(item)
    try:
        listener.bind(str(path))
        owned_socket = path.lstat()
        path.chmod(0o660); listener.listen(1); listener.settimeout(5)
        thread = threading.Thread(target=provider)
        thread.start()
        assert receive_key(str(path), provider_uid=os.getuid(), provider_gid=os.getgid()) == PUBLIC_KEY
        assert directory.is_dir() and stat.S_ISSOCK(path.lstat().st_mode)
        with pytest.raises(Refused) as refused:
            receive_key(str(path))  # Real UID996 binding refuses this live UID1000 fixture.
        assert refused.value.code == 'key_supply_unavailable'
    finally:
        listener.close()
        if thread is not None:
            thread.join(6)
        if owned_socket is not None and (thread is None or not thread.is_alive()):
            current_directory = directory.lstat()
            assert stat.S_ISDIR(current_directory.st_mode)
            assert (current_directory.st_dev, current_directory.st_ino) == (
                owned_directory.st_dev, owned_directory.st_ino)
            current = path.lstat()
            assert stat.S_ISSOCK(current.st_mode)
            assert (current.st_dev, current.st_ino) == (owned_socket.st_dev, owned_socket.st_ino)
            path.unlink()
            directory.rmdir()
    assert not errors and not thread.is_alive()


def test_same_process_http_b_parser_and_agent_cli(tmp_path, rr_socket_dir):
    asyncio.run(scenario(tmp_path, rr_socket_dir))


async def scenario(tmp_path, rr_socket_dir):
    # B is read-only. Use its installed manifest parser, HMAC formatter and HTTP/1.1 parser.
    sys.path.insert(0, str(B_ROOT))
    from rr_review.registry import Registry
    from rr_review.pch_client import PchClient
    from rr_review.http_core import Peer
    cfg, snapshot = create_fixture(tmp_path / 'public', SOURCE)
    Registry._api_manifest(None, PROJECT, snapshot.manifest)
    directory = rr_socket_dir
    browser, agent = str(directory / 'browser.sock'), str(directory / 'agent.sock')
    app = create_app(cfg)
    attach_review(app, snapshot, PublicFixtureKey(), fixture_paths=(browser, agent))
    class FixtureClient(PchClient):
        async def _connect(self):
            # Only socket location/UID provisioning is replaced; B's real wire parser is unchanged.
            return await asyncio.open_unix_connection(browser, limit=16384)
    client = FixtureClient(lambda: PUBLIC_KEY, os.getgid(), asyncio.Semaphore(1),
                           manifest_source=lambda: snapshot.manifest, project_id=PROJECT)
    peer = Peer(PROJECT, 'rr-' + PROJECT + '.invalid', 'a' * 64, 'public-fixture',
                time.time() + 300, snapshot.current)
    async def request(method, path, body=b'', mime=None, mutate=None, same_assertion=None):
        challenge = await client._challenge(peer)
        auth = same_assertion or client._assertion(peer, method, path, body, challenge)
        if mutate:
            envelope = loads(base64.urlsafe_b64decode(auth + '=' * (-len(auth) % 4)))
            mutate(envelope)
            import hmac
            unsigned = {k: v for k, v in envelope.items() if k != 'mac'}
            envelope['mac'] = hmac.digest(PUBLIC_KEY, canonical(unsigned), 'sha256').hex()
            auth = base64.urlsafe_b64encode(canonical(envelope)).decode().rstrip('=')
        headers = {'X-PCH-RR-Auth': auth}
        if mime: headers['Content-Type'] = mime
        reply = await client._exchange(method, path, body, headers, 2097152, peer)
        return reply, auth
    async def cli(*args):
        boot = 'import sys,runpy;sys.path.insert(0,' + repr(str(SOURCE / 'src')) + ');runpy.run_module("wechat_article_scheduler.rr_review.agent_cli",run_name="__main__")'
        process = await asyncio.create_subprocess_exec(sys.executable, '-I', '-B', '-c', boot,
                                                      '--socket', agent, *args,
                                                      stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), 15)
            assert process.returncode == 0, stderr.decode()
            return loads(stdout)
        finally:
            if process.returncode is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(process.wait(), 3)
                except asyncio.TimeoutError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    await process.wait()
            else:
                await process.wait()
    async with app.router.lifespan_context(app):
        for path, (_, mime, data) in snapshot.output.items():
            reply, auth = await request('GET', path)
            assert reply.status == 200 and reply.body == data and reply.headers['content-type'] == mime
            assert sha(reply.body) == next(r['sha256'] for r in snapshot.manifest['resources'] if r['id'] == snapshot.output[path][0])
        reply, _ = await request('GET', '/__rr/v1/data/workbench')
        assert loads(reply.body)['source'] == snapshot.source and b'source_path' not in reply.body
        for path in ('/', '/api/articles', '/api/admin', '/__rr-agent/v1/feedback', '/__rr/v1/feedback/unknown/events'):
            reply, _ = await request('GET', path)
            assert reply.status == 404
        for mutation in (lambda e: e.update(origin='https://wrong.invalid'),
                         lambda e: e.update(project_id='personal-control-hub'),
                         lambda e: e.update(device_sha256='invalid')):
            reply, _ = await request('GET', INDEX, mutate=mutation)
            assert reply.status == 404
        reply, auth = await request('GET', INDEX)
        reply, _ = await request('GET', INDEX, same_assertion=auth)
        assert reply.status == 404
        value, blob = submission(snapshot)
        body, mime = encode(value, blob)
        reply, _ = await request('POST', '/__rr/v1/feedback', body, mime)
        assert reply.status == 201
        receipt = loads(reply.body); fid = receipt['feedback_id']
        reply, _ = await request('POST', '/__rr/v1/feedback', body, mime)
        assert reply.status == 200 and loads(reply.body)['feedback_id'] == fid
        other, mime = encode(dict(value, actual='changed'), blob)
        reply, _ = await request('POST', '/__rr/v1/feedback', other, mime)
        assert reply.status == 409
        reply, _ = await request('GET', '/__rr/v1/feedback/by-request/' + value['client_request_id'])
        assert loads(reply.body)['status'] == 'pending'
        reply, _ = await request('GET', '/__rr/v1/feedback/' + fid, mutate=lambda e: e.update(device_sha256='b'*64))
        assert reply.status == 404
        read = await cli('read', fid)
        assert read['source'] == snapshot.source and read['description'] == value['description']
        assert base64.b64decode(read['attachment_bytes'][0]['base64']) == blob
        assert (await cli('list'))['items'][0]['feedback_id'] == fid
        assert (await cli('ack', fid))['status'] == 'agent_read'
        assert (await cli('result', fid, '--revision', '1', '--description', '合成流程验证完成',
                          '--reference', 'public-fixture'))['status'] == 'processed'
        reply, _ = await request('GET', '/__rr/v1/feedback/' + fid)
        assert loads(reply.body)['result']['description'] == '合成流程验证完成'
        # Real peer UID check in the project handler rejects the same test caller after binding changes.
        app.state.rr_review.browser_uid = 996
        with pytest.raises(Exception):
            await client._challenge(peer)
        app.state.rr_review.browser_uid = os.getuid()
        # Fail closed on source change without modifying source: alter the registered expected digest.
        original = snapshot.inputs.copy()
        snapshot.inputs['pyproject.toml'] = '0'*64
        reply = await client._exchange('GET', INDEX, b'', {}, 4096,
                                       replace(peer, current=lambda: None))
        assert reply.status == 503
        snapshot.inputs = original
    assert not Path(browser).exists() and not Path(agent).exists()
    assert not app.state.rr_review.tasks
    # Same database persists the exact ID, content and processed result after the process hook closes.
    with db.connect(cfg.database_path) as connection:
        assert FeedbackStore(connection).get(fid)['status'] == 'processed'
