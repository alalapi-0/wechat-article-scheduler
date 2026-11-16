"""Strict public schema and multipart validation; errors never contain input."""
import hashlib
import io
import json
import re
import uuid
from datetime import datetime
from email.parser import BytesParser
from email.policy import default

PROJECT = 'wechat-article-scheduler'
ORIGIN = 'https://rr-wechat-article-scheduler.invalid:9419'
HEX = re.compile(r'[a-f0-9]{64}\Z')
OPAQUE = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
MAX_BODY = 2 * 1024 * 1024 + 32768


class Refused(Exception):
    def __init__(self, status=400, code='invalid_request'):
        self.status, self.code = status, code


def need(condition, status=400, code='invalid_request'):
    if not condition:
        raise Refused(status, code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8', 'strict')


def loads(data):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result)
            result[key] = value
        return result
    def reject(_):
        raise Refused()
    try:
        value = json.loads(data.decode('utf-8', 'strict'), object_pairs_hook=pairs,
                           parse_float=reject, parse_constant=reject)
        canonical(value)  # Reject unpaired UTF-16 surrogates, including keys.
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise Refused() from None


def exact(value, names):
    need(type(value) is dict and set(value) == set(names))


def uuid_string(value):
    try:
        return type(value) is str and str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def text(value, maximum, minimum=0):
    need(type(value) is str and minimum <= len(value) <= maximum and '\x00' not in value)


def image_type(data, content_type):
    if content_type == 'text/plain':
        try:
            data.decode('utf-8', 'strict')
        except UnicodeError:
            raise Refused(415, 'attachment_type') from None
        return
    from PIL import Image
    expected = {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'image/webp': 'WEBP'}
    need(content_type in expected, 415, 'attachment_type')
    try:
        with Image.open(io.BytesIO(data)) as image:
            need(image.format == expected[content_type] and image.width * image.height <= 16777216,
                 415, 'attachment_type')
            image.verify()
    except (OSError, ValueError, Image.DecompressionBombError):
        raise Refused(415, 'attachment_type') from None


def multipart(body, content_type):
    need(len(body) <= MAX_BODY, 413, 'feedback_limit')
    need(type(content_type) is str and re.fullmatch(
        r'multipart/form-data; *boundary=(?:[A-Za-z0-9_-]{1,70}|"[A-Za-z0-9_-]{1,70}")',
        content_type), 415, 'feedback_type')
    message = BytesParser(policy=default).parsebytes(
        b'Content-Type: ' + content_type.encode('ascii') + b'\r\nMIME-Version: 1.0\r\n\r\n' + body)
    need(message.is_multipart() and not message.defects)
    need(not (message.preamble or '').strip() and not (message.epilogue or '').strip())
    parts = {}
    for part in message.iter_parts():
        need(not part.is_multipart() and not part.defects)
        names = [name.lower() for name, _ in part.items()]
        need(len(names) == len(set(names)) and set(names) <= {'content-type', 'content-disposition'})
        need(part.get_content_disposition() == 'form-data')
        params = part.get_params(header='content-disposition')[1:]
        need(len(params) == len({name for name, _ in params}) and
             set(name for name, _ in params) <= {'name', 'filename'})
        name = part.get_param('name', header='content-disposition')
        need(name in ('feedback', 'attachment.0', 'attachment.1') and name not in parts)
        payload = part.get_payload(decode=True)
        need(type(payload) is bytes)
        need(len(payload) <= (16384 if name == 'feedback' else 1048576), 413, 'feedback_limit')
        parts[name] = (payload, part.get_content_type())
    need('feedback' in parts)
    value = loads(parts.pop('feedback')[0])
    return value, parts


def validate(value, parts, manifest):
    exact(value, ('schema', 'client_request_id', 'project_id', 'page_path', 'source', 'resource',
                  'description', 'expected', 'actual', 'steps', 'submitted_at', 'attachments'))
    need(type(value['schema']) is int and value['schema'] == 1 and
         value['project_id'] == PROJECT and uuid_string(value['client_request_id']))
    exact(value['source'], ('commit', 'build_id', 'dirty'))
    need(type(value['source']['dirty']) is bool)
    # A stale source cannot be silently rebound to this build.
    need(value['source'] == manifest['source'], 409, 'source_changed')
    pages = {r['path']: r['resource_id'] for r in manifest['routes']['pages']}
    need(type(value['page_path']) is str and value['page_path'] in pages)
    asset = next(r for r in manifest['resources'] if r['id'] == pages[value['page_path']])
    need(value['resource'] == {k: asset[k] for k in ('id', 'sha256', 'mode', 'preview_version')},
         409, 'resource_changed')
    for field in ('description', 'expected', 'actual', 'steps'):
        text(value[field], 6000, 1 if field == 'description' else 0)
    text(value['submitted_at'], 40, 20)
    try:
        need(value['submitted_at'].endswith('Z'))
        datetime.fromisoformat(value['submitted_at'].replace('Z', '+00:00'))
    except ValueError:
        raise Refused() from None
    entries = value['attachments']
    need(type(entries) is list and len(entries) <= 2 and len(entries) == len(parts))
    attachments = []
    seen = set()
    for index, entry in enumerate(entries):
        exact(entry, ('attachment_id', 'size', 'sha256'))
        aid = entry['attachment_id']
        need(type(aid) is str and OPAQUE.fullmatch(aid) and aid not in seen)
        seen.add(aid)
        need('attachment.' + str(index) in parts)
        data, mime = parts['attachment.' + str(index)]
        need(type(entry['size']) is int and entry['size'] == len(data) and entry['sha256'] == sha(data))
        image_type(data, mime)
        attachments.append((aid, mime, sha(data), data))
    return attachments
