"""Public success-response substitute: never connects to a socket or opens a DB."""
import copy
import uuid
import pytest

from wechat_article_scheduler.rr_review.agent_cli import AgentClient
from wechat_article_scheduler.rr_review.protocol import PROJECT, Refused, canonical, sha


def test_agent_rejects_cross_project_or_wrong_object():
    fid = str(uuid.uuid4())
    payload = {'schema': 1, 'project_id': 'another-project', 'client_request_id': str(uuid.uuid4()),
               'page_path': '/public-fixture', 'source': {'commit': 'a'*40, 'build_id': 'b'*64, 'dirty': True},
               'resource': {'id': 'public', 'sha256': 'c'*64, 'mode': 'readonly', 'preview_version': 'v1'},
               'description': 'public synthetic record', 'expected': '', 'actual': '', 'steps': '',
               'submitted_at': '2026-10-22T00:00:00Z', 'attachments': []}
    record = dict(payload, feedback_id=fid, body_sha256=sha(canonical(payload)), payload_sha256=sha(canonical(payload)))
    class PublicSubstitute(AgentClient):
        def request(self, *args, **kwargs): return copy.deepcopy(record)
    client = PublicSubstitute()
    with pytest.raises(Refused): client.read(fid)
    with pytest.raises(Refused): client.result(fid, {'revision': 1, 'description': 'public', 'reference': ''})
    with pytest.raises(Refused): AgentClient.listing({'items': [record], 'next_cursor': None})
    record['project_id'] = PROJECT
    record['feedback_id'] = str(uuid.uuid4())
    with pytest.raises(Refused): client.read(fid)
    with pytest.raises(Refused): client.result(fid, {})
    record['feedback_id'] = fid
    record['project_id'] = 'another-project'
    # ack must reject a mismatched success response even after its read proof was valid.
    client.read = lambda requested: ({'revision': 1, 'body_sha256': 'a'*64, 'attachments': []}, [])
    with pytest.raises(Refused): client.ack(fid)
