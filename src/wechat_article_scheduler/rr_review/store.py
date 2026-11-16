"""Feedback uses the owning project's SQLite connection and transactions only."""
import json
import uuid
from datetime import datetime, timezone

from .protocol import Refused, canonical, exact, need, sha, text


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


class FeedbackStore:
    def __init__(self, connection):
        self.conn = connection  # Borrowed; no path, migration, new DB or worker process.
        need(not connection.in_transaction, 503, 'project_transaction_busy')
        connection.execute('SELECT feedback_id FROM rr_feedback LIMIT 0')

    def by_request(self, device, request_id):
        row = self.conn.execute('SELECT feedback_id FROM rr_feedback WHERE device=? AND client_request_id=?',
                                (device, request_id)).fetchone()
        need(row is not None, 404, 'unknown_feedback')
        return self.get(row['feedback_id'], device=device)

    def get(self, fid, *, device=None):
        row = self.conn.execute('SELECT * FROM rr_feedback WHERE feedback_id=?', (fid,)).fetchone()
        need(row is not None and (device is None or row['device'] == device), 404, 'unknown_feedback')
        value = json.loads(row['payload_json'])
        attachments = self.conn.execute(
            'SELECT attachment_id, content_type, sha256, length(data) AS size FROM rr_feedback_attachment '
            'WHERE feedback_id=? ORDER BY rowid', (fid,)).fetchall()
        return dict(value, feedback_id=fid, revision=row['revision'], accepted_at=row['accepted_at'],
                    payload_sha256=row['payload_sha256'], body_sha256=row['body_sha256'],
                    status=row['status'], attachments=[dict(a) for a in attachments],
                    ack=json.loads(row['ack_json']) if row['ack_json'] else None,
                    result=json.loads(row['result_json']) if row['result_json'] else None)

    def attachment(self, fid, aid, *, device=None):
        self.get(fid, device=device)
        row = self.conn.execute('SELECT data, content_type FROM rr_feedback_attachment '
                                'WHERE feedback_id=? AND attachment_id=?', (fid, aid)).fetchone()
        need(row is not None, 404, 'unknown_attachment')
        return bytes(row['data']), row['content_type']

    def submit(self, device, value, attachments):
        need(not self.conn.in_transaction, 503, 'project_transaction_busy')
        payload = canonical(value)
        digest = sha(payload)
        # body_sha256 identifies the exact canonical submitted JSON, not an HTTP status.
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            row = self.conn.execute('SELECT feedback_id, payload_sha256 FROM rr_feedback '
                                    'WHERE device=? AND client_request_id=?',
                                    (device, value['client_request_id'])).fetchone()
            if row:
                need(row['payload_sha256'] == digest, 409, 'idempotency_conflict')
                fid, status = row['feedback_id'], 200
            else:
                fid, status = str(uuid.uuid4()), 201
                self.conn.execute('INSERT INTO rr_feedback (feedback_id,device,client_request_id,payload_json,'
                                  'payload_sha256,body_sha256,accepted_at) VALUES (?,?,?,?,?,?,?)',
                                  (fid, device, value['client_request_id'], payload.decode(), digest, digest, now()))
                self.conn.executemany('INSERT INTO rr_feedback_attachment VALUES (?,?,?,?,?)',
                                      [(fid, *item) for item in attachments])
        return status, self.get(fid, device=device)

    def pending(self, *, state='pending', after='', limit=20):
        need(state in ('pending', 'agent_read', 'processed') and type(limit) is int and 1 <= limit <= 100)
        rows = self.conn.execute('SELECT feedback_id FROM rr_feedback WHERE status=? AND feedback_id>? '
                                'ORDER BY feedback_id LIMIT ?', (state, after, limit + 1)).fetchall()
        return {'items': [self.get(row['feedback_id']) for row in rows[:limit]],
                'next_cursor': rows[limit-1]['feedback_id'] if len(rows) > limit else None}

    def ack(self, fid, proof):
        exact(proof, ('revision', 'body_sha256', 'attachments'))
        need(not self.conn.in_transaction, 503, 'project_transaction_busy')
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            value = self.get(fid)
            expected = {'revision': value['revision'], 'body_sha256': value['body_sha256'],
                        'attachments': [{'attachment_id': a['attachment_id'], 'sha256': a['sha256']}
                                        for a in value['attachments']]}
            need(type(proof['revision']) is int and proof == expected, 409, 'revision_conflict')
            if value['ack'] is None:
                self.conn.execute("UPDATE rr_feedback SET status='agent_read', ack_json=? WHERE feedback_id=?",
                                  (canonical(dict(proof, read_at=now())).decode(), fid))
        return self.get(fid)

    def result(self, fid, result):
        exact(result, ('revision', 'description', 'reference'))
        text(result['description'], 6000, 1)
        text(result['reference'], 2000)
        need(not self.conn.in_transaction, 503, 'project_transaction_busy')
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            value = self.get(fid)
            need(type(result['revision']) is int and result['revision'] == value['revision'] and
                 value['ack'] is not None, 409, 'ack_required')
            if value['result'] is not None:
                need({k: value['result'][k] for k in result} == result, 409, 'result_conflict')
            else:
                self.conn.execute("UPDATE rr_feedback SET status='processed', result_json=? WHERE feedback_id=?",
                                  (canonical(dict(result, processed_at=now())).decode(), fid))
        return self.get(fid)
