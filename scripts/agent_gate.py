#!/usr/bin/env python3
"""治理门控 + 多轮自主推进。

Agent 循环（仓库根目录，优先使用 .venv/bin/python）::

    python scripts/agent_gate.py status
    # 实现 current_round / next_actions 中的任务
    python scripts/agent_gate.py gate          # exit 0 → 可继续；2 → 修复后重试
    python scripts/agent_gate.py advance --commit   # 推进 round_state；可选提交

子命令:
    status   打印当前轮、阶段、next_actions 与建议的下一步命令
    gate     全量 pytest + 当前轮冒烟 + 安全/协议检查（默认子命令）
    advance  在 gate 通过后更新 round_state；``--commit`` 时安全提交

兼容:
    ``--check-only`` 等价于 ``gate``（不 advance、不 commit）

退出码（与 governance/repo_protocol_standard.yaml 一致）:
    0 PASS — 门控通过，可继续实现或执行 advance
    1 WARNING — 非阻断，记录后继续低风险治理
    2 BLOCKED — 必须修复，禁止自主提交/推进

默认不 push；远程推送需显式 ``advance --push``（通常需人工授权）。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "reports" / "agent_gate_report.md"
ROUND_STATE_PATH = ROOT / "governance" / "round_state.yaml"
PROJECT_PATH = ROOT / "project.yaml"
ROUNDS_DOC = ROOT / "docs" / "rounds.md"

PASS, WARNING, BLOCKED = "PASS", "WARNING", "BLOCKED"
SEVERITY_RANK = {PASS: 0, WARNING: 1, BLOCKED: 2}
EXIT_CODE = {PASS: 0, WARNING: 1, BLOCKED: 2}

# 权威路线图：docs/rounds.md（Round 0–38）。修改路线图时须同步本表与 tests/test_agent_gate.py。
ROUND_ORDER = [
    "round_000",
    "round_001",
    "round_002",
    "round_003",
    "round_004",
    "round_005",
    "round_006",
    "round_007",
    "round_008",
    "round_009",
    "round_010",
    "round_011",
    "round_012",
    "round_013",
    "round_014",
    "round_015",
    "round_016",
    "round_017",
    "round_018",
    "round_019",
    "round_020",
    "round_021",
    "round_022",
    "round_023",
    "round_024",
    "round_025",
    "round_026",
    "round_027",
    "round_028",
    "round_029",
    "round_030",
    "round_031",
    "round_032",
    "round_033",
    "round_034",
    "round_035",
    "round_036",
    "round_037",
    "round_038",
]

# 与 docs/rounds.md 路线图对齐的轮次元数据（gate 冒烟 + advance 写入 round_state）
ROUND_META: dict[str, dict[str, Any]] = {
    "round_000": {
        "name": "Round 0 - CLI MVP 闭环",
        "acceptance_criteria": [
            "init-db / scan / plan / run-once 闭环可运行",
        ],
        "next_actions": [
            "推进 Round 1：治理轮与文档重构",
        ],
    },
    "round_001": {
        "name": "Round 1 - 治理轮",
        "acceptance_criteria": [
            "完成全仓审计与治理文档基线",
            "digest 120 字约束与测试通过",
            "目录骨架创建且不破坏现有导入",
        ],
        "next_actions": [
            "推进 Round 2：内容库建模与审核闸门",
        ],
    },
    "round_002": {
        "name": "Round 2 - 内容库建模",
        "acceptance_criteria": [
            "内容集合、标签与审核状态模型落地",
        ],
        "next_actions": [
            "推进 Round 3：调度域模块化",
        ],
    },
    "round_003": {
        "name": "Round 3 - 调度域模块化",
        "acceptance_criteria": [
            "scheduler 领域拆分与执行器分层",
        ],
        "next_actions": [
            "推进 Round 4：数据迁移体系",
        ],
    },
    "round_004": {
        "name": "Round 4 - 数据迁移体系",
        "acceptance_criteria": [
            "migrations 版本化、回滚策略与兼容升级路径",
        ],
        "next_actions": [
            "推进 Round 5：Web 控制台增强",
        ],
    },
    "round_005": {
        "name": "Round 5 - Web 控制台增强",
        "acceptance_criteria": [
            "轻量鉴权、只读仪表盘与人工确认流",
        ],
        "next_actions": [
            "推进 Round 6：渲染与模板扩展",
        ],
    },
    "round_006": {
        "name": "Round 6 - 渲染与模板扩展",
        "acceptance_criteria": [
            "Markdown/HTML 渲染规则与模板策略稳定",
        ],
        "next_actions": [
            "推进 Round 7：封面资产管理",
        ],
    },
    "round_007": {
        "name": "Round 7 - 封面资产管理",
        "acceptance_criteria": [
            "素材目录、引用与人工裁剪流程",
        ],
        "next_actions": [
            "推进 Round 8：可观测与运维",
        ],
    },
    "round_008": {
        "name": "Round 8 - 可观测与运维",
        "acceptance_criteria": [
            "更细粒度审计、失败分类与 SLO 指标",
            "重试、日志与 DRY_RUN 报告",
        ],
        "next_actions": [
            "推进 Round 9：发布工作台产品化",
        ],
    },
    "round_009": {
        "name": "Round 9 - 发布工作台产品化",
        "acceptance_criteria": [
            "稳定交付、文档收口与长期维护规范",
        ],
        "next_actions": [
            "推进 Round 10：基础工作台可用性升级",
        ],
    },
    "round_010": {
        "name": "Round 10 - 基础工作台可用性升级",
        "acceptance_criteria": [
            "后台页面完成分区布局与操作分组",
            "操作具备 loading、防重复点击与成功/失败反馈",
            "状态展示可读，失败返回下一步建议",
        ],
        "next_actions": [
            "推进 Round 11：路线图执行化与治理编排",
        ],
    },
    "round_011": {
        "name": "Round 11 - 路线图执行化与治理编排",
        "acceptance_criteria": [
            "rounds.md 明确每轮目标/范围/验收/风险/回滚",
            "ROUND_ORDER / ROUND_META / tests 同步校验",
        ],
        "next_actions": [
            "推进 Round 12：持续演进与质量门禁强化",
        ],
    },
    "round_012": {
        "name": "Round 12 - 持续演进与质量门禁强化",
        "acceptance_criteria": [
            "建立后续轮次的最小质量门禁与模板约束",
        ],
        "next_actions": [
            "推进 Round 13：Renderer 内容渲染深化",
        ],
    },
    "round_013": {
        "name": "Round 13 - Renderer 内容渲染深化",
        "acceptance_criteria": [
            "渲染规则矩阵、预览样例与回归测试补齐",
        ],
        "next_actions": [
            "推进 Round 14：Cover 封面资产工作流",
        ],
    },
    "round_014": {
        "name": "Round 14 - Cover 封面资产工作流",
        "acceptance_criteria": [
            "封面索引、缺失检查与发布前提示可用",
        ],
        "next_actions": [
            "推进 Round 15：Content Library 与多合集",
        ],
    },
    "round_015": {
        "name": "Round 15 - Content Library 与多合集",
        "acceptance_criteria": [
            "合集、标签、状态视图具备最小查询能力",
        ],
        "next_actions": [
            "推进 Round 16：Scheduler 编排与人工闸门",
        ],
    },
    "round_016": {
        "name": "Round 16 - Scheduler 编排与人工闸门",
        "acceptance_criteria": [
            "未批准任务不会进入真实发布路径",
        ],
        "next_actions": [
            "推进 Round 17：真实发布安全试运行",
        ],
    },
    "round_017": {
        "name": "Round 17 - 真实发布安全试运行",
        "acceptance_criteria": [
            "real draft / publish 试运行流程具备显式安全开关",
        ],
        "next_actions": [
            "推进 Round 18：能力矩阵与 AI 辅助入口",
        ],
    },
    "round_018": {
        "name": "Round 18 - 能力矩阵与 AI 辅助入口",
        "acceptance_criteria": [
            "能力矩阵明确已实现、未来实现与暂不做边界",
        ],
        "next_actions": [
            "推进 Round 19：普通用户工作台原则与 Playwright 视觉基线",
        ],
    },
    "round_019": {
        "name": "Round 19 - 普通用户工作台原则与 Playwright 视觉基线",
        "acceptance_criteria": [
            "Playwright 诊断脚本可复跑，普通/详情/高级三层信息边界清晰",
        ],
        "next_actions": [
            "推进 Round 20：术语人话化与中文文案标准",
        ],
    },
    "round_020": {
        "name": "Round 20 - 术语人话化与中文文案标准",
        "acceptance_criteria": [
            "普通视图不再直接出现裸内部词，术语映射有单一来源",
        ],
        "next_actions": [
            "推进 Round 21：普通视图信息减法",
        ],
    },
    "round_021": {
        "name": "Round 21 - 普通视图信息减法",
        "acceptance_criteria": [
            "首屏默认不出现数据库路径、原始 JSON、内部统计和技术开关原文",
        ],
        "next_actions": [
            "推进 Round 22：三步操作主流程",
        ],
    },
    "round_022": {
        "name": "Round 22 - 三步操作主流程",
        "acceptance_criteria": [
            "scan/plan/run-once 被组织为找文章、安排时间、执行到点文章三步主流程",
        ],
        "next_actions": [
            "推进 Round 23：人话反馈系统",
        ],
    },
    "round_023": {
        "name": "Round 23 - 人话反馈系统",
        "acceptance_criteria": [
            "操作后展示做成了什么、没做成什么、下一步是什么",
        ],
        "next_actions": [
            "推进 Round 24：空状态与首次使用",
        ],
    },
    "round_024": {
        "name": "Round 24 - 空状态与首次使用",
        "acceptance_criteria": [
            "空数据下首页、文章列表、发布队列和事件日志提供可操作引导",
        ],
        "next_actions": [
            "推进 Round 25：安全发布护栏",
        ],
    },
    "round_025": {
        "name": "Round 25 - 安全发布护栏",
        "acceptance_criteria": [
            "普通用户能在首屏判断是否会真的发到公众号，真实发布前必须确认",
        ],
        "next_actions": [
            "推进 Round 26：桌面主布局",
        ],
    },
    "round_026": {
        "name": "Round 26 - 桌面主布局",
        "acceptance_criteria": [
            "桌面首屏具备顶部安全状态、导航、主内容区、次级内容区和高级入口",
        ],
        "next_actions": [
            "推进 Round 27：文章列表普通化",
        ],
    },
    "round_027": {
        "name": "Round 27 - 文章列表普通化",
        "acceptance_criteria": [
            "文章列表展示标题、合集、状态、摘要、封面、更新时间，技术字段默认隐藏",
        ],
        "next_actions": [
            "推进 Round 28：发布队列普通化",
        ],
    },
    "round_028": {
        "name": "Round 28 - 发布队列普通化",
        "acceptance_criteria": [
            "发布队列展示哪篇、什么时候、当前状态、失败原因和可做什么，技术列默认隐藏",
        ],
        "next_actions": [
            "推进 Round 29：事件日志时间线",
        ],
    },
    "round_029": {
        "name": "Round 29 - 事件日志时间线",
        "acceptance_criteria": [
            "事件日志显示人话时间线，payload 默认隐藏到高级区",
        ],
        "next_actions": [
            "推进 Round 30：高级信息开关",
        ],
    },
    "round_030": {
        "name": "Round 30 - 高级信息开关",
        "acceptance_criteria": [
            "数据库路径、原始 JSON、内部字段和调试统计集中于默认隐藏的高级视图",
        ],
        "next_actions": [
            "推进 Round 31：帮助与解释系统",
        ],
    },
    "round_031": {
        "name": "Round 31 - 帮助与解释系统",
        "acceptance_criteria": [
            "用户能从首屏找到关键操作和关键名词的简短解释",
        ],
        "next_actions": [
            "推进 Round 32：错误与恢复指引",
        ],
    },
    "round_032": {
        "name": "Round 32 - 错误与恢复指引",
        "acceptance_criteria": [
            "常见失败用普通用户语言说明原因、影响和下一步",
        ],
        "next_actions": [
            "推进 Round 33：桌面效率优化",
        ],
    },
    "round_033": {
        "name": "Round 33 - 桌面效率优化",
        "acceptance_criteria": [
            "电脑浏览器中可高效筛选、排序、定位文章和发布任务",
        ],
        "next_actions": [
            "推进 Round 34：窄屏兼容验收",
        ],
    },
    "round_034": {
        "name": "Round 34 - 窄屏兼容验收",
        "acceptance_criteria": [
            "375/768 视口不横向溢出、关键按钮可点、文字可读，且不牺牲桌面布局",
        ],
        "next_actions": [
            "推进 Round 35：Playwright E2E 可用性基线",
        ],
    },
    "round_035": {
        "name": "Round 35 - Playwright E2E 可用性基线",
        "acceptance_criteria": [
            "普通视图不裸露内部字段、三步流程可见、安全状态可读、窄屏无溢出具备自动断言",
        ],
        "next_actions": [
            "推进 Round 36：非技术用户走查报告",
        ],
    },
    "round_036": {
        "name": "Round 36 - 非技术用户走查报告",
        "acceptance_criteria": [
            "按看得懂、做得到、知道结果、知道下一步完成核心场景走查",
        ],
        "next_actions": [
            "推进 Round 37：Web 控制台 MVP 收口",
        ],
    },
    "round_037": {
        "name": "Round 37 - Web 控制台 MVP 收口",
        "acceptance_criteria": [
            "普通用户能完成扫描、排期、执行演练/草稿路径，并理解状态与失败提示",
        ],
        "next_actions": [
            "推进 Round 38：后续功能接入规范",
        ],
    },
    "round_038": {
        "name": "Round 38 - 后续功能接入规范",
        "acceptance_criteria": [
            "未来 Web 功能必须定义普通视图、详情视图和高级字段归属",
        ],
        "next_actions": [
            "维护 docs/rounds.md 与治理协议；按后续功能接入规范规划 Round 39+",
        ],
    },
}

SECRET_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}

SECRET_PATH_SUFFIXES = (
    "/.env",
    "/credentials.json",
    "/secrets.json",
)


@dataclass
class Finding:
    check: str
    severity: str
    message: str


@dataclass
class GateState:
    findings: list[Finding] = field(default_factory=list)

    def add(self, check: str, severity: str, message: str) -> None:
        self.findings.append(Finding(check, severity, message))

    def passed(self, check: str, message: str) -> None:
        self.add(check, PASS, message)

    def warn(self, check: str, message: str) -> None:
        self.add(check, WARNING, message)

    def block(self, check: str, message: str) -> None:
        self.add(check, BLOCKED, message)

    @property
    def verdict(self) -> str:
        worst = PASS
        for f in self.findings:
            if SEVERITY_RANK[f.severity] > SEVERITY_RANK[worst]:
                worst = f.severity
        return worst


def load_yaml(path: Path) -> dict[str, Any] | None:
    if yaml is None or not path.exists():
        return None
    with path.open("r", encoding="utf-8") as h:
        data = yaml.safe_load(h) or {}
    return data if isinstance(data, dict) else None


def load_round_state() -> dict[str, Any]:
    return load_yaml(ROUND_STATE_PATH) or {}


def venv_python() -> str:
    vp = ROOT / ".venv" / "bin" / "python"
    return str(vp) if vp.exists() else (sys.executable or "python3")


def run_cmd(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def git_tracked() -> list[str]:
    code, out, _ = run_cmd(["git", "ls-files"])
    if code != 0:
        return []
    return [line for line in out.splitlines() if line]


def is_secret_path(path: str) -> bool:
    p = path.strip().removeprefix("./")
    base = Path(p).name
    if base in SECRET_BASENAMES:
        return True
    return any(p.endswith(suffix) for suffix in SECRET_PATH_SUFFIXES)


def git_porcelain() -> list[tuple[str, str]]:
    code, out, _ = run_cmd(["git", "status", "--porcelain"])
    if code != 0:
        return []
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        rows.append((xy, path))
    return rows


def check_env_tracking(state: GateState, tracked: list[str]) -> None:
    if any(p == ".env" or p.endswith("/.env") for p in tracked):
        state.block("env_tracking", ".env 被 Git 跟踪，请先 git rm --cached .env")
    else:
        state.passed("env_tracking", ".env 未被跟踪")


def check_staged_secrets(state: GateState) -> None:
    for _xy, path in git_porcelain():
        if is_secret_path(path):
            state.block("secret_staging", f"工作区含敏感路径，禁止提交: {path}")
            return
    state.passed("secret_staging", "工作区未发现待提交的敏感路径")


def check_wechat_mock_default(state: GateState) -> None:
    example = ROOT / ".env.example"
    if not example.exists():
        state.warn("wechat_mode", "缺少 .env.example")
        return
    text = example.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"^WECHAT_MODE\s*=\s*mock", text, re.MULTILINE):
        state.passed("wechat_mode", "默认 WECHAT_MODE=mock")
    else:
        state.warn("wechat_mode", ".env.example 未声明 WECHAT_MODE=mock")


def get_current_round_id() -> str:
    data = load_round_state()
    cur = data.get("current_round", {})
    if isinstance(cur, dict):
        return str(cur.get("id", "round_000"))
    return "round_000"


def get_current_round_status() -> str:
    data = load_round_state()
    cur = data.get("current_round", {})
    if isinstance(cur, dict):
        return str(cur.get("status", "active"))
    return "active"


def round_smoke(round_id: str, py: str) -> tuple[bool, str]:
    """按轮次运行 CLI 冒烟（需已 init-db 与示例配置）。"""
    base = [py, "-m", "wechat_article_scheduler.cli"]
    if round_id == "round_000":
        steps = [
            ([*base, "init-db"], "init-db"),
            ([*base, "scan"], "scan"),
            ([*base, "plan"], "plan"),
            ([*base, "run-once"], "run-once"),
        ]
    elif round_id == "round_001":
        steps = [
            ([py, "-m", "pytest", "tests/test_workflow.py", "-q"], "pytest workflow"),
            ([py, "-m", "pytest", "tests/test_digest_limits.py", "tests/test_parser.py", "-q"], "pytest digest/parser"),
        ]
    elif round_id == "round_002":
        steps = [([*base, "events", "--limit", "5"], "events")]
    elif round_id == "round_003":
        steps = [([py, "-m", "pytest", "tests/test_real_adapter.py", "-q"], "pytest real adapter")]
    elif round_id == "round_004":
        steps = [([py, "scripts/check_repo_contract.py"], "check_repo_contract")]
    elif round_id == "round_005":
        steps = [([py, "-m", "pytest", "tests/test_web_app.py", "-q"], "pytest web app")]
    elif round_id == "round_006":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_renderer_markdown.py", "tests/test_parser.py", "-q"],
                "pytest renderer/parser",
            ),
        ]
    elif round_id == "round_007":
        return True, "cover assets smoke skipped (future round)"
    elif round_id == "round_008":
        steps = [([py, "-m", "pytest", "tests/test_scheduler_hardening.py", "-q"], "pytest hardening")]
    elif round_id == "round_009":
        return True, "productization smoke skipped (future round)"
    elif round_id == "round_010":
        steps = [([py, "-m", "pytest", "tests/test_web_app.py", "-q"], "pytest web app")]
    elif round_id == "round_011":
        steps = [([py, "-m", "pytest", "tests/test_agent_gate.py", "-q"], "pytest agent gate")]
    elif round_id == "round_012":
        steps = [
            ([py, "scripts/check_rounds_doc.py"], "check_rounds_doc"),
            ([py, "scripts/check_test_coverage_hints.py"], "coverage hints"),
            (
                [py, "-m", "pytest", "tests/test_agent_gate.py", "tests/test_check_rounds_doc.py", "-q"],
                "pytest gate/docs",
            ),
        ]
    elif round_id == "round_013":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_renderer_markdown.py", "tests/test_parser.py", "-q"],
                "pytest renderer/parser",
            ),
        ]
    elif round_id == "round_014":
        steps = [([py, "-m", "pytest", "tests/test_cover_assets.py", "-q"], "pytest cover assets")]
    elif round_id == "round_015":
        steps = [([py, "-m", "pytest", "tests/test_content_library.py", "-q"], "pytest content library")]
    elif round_id == "round_016":
        steps = [([py, "-m", "pytest", "tests/test_scheduler_hardening.py", "-q"], "pytest hardening")]
    elif round_id == "round_017":
        steps = [([py, "-m", "pytest", "tests/test_real_adapter.py", "-q"], "pytest real adapter")]
    elif round_id == "round_018":
        steps = [([py, "-m", "pytest", "tests/test_agent_gate.py", "-q"], "pytest agent gate")]
    elif round_id == "round_019":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_ui_review.py", "-q"],
                "pytest ui review / playwright baseline",
            ),
        ]
    elif round_id in {
        "round_020",
        "round_021",
        "round_022",
        "round_023",
        "round_024",
        "round_025",
        "round_026",
        "round_027",
        "round_028",
        "round_029",
        "round_030",
        "round_031",
        "round_032",
        "round_033",
        "round_034",
    }:
        # 普通用户友好 Web 轮：实现时以 tests/test_web_app.py / Playwright 为基础冒烟，未实现前优雅 skip
        return True, f"{round_id} usability smoke skipped (future round; will use tests/test_web_app.py)"
    elif round_id == "round_035":
        return True, "e2e UI smoke skipped until tests/test_ui_e2e.py exists (future round)"
    elif round_id in {"round_036", "round_037", "round_038"}:
        return True, f"{round_id} usability governance smoke skipped (future round)"
    else:
        return True, "unknown round skipped"

    notes = []
    for cmd, name in steps:
        code, so, se = run_cmd(cmd)
        if code != 0:
            return False, f"{name} failed (exit {code}): {se or so}"
        notes.append(f"{name}: ok")
    return True, "; ".join(notes)


def run_pytest(py: str) -> tuple[bool, str]:
    code, so, se = run_cmd([py, "-m", "pytest", "-q"])
    if code != 0:
        return False, se or so
    return True, so.strip() or "pytest ok"


def run_gate_checks(state: GateState, *, py: str | None = None) -> str:
    """执行门控检查，返回 current_round id。"""
    tracked = git_tracked()
    check_env_tracking(state, tracked)
    check_staged_secrets(state)
    check_wechat_mock_default(state)

    if not (ROOT / "governance" / "repo_protocol_standard.yaml").exists():
        state.block("protocol", "governance/repo_protocol_standard.yaml missing")
    else:
        state.passed("protocol", "protocol present")

    interpreter = py or venv_python()
    ok, msg = run_pytest(interpreter)
    if ok:
        state.passed("pytest", msg)
    else:
        state.block("pytest", msg[:800])

    round_id = get_current_round_id()
    smoke_ok, smoke_msg = round_smoke(round_id, interpreter)
    if smoke_ok:
        state.passed("round_smoke", f"{round_id}: {smoke_msg}")
    else:
        state.block("round_smoke", smoke_msg[:800])
    return round_id


def suggest_next_command(round_id: str, status: str) -> str:
    if status == "completed":
        return f"python scripts/agent_gate.py advance --commit  # 将 {round_id} 标记完成并进入下一轮"
    return "python scripts/agent_gate.py gate  # 实现任务后校验；通过后 advance --commit"


def cmd_status(*, json_out: bool) -> int:
    data = load_round_state()
    round_id = get_current_round_id()
    cur = data.get("current_round", {}) if isinstance(data.get("current_round"), dict) else {}
    status = str(cur.get("status", "active"))
    payload = {
        "current_round": {
            "id": round_id,
            "name": cur.get("name") or ROUND_META.get(round_id, {}).get("name", round_id),
            "status": status,
        },
        "last_completed_round": data.get("last_completed_round"),
        "next_actions": data.get("next_actions") or ROUND_META.get(round_id, {}).get("next_actions", []),
        "acceptance_criteria": data.get("acceptance_criteria")
        or ROUND_META.get(round_id, {}).get("acceptance_criteria", []),
        "protocol_standard_sync_required": data.get("protocol_standard_sync_required", False),
        "suggested_command": suggest_next_command(round_id, status),
        "docs": str(ROUNDS_DOC.relative_to(ROOT)),
    }
    if json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"current_round: {payload['current_round']['id']} ({payload['current_round']['name']})")
        print(f"status: {status}")
        if payload["last_completed_round"]:
            print(f"last_completed_round: {payload['last_completed_round']}")
        print("acceptance_criteria:")
        for item in payload["acceptance_criteria"]:
            print(f"  - {item}")
        print("next_actions:")
        for item in payload["next_actions"]:
            print(f"  - {item}")
        print(f"suggested: {payload['suggested_command']}")
    return EXIT_CODE[PASS]


def advance_round_state(current_id: str) -> str | None:
    """将 round_state 推进到下一轮；若已是最后一轮则返回 None。"""
    if yaml is None:
        return None
    try:
        idx = ROUND_ORDER.index(current_id)
    except ValueError:
        idx = 0
    if idx >= len(ROUND_ORDER) - 1:
        return None
    next_id = ROUND_ORDER[idx + 1]
    meta = ROUND_META.get(next_id, {})
    data = load_round_state()
    now = datetime.now(timezone.utc).isoformat()
    data["current_round"] = {
        "id": next_id,
        "name": meta.get("name", next_id),
        "status": "active",
        "updated_at": now,
    }
    data["last_completed_round"] = {
        "id": current_id,
        "completed_at": now,
    }
    data["acceptance_criteria"] = meta.get("acceptance_criteria", [])
    data["next_actions"] = meta.get("next_actions", [])
    data.setdefault("protocol_standard_sync_required", False)
    ROUND_STATE_PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    sync_project_round(next_id)
    return next_id


def sync_project_round(round_id: str) -> None:
    if yaml is None or not PROJECT_PATH.exists():
        return
    data = load_yaml(PROJECT_PATH)
    if not data:
        return
    proj = data.get("project")
    if isinstance(proj, dict):
        proj["current_round"] = round_id
        PROJECT_PATH.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def mark_current_round_completed(round_id: str) -> None:
    if yaml is None:
        return
    data = load_round_state()
    cur = data.get("current_round", {})
    if not isinstance(cur, dict):
        cur = {}
    now = datetime.now(timezone.utc).isoformat()
    cur["id"] = round_id
    cur["status"] = "completed"
    cur["completed_at"] = now.split("T")[0]
    meta = ROUND_META.get(round_id, {})
    cur.setdefault("name", meta.get("name", round_id))
    data["current_round"] = cur
    ROUND_STATE_PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def last_gate_commit_for_round(round_id: str) -> bool:
    code, out, _ = run_cmd(["git", "log", "-1", "--pretty=%s"])
    if code != 0:
        return False
    return f"complete {round_id}" in out


def safe_git_add(state: GateState) -> tuple[bool, list[str]]:
    rows = git_porcelain()
    if not rows:
        state.passed("workspace", "工作区干净，无需提交")
        return True, []
    to_add: list[str] = []
    for _xy, path in rows:
        if is_secret_path(path):
            state.block("secret_add", f"禁止暂存敏感文件: {path}")
            return False, []
        to_add.append(path)
    if not to_add:
        return True, []
    code, so, se = run_cmd(["git", "add", "--"] + to_add)
    if code != 0:
        state.block("git_add", se or so)
        return False, []
    state.passed("git_add", f"已暂存 {len(to_add)} 个路径")
    return True, to_add


def git_commit_round(round_id: str, state: GateState) -> tuple[bool, str]:
    if last_gate_commit_for_round(round_id):
        dirty = git_porcelain()
        if not dirty:
            state.passed("git_commit", f"已存在 {round_id} 的门控提交且无新变更，跳过")
            return True, "duplicate skipped"
    added_ok, _ = safe_git_add(state)
    if not added_ok:
        return False, state.findings[-1].message
    msg = f"chore(agent_gate): complete {round_id}\n\nAutomated round gate commit."
    code, so, se = run_cmd(["git", "commit", "-m", msg])
    combined = so + se
    if code != 0:
        if "nothing to commit" in combined:
            state.passed("git_commit", "nothing to commit")
            return True, "nothing to commit"
        state.block("git_commit", combined[:500])
        return False, combined[:500]
    state.passed("git_commit", "commit ok")
    return True, so.strip()


def git_push_main() -> tuple[bool, str]:
    code, so, se = run_cmd(["git", "push", "origin", "main"])
    if code != 0:
        return False, se or so
    return True, so.strip()


def write_report(state: GateState, extra: dict[str, str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Agent Gate Report",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- verdict: **{state.verdict}**",
        "",
    ]
    for f in state.findings:
        if f.severity != PASS:
            lines.append(f"- [{f.severity}] {f.check}: {f.message}")
    for k, v in extra.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Agent loop")
    lines.append("")
    lines.append("1. `python scripts/agent_gate.py status`")
    lines.append("2. 实现 `next_actions` / `acceptance_criteria`")
    lines.append("3. `python scripts/agent_gate.py gate` (exit 0)")
    lines.append("4. `python scripts/agent_gate.py advance --commit`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_gate() -> int:
    state = GateState()
    round_id = run_gate_checks(state)
    extra: dict[str, str] = {"current_round": round_id, "command": "gate"}
    write_report(state, extra)
    print(f"Agent gate: {state.verdict} (round={round_id})")
    if state.verdict == BLOCKED:
        print("修复上述 BLOCKED 项后重试: python scripts/agent_gate.py gate")
        return EXIT_CODE[BLOCKED]
    if state.verdict == WARNING:
        print("存在 WARNING，可继续低风险任务或修复后 gate")
    else:
        print(f"门控通过。下一步: {suggest_next_command(round_id, get_current_round_status())}")
    return EXIT_CODE[state.verdict]


def cmd_advance(*, do_commit: bool, do_push: bool) -> int:
    state = GateState()
    round_id = run_gate_checks(state)
    extra: dict[str, str] = {"current_round": round_id, "command": "advance"}

    print(f"Agent gate (advance): {state.verdict} (round={round_id})")
    if state.verdict == BLOCKED:
        write_report(state, extra)
        print("advance 中止：请先通过 gate")
        return EXIT_CODE[BLOCKED]

    if do_commit:
        committed, cmsg = git_commit_round(round_id, state)
        extra["git_commit"] = cmsg
        if not committed:
            write_report(state, extra)
            return EXIT_CODE[BLOCKED]
    else:
        extra["git_commit"] = "skipped (--commit 未指定)"

    mark_current_round_completed(round_id)
    nxt = advance_round_state(round_id)
    if nxt:
        extra["advanced_to"] = nxt
        print(f"Advanced round: {round_id} -> {nxt}")
        print(f"下一轮入口: python scripts/agent_gate.py status")
    else:
        extra["advanced_to"] = "complete"
        print("All scripted rounds complete; 见 docs/rounds.md 维护后续规划")

    if do_push:
        push_ok, push_msg = git_push_main()
        extra["git_push"] = push_msg if push_ok else f"failed: {push_msg}"
        if not push_ok:
            state.warn("git_push", push_msg[:300])
    else:
        extra["git_push"] = "skipped (默认不 push；需远程时用 --push)"

    write_report(state, extra)
    return EXIT_CODE[state.verdict]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="治理门控：status / gate / advance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="兼容旧参数：等价于子命令 gate",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    p_status = sub.add_parser("status", help="当前轮次与下一步建议")
    p_status.add_argument("--json", action="store_true", help="JSON 输出")

    sub.add_parser("gate", help="pytest + 冒烟 + 安全检查（默认）")

    p_adv = sub.add_parser("advance", help="gate 通过后推进 round_state")
    p_adv.add_argument(
        "--commit",
        action="store_true",
        help="门控通过后执行安全 git commit（无变更则跳过）",
    )
    p_adv.add_argument(
        "--push",
        action="store_true",
        help="提交后 push origin main（需人工授权，默认不 push）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = args.command
    if args.check_only and command is None:
        command = "gate"
    if command is None:
        command = "gate"

    if command == "status":
        return cmd_status(json_out=getattr(args, "json", False))
    if command == "gate":
        return cmd_gate()
    if command == "advance":
        return cmd_advance(do_commit=args.commit, do_push=args.push)

    parser.error(f"unknown command: {command}")
    return EXIT_CODE[BLOCKED]


if __name__ == "__main__":
    raise SystemExit(main())
