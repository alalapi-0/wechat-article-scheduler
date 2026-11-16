"""Bounded HTTP/1.1 over two Unix sockets, inside the original project process."""
import asyncio
import base64
from contextlib import suppress
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
import time

from .identity import AGENT_SOCKET, BROWSER_SOCKET, GATEWAY_GID, GATEWAY_UID, OWNER_UID, peer, physical
from .protocol import (HEX, MAX_BODY, OPAQUE, ORIGIN, PROJECT, Refused, canonical, exact,
                       loads, multipart, need, sha, uuid_string, validate)
from .store import FeedbackStore


class ReviewService:
    """No TCP listener, proxy, scheduler, config loader, DB migration or filesystem resource lookup."""
    def __init__(self, snapshot, connection, key, *, _fixture_paths=None):
        self.snapshot, self.store, self.key = snapshot, FeedbackStore(connection), key
        self.fixture = _fixture_paths is not None
        self.browser_path, self.agent_path = _fixture_paths or (BROWSER_SOCKET, AGENT_SOCKET)
        self.browser_uid = os.getuid() if self.fixture else GATEWAY_UID
        self.challenges, self.nonces, self.servers, self.tasks, self.owned = {}, {}, [], set(), {}
        self.slots = asyncio.Semaphore(8)
        self.closed = False

    async def start(self):
        try:
            for path, role in ((self.browser_path, 'browser'), (self.agent_path, 'agent')):
                path = physical(path)
                directory = path.parent.stat()
                expected = (os.getuid(), os.getgid(), 0o700) if self.fixture else (OWNER_UID, GATEWAY_GID, 0o750)
                need((directory.st_uid, directory.st_gid, stat.S_IMODE(directory.st_mode) & ~0o2000) == expected,
                     503, 'socket_directory_invalid')
                need(not os.path.lexists(path), 503, 'socket_exists')
                async def handler(reader, writer, role=role):
                    await self.client(reader, writer, role)
                server = await asyncio.start_unix_server(handler, path=str(path), limit=16385)
                self.servers.append(server)
                item = path.lstat()
                self.owned[str(path)] = (item.st_dev, item.st_ino)
                os.chmod(path, 0o660 if role == 'browser' and not self.fixture else 0o600)
                item = path.lstat()
                need(item.st_uid == os.getuid() and (self.fixture or item.st_gid == GATEWAY_GID),
                     503, 'socket_identity_invalid')
            return self
        except BaseException:
            await self.close()
            raise

    async def close(self):
        self.closed = True
        for server in self.servers:
            server.close()
            await server.wait_closed()
        for task in tuple(self.tasks):
            task.cancel()
        if self.tasks:
            await asyncio.gather(*tuple(self.tasks), return_exceptions=True)
        for path, identity in self.owned.items():
            with suppress(FileNotFoundError):
                item = Path(path).lstat()
                if (item.st_dev, item.st_ino) == identity:
                    Path(path).unlink()
        self.key.close()

    def browser_auth(self, identity, method, path, headers, body):
        token = headers.get('x-pch-rr-auth', '')
        need(0 < len(token) <= 4096 and re.fullmatch('[A-Za-z0-9_-]+', token), 404, 'identity_refused')
        try:
            raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
        except ValueError:
            raise Refused(404, 'identity_refused') from None
        envelope = loads(raw)
        exact(envelope, ('v', 'challenge', 'device_sha256', 'project_id', 'origin', 'method', 'path',
                         'body_sha256', 'nonce', 'issued_at', 'expires', 'mac'))
        need(type(envelope['mac']) is str and HEX.fullmatch(envelope['mac']), 404, 'identity_refused')
        unsigned = {k: v for k, v in envelope.items() if k != 'mac'}
        need(hmac.compare_digest(envelope['mac'], hmac.digest(self.key.value(), canonical(unsigned), 'sha256').hex()),
             404, 'identity_refused')
        now = int(time.time())
        self.challenges = {k: v for k, v in self.challenges.items() if v[1] > now}
        self.nonces = {k: v for k, v in self.nonces.items() if v > now}
        need(type(envelope['v']) is int and envelope['v'] == 1 and envelope['project_id'] == PROJECT and
             envelope['origin'] == ORIGIN and envelope['method'] == method and envelope['path'] == path and
             envelope['body_sha256'] == sha(body) and type(envelope['device_sha256']) is str and
             HEX.fullmatch(envelope['device_sha256']) and uuid_string(envelope['nonce']) and
             type(envelope['issued_at']) is int and type(envelope['expires']) is int and
             now - 30 <= envelope['issued_at'] <= now < envelope['expires'] <= envelope['issued_at'] + 30 and
             type(envelope['challenge']) is str and
             self.challenges.get(envelope['challenge'], (None, 0))[0] == identity and
             envelope['nonce'] not in self.nonces, 404, 'identity_refused')
        need(len(self.nonces) < 256, 503, 'identity_busy')
        self.challenges.pop(envelope['challenge'])
        self.nonces[envelope['nonce']] = envelope['expires']
        need(headers.get('origin', ORIGIN) == ORIGIN, 404, 'identity_refused')
        return envelope['device_sha256']

    async def client(self, reader, writer, role):
        task = asyncio.current_task()
        self.tasks.add(task)
        try:
            async with asyncio.timeout(12):
                async with self.slots:
                    pid, uid, gid = peer(writer.get_extra_info('socket'))
                    need(uid == (self.browser_uid if role == 'browser' else OWNER_UID) and
                         (self.fixture or role != 'browser' or gid == GATEWAY_GID), 404, 'identity_refused')
                    header = await reader.readuntil(b'\r\n\r\n')
                    need(len(header) <= 16384)
                    lines = header.decode('ascii', 'strict').split('\r\n')
                    first = lines[0].split(' ')
                    need(len(first) == 3 and first[2] == 'HTTP/1.1')
                    method, path = first[:2]
                    need(method in ('GET', 'POST') and path.startswith('/') and len(path) <= 1024 and
                         not any(c in path for c in ('?', '#', '%', '\\', '..')) and
                         all(33 <= ord(c) <= 126 for c in path), 404, 'unknown_route')
                    headers = {}
                    for line in lines[1:-2]:
                        name, sep, value = line.partition(':')
                        name = name.lower()
                        need(sep and re.fullmatch('[a-z0-9-]+', name) and name not in headers)
                        need(all(32 <= ord(c) < 127 for c in value))
                        headers[name] = value.strip(' ')
                    need(headers.get('host') == 'pch-rr.local' and 'transfer-encoding' not in headers)
                    need(not set(headers) & {'cookie', 'authorization', 'forwarded', 'x-forwarded-for', 'x-forwarded-host'},
                         404, 'identity_refused')
                    length = headers.get('content-length', '0')
                    need(re.fullmatch('[0-9]{1,8}', length))
                    need(int(length) <= MAX_BODY, 413, 'feedback_limit')
                    need(method == 'POST' or int(length) == 0)
                    body = await reader.readexactly(int(length))
                    self.snapshot.current()
                    if role == 'browser':
                        if method == 'GET' and path == '/__rr-local/v1/challenge':
                            self.key.value()
                            now = int(time.time())
                            self.challenges = {k: v for k, v in self.challenges.items() if v[1] > now}
                            need(len(self.challenges) < 256, 503, 'identity_busy')
                            challenge = secrets.token_hex(32)
                            self.challenges[challenge] = ((pid, uid, gid), now + 30)
                            response = (200, 'application/json', canonical({'challenge': challenge}))
                        else:
                            device = self.browser_auth((pid, uid, gid), method, path, headers, body)
                            response = self.browser(method, path, headers, body, device)
                    else:
                        response = self.agent(method, path, body)
                    await self.reply(writer, *response)
        except Refused as error:
            with suppress(Exception):
                await self.reply(writer, error.status, 'application/json', canonical({'error': error.code}))
        except (OSError, ValueError, UnicodeError, TimeoutError, asyncio.IncompleteReadError,
                asyncio.LimitOverrunError, RecursionError):
            with suppress(Exception):
                await self.reply(writer, 400, 'application/json', b'{"error":"invalid_request"}')
        except Exception:
            with suppress(Exception):
                await self.reply(writer, 503, 'application/json', b'{"error":"project_unavailable"}')
        finally:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
            self.tasks.discard(task)

    @staticmethod
    async def reply(writer, status, mime, data):
        names = {200: 'OK', 201: 'Created', 204: 'No Content', 400: 'Bad Request', 404: 'Not Found',
                 409: 'Conflict', 413: 'Content Too Large', 415: 'Unsupported Media Type', 503: 'Service Unavailable'}
        header = ('HTTP/1.1 ' + str(status) + ' ' + names.get(status, 'Error') + '\r\nContent-Type: ' + mime +
                  '\r\nContent-Length: ' + str(len(data)) + '\r\nCache-Control: no-store\r\n'
                  'X-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n').encode('ascii')
        writer.write(header + data)
        await writer.drain()

    def browser(self, method, path, headers, body, device):
        def json(value, status=200):
            return status, 'application/json', canonical(value)
        if method == 'GET' and path == '/__rr/v1/manifest':
            return json(self.snapshot.manifest)
        if method == 'GET' and path in self.snapshot.output:
            _, mime, data = self.snapshot.output[path]
            return 200, mime, data
        if method == 'GET' and path == '/__rr/v1/data/workbench':
            return json(self.snapshot.data())
        if method == 'POST' and path == '/__rr/v1/feedback':
            value, parts = multipart(body, headers.get('content-type', ''))
            attachments = validate(value, parts, self.snapshot.manifest)
            status, receipt = self.store.submit(device, value, attachments)
            return json(receipt, status)
        match = re.fullmatch(r'/__rr/v1/feedback/by-request/([a-f0-9-]{36})', path)
        if method == 'GET' and match:
            need(uuid_string(match[1]))
            return json(self.store.by_request(device, match[1]))
        match = re.fullmatch(r'/__rr/v1/feedback/([A-Za-z0-9_-]{1,128})(?:/attachments/([A-Za-z0-9_-]{1,128}))?', path)
        if method == 'GET' and match:
            if match[2]:
                data, mime = self.store.attachment(match[1], match[2], device=device)
                return 200, mime, data
            return json(self.store.get(match[1], device=device))
        raise Refused(404, 'unknown_route')

    def agent(self, method, path, body):
        prefix = '/__rr-agent/v1/feedback'
        if method == 'GET' and path == prefix:
            value = self.store.pending()
        elif method == 'POST' and path == prefix + '/list':
            query = loads(body)
            exact(query, ('state', 'after', 'limit'))
            need(type(query['after']) is str and (not query['after'] or uuid_string(query['after'])))
            value = self.store.pending(**query)
        else:
            match = re.fullmatch(prefix + r'/([A-Za-z0-9_-]{1,128})(?:/(ack|result|attachments/([A-Za-z0-9_-]{1,128})))?', path)
            need(match is not None, 404, 'unknown_route')
            if method == 'GET' and not match[2]:
                value = self.store.get(match[1])
            elif method == 'GET' and match[3]:
                data, mime = self.store.attachment(match[1], match[3])
                return 200, mime, data
            elif method == 'POST' and match[2] in ('ack', 'result'):
                value = getattr(self.store, match[2])(match[1], loads(body))
            else:
                raise Refused(404, 'unknown_route')
        return 200, 'application/json', canonical(value)
