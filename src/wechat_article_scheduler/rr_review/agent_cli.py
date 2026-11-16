"""Formal project CLI: Unix transport only; never opens the project database."""
import argparse
import base64
import http.client
import json
import os
from pathlib import Path
import socket
import stat

from .identity import AGENT_SOCKET, OWNER_UID, peer, physical
from .protocol import PROJECT, canonical, need, sha, uuid_string


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__('pch-rr.local', timeout=10)
        self.path = str(path)

    def connect(self):
        item = physical(self.path).lstat()
        need(stat.S_ISSOCK(item.st_mode) and item.st_uid == OWNER_UID and
             stat.S_IMODE(item.st_mode) == 0o600, 503, 'agent_socket_invalid')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)
        need(peer(self.sock)[1] == OWNER_UID, 503, 'agent_peer_invalid')


class AgentClient:
    def __init__(self, path=AGENT_SOCKET):
        need(os.getuid() == OWNER_UID, 503, 'owner_required')
        self.path = path

    @staticmethod
    def record(value, fid=None):
        need(type(value) is dict and type(value.get('schema')) is int and value['schema'] == 1 and
             value.get('project_id') == PROJECT and uuid_string(value.get('feedback_id')) and
             (fid is None or value['feedback_id'] == fid), 409, 'agent_object_binding')
        return value

    @classmethod
    def listing(cls, value):
        need(type(value) is dict and type(value.get('items')) is list and
             (value.get('next_cursor') is None or uuid_string(value['next_cursor'])), 409, 'agent_object_binding')
        for item in value['items']:
            cls.record(item)
        return value

    def request(self, method, path, value=None, *, raw=False):
        connection = UnixHTTP(self.path)
        try:
            body = b'' if value is None else canonical(value)
            connection.request(method, path, body, {'Content-Type': 'application/json'})
            response = connection.getresponse()
            need(response.status == 200, response.status, 'agent_request_refused')
            need(response.getheader('Transfer-Encoding') is None and
                 0 <= int(response.getheader('Content-Length', '-1')) <= 2097152, 503, 'agent_response_invalid')
            data = response.read(2097153)
            need(len(data) == int(response.getheader('Content-Length')), 503, 'agent_response_invalid')
            if raw:
                return data
            value = json.loads(data)
            prefix = '/__rr-agent/v1/feedback'
            if path in (prefix, prefix + '/list'):
                return self.listing(value)
            fid = path.removeprefix(prefix + '/').split('/')[0]
            need(uuid_string(fid), 409, 'agent_object_binding')
            return self.record(value, fid)
        finally:
            connection.close()

    def read(self, fid):
        need(uuid_string(fid))
        path = '/__rr-agent/v1/feedback/' + fid
        value = self.record(self.request('GET', path), fid)
        blobs = []
        for item in value['attachments']:
            data = self.request('GET', path + '/attachments/' + item['attachment_id'], raw=True)
            need(len(data) == item['size'] and sha(data) == item['sha256'], 409, 'attachment_changed')
            blobs.append({'attachment_id': item['attachment_id'], 'base64': base64.b64encode(data).decode('ascii')})
        # Verify the exact submitted JSON independently from the returned receipt digest.
        submitted = {k: value[k] for k in ('schema', 'client_request_id', 'project_id', 'page_path', 'source',
                                         'resource', 'description', 'expected', 'actual', 'steps', 'submitted_at')}
        submitted['attachments'] = [{k: a[k] for k in ('attachment_id', 'size', 'sha256')} for a in value['attachments']]
        need(sha(canonical(submitted)) == value['body_sha256'] == value['payload_sha256'], 409, 'body_changed')
        return value, blobs

    def ack(self, fid):
        value, _ = self.read(fid)  # Always fetch body, source, context and actual attachment bytes first.
        proof = {'revision': value['revision'], 'body_sha256': value['body_sha256'],
                 'attachments': [{k: a[k] for k in ('attachment_id', 'sha256')} for a in value['attachments']]}
        return self.record(self.request('POST', '/__rr-agent/v1/feedback/' + fid + '/ack', proof), fid)

    def result(self, fid, result):
        need(uuid_string(fid))
        return self.record(self.request('POST', '/__rr-agent/v1/feedback/' + fid + '/result', result), fid)


def main(argv=None):
    parser = argparse.ArgumentParser(description='原项目 RR 反馈 CLI（仅连接原项目 Agent Unix socket）')
    parser.add_argument('--socket', default=AGENT_SOCKET)
    commands = parser.add_subparsers(dest='command', required=True)
    listing = commands.add_parser('list')
    listing.add_argument('--state', choices=['pending', 'agent_read', 'processed'], default='pending')
    listing.add_argument('--after', default='')
    listing.add_argument('--limit', type=int, default=20)
    for name in ('read', 'ack', 'result'):
        command = commands.add_parser(name)
        command.add_argument('feedback_id')
        if name == 'result':
            command.add_argument('--revision', type=int, required=True)
            command.add_argument('--description', required=True)
            command.add_argument('--reference', default='')
    args = parser.parse_args(argv)
    from .protocol import Refused
    try:
        client = AgentClient(args.socket)
        if args.command == 'list':
            value = client.request('POST', '/__rr-agent/v1/feedback/list',
                                   {'state': args.state, 'after': args.after, 'limit': args.limit})
        elif args.command == 'read':
            value, blobs = client.read(args.feedback_id)
            value = dict(value, attachment_bytes=blobs)
        elif args.command == 'ack':
            value = client.ack(args.feedback_id)
        else:
            need(uuid_string(args.feedback_id))
            value = client.result(args.feedback_id,
                                  {'revision': args.revision, 'description': args.description, 'reference': args.reference})
        print(canonical(value).decode())
        return 0
    except (Refused, OSError, ValueError, http.client.HTTPException):
        print('{"error":"agent_request_refused"}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
