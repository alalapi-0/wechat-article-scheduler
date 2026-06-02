"""Round 121：队列表格与作品卡详情链接统一捕获返回上下文。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config
from wechat_article_scheduler import db


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "r121.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    return TestClient(create_app(cfg))


def test_workbench_detail_capture_helpers(client: TestClient) -> None:
    html = client.get("/").text
    assert "refreshWorkbenchDetailLinkBindings" in html
    assert "isWorkbenchArticleDetailHref" in html
    assert 'onclick="captureWorkbenchReturnContext()"' in html
    assert "wb-detail-link" in html
    assert 'onclick="captureWorkbenchReturnContext()">详情</a>' in html
    assert 'onclick="captureWorkbenchReturnContext()">${esc(j.title' in html
    assert "refreshWorkbenchDetailLinkBindings(el('queueBox'))" in html
