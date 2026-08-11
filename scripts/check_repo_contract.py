#!/usr/bin/env python3
"""Validate the repository's small, current source-of-truth surface."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    "project.yaml",
    "pyproject.toml",
    ".env.example",
    "config/rules.example.yaml",
    "migrations/015_wechat_draft_adapter_mode.sql",
    "docs/index.md",
    "docs/user_manual.md",
    "docs/architecture.md",
    "docs/wechat_capability_matrix.md",
    "docs/wechat_chrome_session_runbook.md",
    "docs/scheduler_runbook.md",
    "docs/testing/README.md",
    "docs/backlog.md",
    "src/wechat_article_scheduler/cli.py",
)

OBSOLETE_PATHS = (
    "agent_layer.yaml",
    "agent_tools.yaml",
    "governance/repo_protocol_standard.yaml",
    "governance/round_state.yaml",
    "docs/rounds.md",
    "scripts/agent_gate.py",
    "scripts/auto_approve_pipeline.py",
    "package.json",
    "requirements.txt",
    "src/wechat_article_scheduler/adapters/browser_assist",
    "src/wechat_article_scheduler/adapters/manual_export",
    "src/wechat_article_scheduler/adapters/local_blog",
    "src/wechat_article_scheduler/adapters/registry.py",
    "src/wechat_article_scheduler/adapters/webhook",
    "src/wechat_article_scheduler/content_packages",
    "src/wechat_article_scheduler/core/cross_project_calendar.py",
    "src/wechat_article_scheduler/core/dry_run.py",
    "src/wechat_article_scheduler/core/manifest_loader.py",
    "src/wechat_article_scheduler/core/models.py",
    "src/wechat_article_scheduler/core/multi_project_dry_run.py",
    "src/wechat_article_scheduler/core/ops_health_presearch.py",
    "src/wechat_article_scheduler/core/phase5_closure_summary.py",
    "src/wechat_article_scheduler/core/projects_registry.py",
    "src/wechat_article_scheduler/core/state_machine.py",
    "src/wechat_article_scheduler/core/unified_outbox_presearch.py",
    "src/wechat_article_scheduler/external_agent/proof_templates.py",
    "src/wechat_article_scheduler/field_settings.py",
    "src/wechat_article_scheduler/manifests",
    "src/wechat_article_scheduler/platform_payloads",
    "src/wechat_article_scheduler/publish_policy.py",
    "src/wechat_article_scheduler/remote_delete.py",
    "src/wechat_article_scheduler/review",
    "src/wechat_article_scheduler/scheduler.py",
    "src/wechat_article_scheduler/web/agent_gate_status.py",
    "src/wechat_article_scheduler/web/export_outbox_ui.js",
    "src/wechat_article_scheduler/web/generation_policy.py",
    "src/wechat_article_scheduler/web/publish_dry_run.py",
    "src/wechat_article_scheduler/web/roadmap_state.py",
    "src/wechat_article_scheduler/web/workbench_mvp.py",
    "src/wechat_article_scheduler/wechat",
    "tools/browser_automation/ui_review.py",
)


def main() -> int:
    issues: list[str] = []
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            issues.append(f"missing or empty: {relative}")

    for relative in OBSOLETE_PATHS:
        if (ROOT / relative).exists():
            issues.append(f"obsolete path still present: {relative}")

    project: object = None
    try:
        project = yaml.safe_load((ROOT / "project.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        issues.append(f"invalid project.yaml: {exc}")
    else:
        if not isinstance(project, dict):
            issues.append("project.yaml root must be a mapping")
            project = {}
        runtime = project.get("runtime")
        safety = project.get("safety")
        scope = project.get("scope")
        if not isinstance(runtime, dict):
            issues.append("project.yaml runtime must be a mapping")
            runtime = {}
        if not isinstance(safety, dict):
            issues.append("project.yaml safety must be a mapping")
            safety = {}
        if not isinstance(scope, dict):
            issues.append("project.yaml scope must be a mapping")
            scope = {}
        if runtime.get("default_mode") != "mock":
            issues.append("project.yaml must keep runtime.default_mode=mock")
        if safety.get("final_publish_api_present") is not False:
            issues.append("project.yaml must declare final_publish_api_present=false")
        raw_includes = scope.get("includes")
        raw_excludes = scope.get("excludes")
        if not isinstance(raw_includes, list):
            issues.append("project.yaml scope.includes must be a list")
            raw_includes = []
        if not isinstance(raw_excludes, list):
            issues.append("project.yaml scope.excludes must be a list")
            raw_excludes = []
        if any(not isinstance(value, str) for value in raw_includes):
            issues.append("project.yaml scope.includes values must be strings")
        if any(not isinstance(value, str) for value in raw_excludes):
            issues.append("project.yaml scope.excludes values must be strings")
        includes = {value for value in raw_includes if isinstance(value, str)}
        excludes = {value for value in raw_excludes if isinstance(value, str)}
        required_includes = {
            "wechat_draft_create_and_update",
            "remote_read_only_sync",
            "external_agent_task_packages",
            "human_supplied_publish_proof",
        }
        required_excludes = {
            "automatic_final_publish",
            "remote_draft_deletion",
            "built_in_browser_agent",
            "multi_platform_publishing",
            "automatic_content_review",
        }
        for value in sorted(required_includes - includes):
            issues.append(f"project.yaml scope.includes missing: {value}")
        for value in sorted(required_excludes - excludes):
            issues.append(f"project.yaml scope.excludes missing: {value}")

    try:
        rules = yaml.safe_load(
            (ROOT / "config" / "rules.example.yaml").read_text(encoding="utf-8")
        )
    except (OSError, yaml.YAMLError) as exc:
        issues.append(f"invalid config/rules.example.yaml: {exc}")
    else:
        if not isinstance(rules, dict):
            issues.append("config/rules.example.yaml root must be a mapping")
        else:
            publish = rules.get("publish")
            external_agent = rules.get("external_agent")
            if not isinstance(publish, dict):
                issues.append("config/rules.example.yaml publish must be a mapping")
            elif publish.get("auto_execute") is not False:
                issues.append("config/rules.example.yaml must default publish.auto_execute=false")
            if not isinstance(external_agent, dict):
                issues.append("config/rules.example.yaml external_agent must be a mapping")
            else:
                if external_agent.get("redact_sensitive_values") is not True:
                    issues.append("external_agent.redact_sensitive_values must default true")
                if external_agent.get("include_inspection_report") is not True:
                    issues.append("external_agent.include_inspection_report must default true")
                if "include_proof_template" in external_agent:
                    issues.append("obsolete external_agent.include_proof_template remains")

    source_root = ROOT / "src" / "wechat_article_scheduler"
    forbidden_source_patterns = (
        ("final publish", re.compile(r"cgi-bin/freepublish/submit")),
        ("final publish", re.compile(r"\bdef\s+submit_publish\s*\(")),
        ("final publish", re.compile(r"\.submit_publish\s*\(")),
        ("remote draft deletion", re.compile(r"cgi-bin/draft/delete")),
        ("remote draft deletion", re.compile(r"\bdef\s+delete_draft\s*\(")),
        ("remote draft deletion", re.compile(r"\.delete_draft\s*\(")),
    )
    for path in source_root.rglob("*"):
        if path.suffix not in {".py", ".html", ".js"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for capability, pattern in forbidden_source_patterns:
            if pattern.search(text):
                issues.append(
                    f"forbidden {capability} capability remains in "
                    f"{path.relative_to(ROOT)}: {pattern.pattern}"
                )

    if issues:
        print("check_repo_contract: FAIL")
        for issue in issues:
            print(f"  {issue}")
        return 1

    print("check_repo_contract: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
