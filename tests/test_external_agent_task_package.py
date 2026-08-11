"""External Browser Agent task package export."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.external_agent import (
    export_task_package,
    export_task_packages_by_status,
)
from tests.conftest import make_test_config
from tests.test_web_upload import PNG


def _seed_job(tmp_path: Path) -> tuple[object, int]:
    cfg = make_test_config(
        tmp_path,
        tmp_path / "agent.sqlite3",
        external_agent_task_outbox=tmp_path / "outbox" / "wechat_agent_tasks",
        rules={
            "publish": {
                "need_open_comment": True,
                "only_fans_can_comment": False,
                "author": "本地作者",
                "content_source_url": "https://example.com/source",
            }
        },
    )
    db.init_db(cfg.database_path)
    cover = tmp_path / "articles" / "covers" / "cover.png"
    cover.parent.mkdir(parents=True, exist_ok=True)
    cover.write_bytes(PNG)
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
            INSERT INTO wechat_drafts (
                article_id, media_id, status, payload_json,
                adapter_mode, publish_job_id
            ) VALUES (?, 'mock_media_agent_001', 'created', '{}', 'mock', ?)
            """,
            (article_id, job_id),
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
        "inspection_report.md",
    ):
        assert (out_dir / filename).is_file()

    task = json.loads((out_dir / "task.json").read_text(encoding="utf-8"))
    assert task["schema_version"] == 2
    assert task["job_id"] == str(job_id)
    assert task["manual_confirmation_required"] is True
    assert task["inspection_report_required"] is True
    assert "不能作为发布 proof" in task["completion_rule"]
    assert "click_final_publish" in task["forbidden_actions"]
    assert "click_final_publish_without_user_confirmation" not in task["forbidden_actions"]
    assert "operate_outside_approved_task_package" in task["forbidden_actions"]
    assert "modify_backend_fields" in task["forbidden_actions"]
    assert "save_draft" in task["forbidden_actions"]
    assert "schedule_backend_publish" in task["forbidden_actions"]
    assert "click_final_schedule_confirm" in task["forbidden_actions"]
    assert "report_non_api_field_gap" in task["required_actions"]
    assert "save_draft" not in task["required_actions"]
    assert "set_pre_publish_fields" not in task["required_actions"]
    assert task["simulation"] is True
    assert "wait_for_manual_login" not in task["required_actions"]
    assert "check_cover_crop" in task["required_actions"]
    assert "check_recommend_notify" in task["required_actions"]
    assert task["collection_name"] == "每周固定合集"
    assert task["expected_field_values"]["fixed_collection"] == "每周固定合集"
    assert task["expected_field_values"]["scheduled_draft_creation"] == "2026-06-04T10:00:00"
    assert task["expected_field_values"]["backend_schedule_final_confirm"] == "user_only"
    assert task["human_confirmation_steps"]["backend_changes"]

    metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["schema_version"] == 2
    assert metadata["task_package_status"] == "external_agent_task_ready"
    assert metadata["safety"]["does_not_run_browser"] is True
    assert metadata["safety"]["does_not_call_llm"] is True


def test_task_package_listing_never_uses_path_iteration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, job_id = _seed_job(tmp_path)
    monkeypatch.setattr(Path, "iterdir", lambda _path: (_ for _ in ()).throw(AssertionError("iterdir")))
    with db.connect(cfg.database_path) as conn:
        result = export_task_package(cfg, conn, job_id)
    assert "task.json" in result["files"]


def test_task_package_cleanup_does_not_delete_from_replacement_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    cfg, job_id = _seed_job(tmp_path)
    job_dir = cfg.external_agent_task_outbox / f"job-{job_id:06d}"
    detached = job_dir.parent / "detached-job"
    job_dir.mkdir(parents=True)
    (job_dir / "cover.stale").write_bytes(b"original-stale")
    original_list = fs.DirectoryHandle.list_names
    swapped = {"done": False}

    def list_then_replace(handle):
        names = original_list(handle)
        if handle.path == job_dir.absolute() and "cover.stale" in names and not swapped["done"]:
            swapped["done"] = True
            job_dir.rename(detached)
            job_dir.mkdir()
            (job_dir / "cover.stale").write_bytes(b"replacement-must-survive")
        return names

    monkeypatch.setattr(fs.DirectoryHandle, "list_names", list_then_replace)
    with db.connect(cfg.database_path) as conn:
        result = export_task_package(cfg, conn, job_id)
    assert result["ok"] is True
    assert not (detached / "cover.stale").exists()
    assert (job_dir / "cover.stale").read_bytes() == b"replacement-must-survive"


def test_task_package_final_listing_verifies_original_held_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from wechat_article_scheduler import filesystem_safety as fs

    cfg, job_id = _seed_job(tmp_path)
    job_dir = cfg.external_agent_task_outbox / f"job-{job_id:06d}"
    detached = job_dir.parent / "detached-final-listing"
    original_list = fs.DirectoryHandle.list_names
    swapped = {"done": False}

    def final_list_then_replace(handle):
        names = original_list(handle)
        if handle.path == job_dir.absolute() and "task.json" in names and not swapped["done"]:
            swapped["done"] = True
            job_dir.rename(detached)
            job_dir.mkdir()
            (job_dir / "task.json").write_bytes(b"replacement-must-not-be-verified")
        return names

    monkeypatch.setattr(fs.DirectoryHandle, "list_names", final_list_then_replace)
    with db.connect(cfg.database_path) as conn:
        result = export_task_package(cfg, conn, job_id)
    assert "task.json" in result["files"]
    assert (detached / "task.json").read_bytes().startswith(b"{")
    assert (job_dir / "task.json").read_bytes() == b"replacement-must-not-be-verified"


def test_export_rejects_preplanted_job_directory_symlink(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    root = cfg.external_agent_task_outbox
    root.mkdir(parents=True, exist_ok=True)
    (root / f"job-{job_id:06d}").symlink_to(outside, target_is_directory=True)
    with db.connect(cfg.database_path) as conn, pytest.raises(ValueError):
        export_task_package(cfg, conn, job_id)
    assert list(outside.iterdir()) == []


def test_prompt_checklist_and_inspection_report_include_safety_boundaries(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        result = export_task_package(cfg, conn, job_id)

    out_dir = Path(result["task_package_path"])
    prompt = (out_dir / "browser_agent_prompt.md").read_text(encoding="utf-8")
    checklist = (out_dir / "checklist.md").read_text(encoding="utf-8")
    report = (out_dir / "inspection_report.md").read_text(encoding="utf-8")

    assert "不得点击“保存草稿”" in prompt
    assert "不要点击保存草稿、正式发表、群发" in prompt
    assert "用户明确批准" in prompt
    assert "不得假装新建或隔离浏览器已经登录" in prompt
    assert "报告 BLOCKED 并停止" in prompt
    assert "不得读取 cookie/session/token" in prompt
    assert "等待用户在可见 Chrome 页面自行扫码/验证" in prompt
    assert "只读核对" in prompt
    assert "不要绕过登录、扫码、验证码" in prompt
    assert "用户已批准使用当前可见的既有登录会话" in checklist
    assert "未假装新建或隔离浏览器已经登录" in checklist
    assert "已确认当前页面属于 mp.weixin.qq.com" in checklist
    assert "报告 BLOCKED 并停止" in checklist
    assert "不得读取 cookie/session/token" in checklist
    assert "可见 Chrome 页面自行扫码" in checklist
    assert "未点击保存草稿" in checklist
    assert "未点击正式发表、群发" in checklist
    assert "未点击最终发布" in checklist
    assert "已填写 inspection_report.md" in checklist
    assert "## 是否点击最终发布" in report
    assert "不能作为发布 proof" in report
    assert "否" in report


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


def test_batch_export_requires_draft_from_exact_job(tmp_path: Path) -> None:
    cfg, first_job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        article_id = int(
            conn.execute(
                "SELECT article_id FROM publish_jobs WHERE id = ?",
                (first_job_id,),
            ).fetchone()["article_id"]
        )
        second_job_id = int(
            conn.execute(
                """
                INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode)
                VALUES (?, datetime('now'), 'done', 'mock')
                """,
                (article_id,),
            ).lastrowid
        )
        conn.commit()
        result = export_task_packages_by_status(
            cfg,
            conn,
            status="draft_created",
            limit=10,
        )

    assert [item["job_id"] for item in result["results"]] == [first_job_id]
    assert second_job_id != first_job_id


def test_reexport_removes_disabled_managed_files(tmp_path: Path) -> None:
    cfg, job_id = _seed_job(tmp_path)
    with db.connect(cfg.database_path) as conn:
        first = export_task_package(cfg, conn, job_id)
    out_dir = Path(first["task_package_path"])
    assert (out_dir / "article_source.md").is_file()
    assert (out_dir / "cover.png").is_file()

    minimal = replace(
        cfg,
        external_agent_include_article_preview=False,
        external_agent_include_article_source=False,
        external_agent_include_cover=False,
        external_agent_include_prompt=False,
        external_agent_include_checklist=False,
        external_agent_include_inspection_report=False,
    )
    with db.connect(cfg.database_path) as conn:
        second = export_task_package(minimal, conn, job_id)

    assert second["files"] == ["metadata.json", "task.json"]
    task = json.loads((out_dir / "task.json").read_text(encoding="utf-8"))
    assert task["local_files"] == {
        "browser_agent_prompt": None,
        "checklist": None,
        "inspection_report": None,
        "article_preview": None,
        "article_source": None,
        "cover": None,
        "metadata": "metadata.json",
    }
