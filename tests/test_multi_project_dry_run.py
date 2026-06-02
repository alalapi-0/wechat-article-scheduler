"""Phase5 多项目 projects.yaml + manifest 批量干跑。"""

from __future__ import annotations

from pathlib import Path

from wechat_article_scheduler.core.multi_project_dry_run import (
    build_multi_project_dry_run,
    projects_registry_summary,
)
from wechat_article_scheduler.core.projects_registry import (
    default_projects_path,
    load_projects_registry,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_EXAMPLE = ROOT / "config" / "projects.example.yaml"


def test_default_projects_example_exists():
    assert PROJECTS_EXAMPLE.is_file()


def test_load_projects_registry_two_projects():
    entries, _meta, validation = load_projects_registry(ROOT, PROJECTS_EXAMPLE)
    assert validation.ok
    assert len(entries) == 2
    assert entries[0].project_id == "demo-novel"
    assert entries[1].enabled is True


def test_multi_project_dry_run_all_ok():
    summary = build_multi_project_dry_run(ROOT, projects_path=PROJECTS_EXAMPLE)
    assert summary["ok"] is True
    assert summary["project_count"] == 2
    assert summary["manifest_count"] == 2
    assert "scan/plan" in summary["wechat_mainline"]
    for proj in summary["projects"]:
        assert proj["ok"] is True
        assert proj["manifest_count"] >= 1


def test_projects_registry_api_shape():
    reg = projects_registry_summary(ROOT, projects_path=PROJECTS_EXAMPLE)
    assert reg["ok"] is True
    assert len(reg["projects"]) == 2
    assert default_projects_path(ROOT) == PROJECTS_EXAMPLE or (
        ROOT / "config" / "projects.yaml"
    ).exists()
