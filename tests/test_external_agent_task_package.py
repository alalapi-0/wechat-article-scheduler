"""External Browser Agent task package export."""

from __future__ import annotations

import json
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.external_agent import (
    export_task_package,
    export_task_packages_by_status,
)
from tests.conftest import make_test_config


def _seed_job(tmp_path: Path) -> tuple[object, int]:
    cfg = make_test_config(
        tmp_path,
        tmp_path / "agent.sqlite3",
        external_agent_task_outbox=tmp_path / "outbox" / "wechat_agent_tasks",
        rules={
            "publish": {
                "default_action": "draft",
                "need_open_comment": True,
                "only_fans_can_comment": False,
                "author": "本地作者",
                "content_source_url": "https://example.com/source",
            }
        },
    )
    db.init_db(cfg.database_path)
    cover = tmp_path / "cover.png"
    cover.write_bytes(b"\x89PNG\r\n\x1a\n")
    body = (
        "正文段落\n\n"
        "WECHAT_ACCESS_TOKEN=secret-token\n"
        "OPENAI_API_KEY=sk-secret\n"
        "COOKIE=session-secret\n"
    )
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (
                source_path, title, summary, body, content_hash, status, cover_path
            ) VALUES (?, '外部 Agent 测试', '摘要 AppSecret=secret-app', ?, 'hash-agent', 'imported', ?)
            """,
            (str(tmp_path / "article.md"), body, str(cover)),
        )
        article_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, '2026-06-04T10:00:00', 'done', 'mock', ?)
            """,
            (
                article_id,
                json.dumps(
                    {
                        "publish_action": "draft",
                        "need_open_comment": True,
                        "author": "任务作者",
                        "fixed_collection": "每周固定合集",
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        job_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            """
            INSERT INTO wechat_drafts (article_id, media_id, status, payload_json)
            VALUES (?, 'media-agent-001', 'created', '{}')
            """,
            (article_id,),
        )
        conn.commit()
    return cfg, job_id


def test_export_task_package_creates_required_files(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_task_package(cfg, conn, job_id)

    assert result["ok"]
    out_dir = Path(result["task_package_path"])
    for filename in (
        "task.json",
        "browser_agent_prompt.md",
        "checklist.md",
        "article_preview.html",
        "article_source.md",
        "cover.png",
        "metadata.json",
        "proof_template.md",
    ):
        assert (out_dir / filename).is_file()

    task = json.loads((out_dir / "task.json").read_text(encoding="utf-8"))
    assert task["job_id"] == str(job_id)
    assert task["manual_confirmation_required"] is True
    assert task["proof_required"] is True
    assert "click_final_publish_without_user_confirmation" in task["forbidden_actions"]
    assert "operate_outside_approved_manifest" in task["forbidden_actions"]
    assert "schedule_without_batch_confirmation" in task["forbidden_actions"]
    assert "fill_non_final_field" in task["required_actions"]
    assert task["simulation"] is True
    assert "wait_for_manual_login" not in task["required_actions"]
    assert "check_cover_crop" in task["required_actions"]
    assert "check_recommend_notify" in task["required_actions"]
    assert task["collection_name"] == "每周固定合集"
    assert task["target_field_values"]["fixed_collection"] == "每周固定合集"
    assert task["target_field_values"]["wechat_backend_schedule"] == "2026-06-04T10:00:00"
    assert task["target_field_values"]["backend_schedule_final_confirm"] == "user_only_in_wechat_backend"
    assert task["human_confirmation_steps"]["final_schedule_confirm"]

    metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["task_package_status"] == "external_agent_task_ready"
    assert metadata["safety"]["does_not_run_browser"] is True
    assert metadata["safety"]["does_not_call_llm"] is True


def test_prompt_checklist_and_proof_include_safety_boundaries(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_task_package(cfg, conn, job_id)

    out_dir = Path(result["task_package_path"])
    prompt = (out_dir / "browser_agent_prompt.md").read_text(encoding="utf-8")
    checklist = (out_dir / "checklist.md").read_text(encoding="utf-8")
    proof = (out_dir / "proof_template.md").read_text(encoding="utf-8")

    assert "不要点击最终发布按钮" in prompt
    assert "等待用户在本浏览器窗口扫码登录" in prompt
    assert "最终定时群发确认" in prompt
    assert "需要人工确认" in prompt
    assert "不要绕过登录、扫码、验证码" in prompt
    assert "已等待用户扫码登录" in checklist
    assert "未点击最终定时群发确认" in checklist
    assert "未点击最终发布" in checklist
    assert "已截图或记录 proof" in checklist
    assert "## 是否点击最终发布" in proof
    assert "否" in proof


def test_task_package_redacts_sensitive_values(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_task_package(cfg, conn, job_id)

    out_dir = Path(result["task_package_path"])
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in out_dir.iterdir()
        if path.suffix in {".json", ".md", ".html"}
    )
    assert "secret-token" not in combined
    assert "secret-app" not in combined
    assert "session-secret" not in combined
    assert "sk-secret" not in combined
    assert "access_token=secret-token" not in combined.lower()
    assert "appsecret=secret-app" not in combined.lower()


def test_batch_export_by_draft_created_status(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_task_packages_by_status(cfg, conn, status="draft_created", limit=10)

    assert result["ok"]
    assert result["count"] == 1
    assert result["results"][0]["job_id"] == job_id
