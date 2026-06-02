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

# 权威路线图：docs/rounds.md（Round 0–102，脚本轮注册表）。修改路线图时须同步本表与 tests/test_agent_gate.py。
# 里程碑：round_000–101 Phase0–4；round_102 维护收口；round_103+ Phase5 多项目 manifest 等见 roadmap。
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
    "round_039",
    "round_040",
    "round_041",
    "round_042",
    "round_043",
    "round_044",
    "round_045",
    "round_046",
    "round_047",
    "round_048",
    "round_049",
    "round_050",
    "round_051",
    "round_052",
    "round_053",
    "round_054",
    "round_055",
    "round_056",
    "round_057",
    "round_058",
    "round_059",
    "round_060",
    "round_061",
    "round_062",
    "round_063",
    "round_064",
    "round_065",
    "round_066",
    "round_067",
    "round_068",
    "round_069",
    "round_070",
    "round_071",
    "round_072",
    "round_073",
    "round_074",
    "round_075",
    "round_076",
    "round_077",
    "round_078",
    "round_079",
    "round_080",
    "round_081",
    "round_082",
    "round_083",
    "round_084",
    "round_085",
    "round_086",
    "round_087",
    "round_088",
    "round_089",
    "round_090",
    "round_091",
    "round_092",
    "round_093",
    "round_094",
    "round_095",
    "round_096",
    "round_097",
    "round_098",
    "round_099",
    "round_100",
    "round_101",
    "round_102",
    "round_103",
    "round_104",
    "round_105",
    "round_106",
    "round_107",
    "round_108",
    "round_109",
    "round_110",
    "round_111",
    "round_112",
    "round_113",
    "round_114",
    "round_115",
    "round_116",
    "round_117",
    "round_118",
    "round_119",
    "round_120",
    "round_121",
    "round_122",
    "round_123",
    "round_124",
    "round_125",
    "round_126",
    "round_127",
    "round_128",
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
            "推进 Round 39：Web 审核闸门",
        ],
    },
    "round_039": {
        "name": "Round 39 - Web 发布前确认入口",
        "acceptance_criteria": [
            "Web 执行到点前给出可读发布确认与预检提示",
            "真实发布需显式开关与确认，普通视图不裸露内部枚举",
        ],
        "next_actions": [
            "推进 Round 40：定时发布 UX",
        ],
    },
    "round_040": {
        "name": "Round 40 - 定时发布 UX",
        "acceptance_criteria": [
            "概览与发布队列展示人话计划时间",
            "下一篇待发布摘要在普通视图可读",
        ],
        "next_actions": [
            "推进 Round 41：真实发布预检清单",
        ],
    },
    "round_041": {
        "name": "Round 41 - 真实发布预检清单",
        "acceptance_criteria": [
            "真实模式提供发布前检查 API 与人话摘要",
            "执行到点前展示阻断/提示项",
        ],
        "next_actions": [
            "推进 Round 42：能力矩阵维护",
        ],
    },
    "round_042": {
        "name": "Round 42 - 能力矩阵维护",
        "acceptance_criteria": [
            "wechat_capability_matrix 与已实现能力同步",
            "路线图 Phase 9 维护轮次可 gate 校验",
        ],
        "next_actions": [
            "推进 Round 43：产品重定位与审核概念移除",
        ],
    },
    "round_043": {
        "name": "Round 43 - 产品重定位与审核概念移除",
        "acceptance_criteria": [
            "全仓 src 无 review_status 引用，init-db 后 articles 表无该列",
            "scan/plan/run-once 与 mock 路径不受影响",
        ],
        "next_actions": [
            "推进 Round 44：网页批量上传作品与封面",
        ],
    },
    "round_044": {
        "name": "Round 44 - 网页批量上传作品与封面",
        "acceptance_criteria": [
            "POST /api/upload 支持多文件上传文章与封面",
            "封面按文件名绑定到对应作品，mock 全流程可发布",
        ],
        "next_actions": [
            "推进 Round 45：工作台界面与配色重构",
        ],
    },
    "round_045": {
        "name": "Round 45 - 工作台界面与配色重构",
        "acceptance_criteria": [
            "首屏以作品库与上传区为中心，移除审核区块",
            "普通视图不裸露内部字段，窄屏无整页横向溢出",
        ],
        "next_actions": [
            "推进 Round 46：发布确认护栏与能力矩阵收口",
        ],
    },
    "round_046": {
        "name": "Round 46 - 发布确认护栏与能力矩阵收口",
        "acceptance_criteria": [
            "发布前二次确认与预检替代审核门禁",
            "能力矩阵与文档同步，受影响测试全绿",
        ],
        "next_actions": [
            "推进 Round 47：轻量 UI 细节修正",
        ],
    },
    "round_047": {
        "name": "Round 47 - 轻量 UI 细节修正",
        "acceptance_criteria": [
            "左上角品牌标识不突兀，作品列表与按钮视觉更克制",
            "普通视图不回归审核概念或内部字段",
        ],
        "next_actions": [
            "推进 Round 48：微信草稿正文规范化与标题去重",
        ],
    },
    "round_048": {
        "name": "Round 48 - 微信草稿正文规范化与标题去重",
        "acceptance_criteria": [
            "草稿 payload title 正确，content 不含重复首标题",
            "Markdown / frontmatter / HTML 标题去重有测试覆盖",
        ],
        "next_actions": [
            "推进 Round 49：公众号效果预览修正",
        ],
    },
    "round_049": {
        "name": "Round 49 - 公众号效果预览修正",
        "acceptance_criteria": [
            "预览弹窗展示可读正文，不显示 HTML 标签源码",
            "Web 预览与真实 draft 共用同源渲染入口",
        ],
        "next_actions": [
            "推进 Round 50：作品回收站与可逆删除",
        ],
    },
    "round_050": {
        "name": "Round 50 - 作品回收站与可逆删除",
        "acceptance_criteria": [
            "作品可从页面删除进入回收站，作品库/队列默认隐藏",
            "回收站作品可恢复且不影响未删除作品",
        ],
        "next_actions": [
            "推进 Round 51：清空回收站与彻底删除",
        ],
    },
    "round_051": {
        "name": "Round 51 - 清空回收站与彻底删除",
        "acceptance_criteria": [
            "清空后数据库和本地文章/封面文件按安全范围彻底删除",
            "危险操作有二次确认且不会删除项目外路径",
        ],
        "next_actions": [
            "推进 Round 52：批量管理与删除一致性",
        ],
    },
    "round_052": {
        "name": "Round 52 - 批量管理与删除一致性",
        "acceptance_criteria": [
            "作品、封面、未完成任务、回收站项都有清晰删除/恢复路径",
            "批量操作不会影响未选中作品",
        ],
        "next_actions": [
            "推进 Round 53：发布前内容质量检查",
        ],
    },
    "round_053": {
        "name": "Round 53 - 发布前内容质量检查",
        "acceptance_criteria": [
            "预检可发现标题重复、正文为空、疑似 HTML 源码等质量问题",
            "真实发布路径对严重内容问题给出明确阻断或提示",
        ],
        "next_actions": [
            "推进 Round 54：真实微信 API 闭环验证",
        ],
    },
    "round_054": {
        "name": "Round 54 - 真实微信 API 闭环验证",
        "acceptance_criteria": [
            "real_api_check 在 real 模式下完成样本草稿验证并保存报告",
            "不泄露 token；WECHAT_ENABLE_PUBLISH 关闭时不提交发布",
        ],
        "next_actions": [
            "推进 Round 55：Auto-Approved Real API Pipeline",
        ],
    },
    "round_055": {
        "name": "Round 55 - Auto-Approved Real API Pipeline",
        "acceptance_criteria": [
            "auto_approve_pipeline 在 real 模式下完成真实草稿并自动标记 auto_approved",
            "报告写入 reports/auto_approve_pipeline/ 与 reports/real_api_runs/",
            "下游 scan/run-once 可继续执行且不等待人工审核",
        ],
        "next_actions": [
            "推进 Round 56：路线收敛治理轮",
        ],
    },
    "round_056": {
        "name": "Round 56 - 路线收敛治理轮",
        "acceptance_criteria": [
            "路线发散审计、产品愿景、架构、收敛路线图与平台优先级已更新",
            "不破坏微信公众号 scan/plan/run-once/草稿创建链路",
            "默认 mock 不联网；real 模式用于真实 API 测试；browser_assist 只作为个人本地自用后备方案",
        ],
        "next_actions": [
            "推进 Round 57：收敛后微信链路稳定化",
        ],
    },
    "round_057": {
        "name": "Round 57 - 收敛后微信链路稳定化（启动）",
        "acceptance_criteria": [
            "scan/plan/run-once mock 主链路测试通过",
            "draft-only 与正式发布路径在文档和测试中可区分",
        ],
        "next_actions": [
            "推进 Round 58：摘要、错误码与幂等（收敛 Phase 1 Round 3）",
        ],
    },
    "round_058": {
        "name": "Round 58 - 摘要错误码与草稿幂等",
        "acceptance_criteria": [
            "摘要 120 字统一截断且超长有 warning 事件",
            "常见微信 errcode 有可读 human_hint",
            "相同 content_hash 不重复 create_draft",
        ],
        "next_actions": [
            "推进 Round 59：微信公众号 HTML 渲染器（收敛 Phase 1 Round 4）",
        ],
    },
    "round_059": {
        "name": "Round 59 - 微信公众号 HTML 渲染器",
        "acceptance_criteria": [
            "预览与 draft/add 使用同源 render_for_publish",
            "Markdown 标题/列表/引用/代码/内联样式稳定输出",
            "正文不重复标题",
        ],
        "next_actions": [
            "推进 Round 60：公众号效果预览快照",
        ],
    },
    "round_060": {
        "name": "Round 60 - 公众号效果预览快照",
        "acceptance_criteria": [
            "统一预览包含摘要、正文 HTML、封面与 content_hints",
            "预览与 draft content 同源并标注近似说明",
            "快照可经 API/CLI 写入 storage/preview_snapshots",
        ],
        "next_actions": [
            "推进 Round 61：封面资产管理",
        ],
    },
    "round_061": {
        "name": "Round 61 - 封面资产管理",
        "acceptance_criteria": [
            "封面素材库可扫描并汇总绑定/孤儿状态",
            "按作品文件名 stem 可自动绑定封面",
            "无效 cover_path 可修复；孤儿封面可安全清理",
        ],
        "next_actions": [
            "推进 Round 62：封面裁剪与双比例预览",
        ],
    },
    "round_062": {
        "name": "Round 62 - 封面裁剪与双比例预览",
        "acceptance_criteria": [
            "桌面 Web 可预览横向 2.35:1 与方形 1:1 封面",
            "cover_config 含 crop/focal 并可保存",
            "无 Pillow 时 CSS 预览降级且测试通过",
        ],
        "next_actions": [
            "推进 Round 63：多合集内容库",
        ],
    },
    "round_063": {
        "name": "Round 63 - 多合集内容库",
        "acceptance_criteria": [
            "content/collections/*/collection.yaml 可发现并同步",
            "scan 兼容 articles/inbox 根目录与各合集 inbox",
            "Web/API 可按合集筛选作品",
        ],
        "next_actions": [
            "推进 Round 64：合集排期规则",
        ],
    },
    "round_064": {
        "name": "Round 64 - 合集排期规则",
        "acceptance_criteria": [
            "collection.yaml schedule 块可解析并参与 plan",
            "按合集 max_per_day / 偏好时段 / stagger 错峰",
            "plan 返回 by_collection 与可读 hints",
        ],
        "next_actions": [
            "推进 Round 65：Web 控制台 MVP（收敛 Round 10）",
        ],
    },
    "round_065": {
        "name": "Round 65 - Web 控制台 MVP",
        "acceptance_criteria": [
            "Dashboard 概览含下一步提示与统计",
            "scan/plan/run-once 入口与普通用户队列筛选",
            "普通视图默认隐藏高级信息；8080 核心 API 无失败",
        ],
        "next_actions": [
            "推进 Round 66：文章详情与预览页面",
        ],
    },
    "round_066": {
        "name": "Round 66 - 文章详情与预览页面",
        "acceptance_criteria": [
            "GET /articles/{id} 详情页与 /api/articles/{id} API",
            "展示封面、摘要、排期、草稿状态与发布前检查",
            "正文 render-preview 集成；mock 草稿有演练说明",
        ],
        "next_actions": [
            "推进 Round 67：发布队列页面",
        ],
    },
    "round_067": {
        "name": "Round 67 - 发布队列页面",
        "acceptance_criteria": [
            "队列表格含计划时间、状态、失败原因与下一步提示",
            "单条/批量重试失败任务 API",
            "队列筛选与 queue-summary 摘要",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 13：草稿管理页面",
        ],
    },
    "round_068": {
        "name": "Round 68 - 微信草稿管理页面",
        "acceptance_criteria": [
            "wechat_drafts 列表/筛选/关联作品 API",
            "工作台 #drafts 与 /drafts 页面",
            "mock 演练说明，不误导为公众号后台全量草稿",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 14：本地 scheduler 稳定化",
        ],
    },
    "round_069": {
        "name": "Round 69 - 本地 scheduler 稳定化",
        "acceptance_criteria": [
            "run-once 原子 claim 与单实例锁",
            "失败退避重试、stale running 恢复、misfire 事件",
            "scheduler-health CLI 与稳定性测试",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 15：scheduler 常驻运行文档",
        ],
    },
    "round_070": {
        "name": "Round 70 - Scheduler 常驻运行文档",
        "acceptance_criteria": [
            "scheduler_runbook：launchd/systemd/cron/tmux 与故障处理",
            "deploy/examples/scheduler 可运行示例与包装脚本",
            "README/用户手册/scheduler-daemon CLI",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 16：微信草稿更新能力",
        ],
    },
    "round_071": {
        "name": "Round 71 - 微信草稿更新能力",
        "acceptance_criteria": [
            "mock/real update_draft 与 draft/update 路径",
            "内容指纹幂等；superseded 历史不丢 media_id",
            "CLI/Web 更新入口与测试",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 17：微信公众号字段能力矩阵核验",
        ],
    },
    "round_072": {
        "name": "Round 72 - 微信字段能力矩阵核验",
        "acceptance_criteria": [
            "字段级矩阵：API 支持/实现/缺口/处理方式",
            "wechat_field_matrix.py 与文档同步",
            "CLI field-matrix 与 /api/wechat-field-matrix",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 18：browser_assist 方案",
        ],
    },
    "round_073": {
        "name": "Round 73 - browser_assist 后备流程",
        "acceptance_criteria": [
            "操作清单、人工确认点、guardrails 文档与代码一致",
            "build_dry_run_plan 止于 awaiting_human_confirmation",
            "CLI browser-assist-plan 与 /api/browser-assist-plan",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 19：人工确认与 proof 记录",
        ],
    },
    "round_074": {
        "name": "Round 74 - 人工确认与 proof 记录",
        "acceptance_criteria": [
            "publish_proofs 表与 proof 字段文档",
            "无 proof 时 waiting_confirmation 不得标为已发布",
            "Web/CLI/API 提交 proof 入口",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 20：可选正式发布",
        ],
    },
    "round_075": {
        "name": "Round 75 - 可选正式发布策略",
        "acceptance_criteria": [
            "WECHAT_ENABLE_PUBLISH 与任务级 draft/publish 可区分",
            "publish_policy 与 UI 徽章、预检任务分布",
            "全局草稿-only 不调用 freepublish/submit",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续 Round 21：闭环验收",
        ],
    },
    "round_076": {
        "name": "Round 76 - 微信公众号闭环验收",
        "acceptance_criteria": [
            "wechat_mvp_acceptance.md 验收清单",
            "核心模块可导入、路线图 Round 21 对齐",
            "回归测试入口文档化",
        ],
        "next_actions": [
            "Phase 1 完成后按 backlog 评估 Phase 2",
        ],
    },
    "round_077": {
        "name": "Round 77 - manual_export 通用 outbox",
        "acceptance_criteria": [
            "export-outbox 生成 md/html/manifest/说明",
            "不联网、不标记已发布",
            "Web/CLI/API 与作品详情导出入口",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续文本平台模板与 outbox 索引",
        ],
    },
    "round_078": {
        "name": "Round 78 - Phase 2 平台提示包",
        "acceptance_criteria": [
            "zhihu/douban 平台 copy 提示文件",
            "phase2_text_platforms.md 启动说明",
            "outbox 列表 API 可在 /debug 查看",
        ],
        "next_actions": [
            "评估知乎/豆瓣 browser_assist（backlog）",
        ],
    },
    "round_079": {
        "name": "Round 79 - 知乎发布包模板",
        "acceptance_criteria": [
            "zhihu 专用字段文件与发布清单",
            "CLI/Web --platform zhihu 与详情页导出入口",
            "不联网、不自动发布、需 proof",
        ],
        "next_actions": [
            "按 docs/roadmap_converged.md 继续豆瓣发布包或知乎 browser_assist 评估",
        ],
    },
    "round_080": {
        "name": "Round 80 - 豆瓣发布包模板",
        "acceptance_criteria": [
            "douban 专用字段与标签提示文件",
            "platform=douban 导出与 API 平台列表",
            "不声称 API 已支持",
        ],
        "next_actions": [
            "评估知乎/豆瓣 browser_assist（backlog）",
        ],
    },
    "round_081": {
        "name": "Round 81 - 知乎 browser_assist 评估",
        "acceptance_criteria": [
            "zhihu dry-run 计划含 checkpoints 与 assessment",
            "CLI/Web/debug 入口 platform=zhihu",
            "不绕过登录/验证码、不自动发布",
        ],
        "next_actions": [
            "微信 browser_assist 平台列表 API 或豆瓣 browser_assist 评估",
        ],
    },
    "round_082": {
        "name": "Round 82 - browser_assist 多平台入口",
        "acceptance_criteria": [
            "/api/browser-assist/platforms 含微信",
            "微信干跑计划默认 platform 兼容",
            "文档与测试更新",
        ],
        "next_actions": [
            "豆瓣 browser_assist 评估或微信闭环修复",
        ],
    },
    "round_083": {
        "name": "Round 83 - 豆瓣 browser_assist 评估",
        "acceptance_criteria": [
            "douban dry-run 含 checkpoints 与 assessment",
            "platform=douban API/CLI/debug",
            "不自动发布、不绕过登录",
        ],
        "next_actions": [
            "Phase 2 文本平台 browser_assist 索引收口",
        ],
    },
    "round_084": {
        "name": "Round 84 - Phase2 browser_assist 收口",
        "acceptance_criteria": [
            "三平台 browser_assist 均在 platforms API",
            "phase2 文档更新",
            "zhihu/douban/wechat 计划可生成",
        ],
        "next_actions": [
            "Adapter registry 能力声明（round_085）",
        ],
    },
    "round_085": {
        "name": "Round 85 - Adapter Registry 能力声明",
        "acceptance_criteria": [
            "BUILTIN_CAPABILITIES 含微信与 Phase2 平台",
            "/api/adapter-registry 与 CLI adapter-registry",
            "不替代现有 get_adapter 运行时",
        ],
        "next_actions": [
            "publish_manifest 校验（round_086）",
        ],
    },
    "round_086": {
        "name": "Round 86 - publish_manifest 校验",
        "acceptance_criteria": [
            "validate_manifest 与示例 JSON",
            "manifest-validate CLI",
            "不写 SQLite",
        ],
        "next_actions": [
            "manifest 干跑 content_package（round_087）",
        ],
    },
    "round_087": {
        "name": "Round 87 - manifest 干跑 content_package",
        "acceptance_criteria": [
            "manifest_to_drafts 与 registry_checks",
            "manifest-dry-run CLI 与 sample API",
            "/debug 可见 registry 与干跑 JSON",
        ],
        "next_actions": [
            "local_blog 博客评估 round_088",
        ],
    },
    "round_088": {
        "name": "Round 88 - 个人博客 local_blog 评估",
        "acceptance_criteria": [
            "static_site/wordpress/local_files dry-run 计划",
            "registry 含 local_blog 能力",
            "local-blog-plan CLI 与 /debug",
        ],
        "next_actions": [
            "Webhook 评估 round_089",
        ],
    },
    "round_089": {
        "name": "Round 89 - Webhook 适配器评估",
        "acceptance_criteria": [
            "webhook dry-run 不发起 HTTP",
            "notification+webhook 在 registry",
            "webhook-plan CLI 与 /debug",
        ],
        "next_actions": [
            "Phase3 视频预研 round_090",
        ],
    },
    "round_090": {
        "name": "Round 90 - Phase3 视频内容包预研",
        "acceptance_criteria": [
            "video_package dry-run 与三平台占位",
            "registry bilibili/wechat_channels 占位",
            "video manifest 校验与 sample JSON",
        ],
        "next_actions": [
            "微信闭环链路摘要 round_091",
        ],
    },
    "round_091": {
        "name": "Round 91 - 微信闭环链路摘要",
        "acceptance_criteria": [
            "wechat-chain-summary CLI/API",
            "overview 含 recommended_next_action",
            "scan/plan 主线不回归",
        ],
        "next_actions": [
            "Bilibili manual_export round_092",
        ],
    },
    "round_092": {
        "name": "Round 92 - Bilibili manual_export 发布包",
        "acceptance_criteria": [
            "export-outbox --platform bilibili 生成完整文件集",
            "含 video placeholder 与 upload checklist",
            "不真上传、不标已发布",
        ],
        "next_actions": [
            "Bilibili browser_assist 评估 round_093",
        ],
    },
    "round_093": {
        "name": "Round 93 - Bilibili browser_assist 评估",
        "acceptance_criteria": [
            "platform=bilibili browser-assist-plan",
            "browser-assist/platforms 含 bilibili",
            "/debug 可见 bilibili 评估 JSON",
        ],
        "next_actions": [
            "小红书发布包 round_094",
        ],
    },
    "round_094": {
        "name": "Round 94 - 小红书 manual_export 发布包",
        "acceptance_criteria": [
            "export-outbox --platform xiaohongshu 文件集完整",
            "含 media placeholder 与 checklist",
            "不真上传",
        ],
        "next_actions": [
            "小红书 browser_assist round_095",
        ],
    },
    "round_095": {
        "name": "Round 95 - 小红书 browser_assist 评估",
        "acceptance_criteria": [
            "platform=xiaohongshu dry-run assessment deferred",
            "browser-assist/platforms 含 xiaohongshu",
            "/debug 可见小红书 JSON",
        ],
        "next_actions": [
            "微信视频号发布包 round_096",
        ],
    },
    "round_096": {
        "name": "Round 96 - 微信视频号 manual_export",
        "acceptance_criteria": [
            "export-outbox --platform wechat_channels 完整文件集",
            "channels_article_link_note 明示与公众号分离",
            "不真上传视频",
        ],
        "next_actions": [
            "视频号 browser_assist round_097",
        ],
    },
    "round_097": {
        "name": "Round 97 - 微信视频号 browser_assist",
        "acceptance_criteria": [
            "platform=wechat_channels dry-run",
            "terminal_policy 区分视频号与公众号",
            "/debug 可见视频号 JSON",
        ],
        "next_actions": [
            "抖音/快手发布包 round_098",
        ],
    },
    "round_098": {
        "name": "Round 98 - 抖音/快手 manual_export 骨架",
        "acceptance_criteria": [
            "export-outbox douyin 与 kuaishou 文件集",
            "含 video placeholder 与 deferred 说明",
            "不真上传",
        ],
        "next_actions": [
            "短视频 deferred 评估 round_099",
        ],
    },
    "round_099": {
        "name": "Round 99 - 抖音/快手 deferred 评估",
        "acceptance_criteria": [
            "short-video-plan recommendation=deferred",
            "registry douyin/kuaishou manual_export",
            "/debug 可见抖音/快手 JSON",
        ],
        "next_actions": [
            "Phase4 音频预研 round_100",
        ],
    },
    "round_100": {
        "name": "Round 100 - Phase4 音频/播客预研",
        "acceptance_criteria": [
            "audio/podcast manifest 校验",
            "audio-package-plan dry-run",
            "registry podcast/netease 占位",
        ],
        "next_actions": [
            "工作台链路提示 round_101",
        ],
    },
    "round_101": {
        "name": "Round 101 - 微信工作台链路提示增强",
        "acceptance_criteria": [
            "overview.workbench 含 recommended_cli",
            "空库时 primary_action=scan",
            "test_workbench_chain_hints 通过",
        ],
        "next_actions": [
            "维护收口 round_102",
        ],
    },
    "round_102": {
        "name": "Round 102 - 脚本轮维护收口",
        "acceptance_criteria": [
            "docs/rounds.md 与 ROUND_ORDER 同步",
            "全量 pytest + maintenance API 冒烟",
            "mock 主链路 scan→plan→预览→队列→草稿→debug API",
        ],
        "next_actions": [
            "Phase5 多项目 manifest round_103",
        ],
    },
    "round_103": {
        "name": "Round 103 - Phase5 多项目 manifest 干跑",
        "acceptance_criteria": [
            "projects.example.yaml 与 registry 加载",
            "多项目 manifest dry-run CLI/API",
            "/debug Phase5 区块",
            "不替代 scan/plan",
        ],
        "next_actions": [
            "round_104 跨项目发布日历预研",
        ],
    },
    "round_104": {
        "name": "Round 104 - Phase5 跨项目发布日历预研",
        "acceptance_criteria": [
            "manifest scheduled_at 日历 dry-run 视图",
            "同账号冲突检测",
            "publish-calendar API 与 /debug",
            "不写 SQLite publish_jobs",
        ],
        "next_actions": [
            "round_105 统一 outbox 预研",
        ],
    },
    "round_105": {
        "name": "Round 105 - Phase5 统一 outbox 预研",
        "acceptance_criteria": [
            "outbox 目录只读索引与按平台聚合",
            "publish_manifest 汇总 dry-run",
            "unified-outbox API 与 /debug",
            "不移动真实文件",
        ],
        "next_actions": [
            "round_106 长期运维预研",
        ],
    },
    "round_106": {
        "name": "Round 106 - Phase5 长期运维预研",
        "acceptance_criteria": [
            "ops runbook 检查清单 dry-run",
            "健康指标聚合 API",
            "不修改生产 cron",
        ],
        "next_actions": [
            "round_107 Phase5 收口",
        ],
    },
    "round_107": {
        "name": "Round 107 - Phase5 收口摘要",
        "acceptance_criteria": [
            "phase5-closure-summary API",
            "round_103-106 模块 ok 聚合",
            "docs/phase5_closure.md",
        ],
        "next_actions": [
            "微信 P0 强化 round_108",
        ],
    },
    "round_108": {
        "name": "Round 108 - 微信 P0 主线小步强化",
        "summary": "overview/status 联动 publish_preflight；队列摘要与 AUTO_APPROVE",
        "acceptance_criteria": [
            "overview 联动 publish_preflight",
            "status 暴露 AUTO_APPROVE 标识",
            "队列摘要含 preflight_ready",
            "mock@8080 核心路径浏览器验证",
        ],
        "next_actions": [
            "推进 round_109 作品预检与队列失败重试",
        ],
    },
    "round_109": {
        "name": "Round 109 - 微信 P0 续（预检条与失败队列）",
        "summary": "作品/详情预检条；失败队列 Tab 重试与 failed_preview",
        "acceptance_criteria": [
            "作品详情/卡片预检条与 blocking 联动",
            "队列失败 Tab 重试入口与错误摘要增强",
            "mock@8080 核心路径浏览器验证",
        ],
        "next_actions": [
            "推进 round_110 执行到点与预检联动",
        ],
    },
    "round_110": {
        "name": "Round 110 - 执行到点与预检 blocking 联动",
        "summary": "执行到点预检 blocking 禁用；run-once toast 与事件刷新",
        "acceptance_criteria": [
            "执行到点按钮预检 blocking 禁用与原因文案",
            "run-once 结果 toast 与事件区刷新",
            "mock@8080 点击执行到点路径验证",
        ],
        "next_actions": [
            "推进 round_111 生成排期与待确认入口",
        ],
    },
    "round_111": {
        "name": "Round 111 - 生成排期与待人工确认入口",
        "summary": "生成排期 plan_gate；首页与队列待人工确认入口",
        "acceptance_criteria": [
            "生成排期与 publish_preflight plan_gate 联动",
            "首页待人工确认队列入口与队列筛选",
            "mock@8080 点击生成排期与待确认路径验证",
        ],
        "next_actions": [
            "推进 round_112 扫描收件箱反馈增强",
        ],
    },
    "round_112": {
        "name": "Round 112 - 扫描收件箱反馈与链路联动",
        "summary": "扫描 toast/scan_summary；与 chain_summary 联动",
        "acceptance_criteria": [
            "扫描 toast 与 scan_summary 摘要",
            "scan 结果与 chain_summary 联动展示",
            "scan 前轻量预检 inbox 路径",
            "mock@8080 点击扫描路径验证",
        ],
        "next_actions": [
            "推进 round_113 待确认快速 proof",
        ],
    },
    "round_113": {
        "name": "Round 113 - 待确认快速 proof",
        "summary": "待确认 Tab 快速 dry-run proof；详情 #proof 锚点",
        "acceptance_criteria": [
            "待人工确认 Tab 快速提交 dry-run proof",
            "AUTO_APPROVE 标识与详情 #proof 跳转",
            "mock@8080 点击待确认与快速确认路径",
        ],
        "next_actions": [
            "推进 round_114 上传与 outbox 快捷导出",
        ],
    },
    "round_114": {
        "name": "Round 114 - 上传反馈与 outbox 快捷导出",
        "summary": "上传 .md 与 scan 联动；作品卡导出 outbox",
        "acceptance_criteria": [
            "上传 .md toast 与 scan 联动提示",
            "作品卡导出 outbox 按钮",
            "mock@8080 上传与导出路径验证",
        ],
        "next_actions": [
            "推进 round_115 仓库卫生与冒烟扩展",
        ],
    },
    "round_115": {
        "name": "Round 115 - 仓库卫生与维护冒烟",
        "summary": "gitignore outbox/MCP；test_round_102 扩展 upload/export",
        "acceptance_criteria": [
            ".gitignore 忽略 outbox 测试包与 .playwright-mcp",
            "test_round_102 覆盖上传/export-outbox API",
            "git status 无密钥；mock@8080 首页回归",
        ],
        "next_actions": [
            "推进 round_116 高级信息持久化与 Desktop-first",
        ],
    },
    "round_116": {
        "name": "Round 116 - 高级信息持久化",
        "summary": "高级信息 localStorage；默认隐藏 /debug 与 JSON",
        "acceptance_criteria": [
            "高级信息开关 localStorage 持久化",
            "默认隐藏 /debug 与内部 JSON 区块",
            "mock@8080 开关切换与刷新保持",
        ],
        "next_actions": [
            "推进 round_117 合集筛选持久化",
        ],
    },
    "round_117": {
        "name": "Round 117 - 合集筛选持久化",
        "summary": "作品库合集下拉 localStorage 持久化",
        "acceptance_criteria": [
            "合集下拉 localStorage 持久化",
            "刷新后恢复筛选",
            "mock@8080 筛选与无横向溢出",
        ],
        "next_actions": [
            "推进 round_118 队列 Tab 筛选持久化",
        ],
    },
    "round_118": {
        "name": "Round 118 - 队列 Tab 筛选持久化",
        "summary": "发布队列状态 Tab localStorage 持久化",
        "acceptance_criteria": [
            "发布队列 Tab localStorage 持久化",
            "刷新后恢复 Tab 状态",
            "mock@8080 切换失败/待发布 Tab",
        ],
        "next_actions": [
            "推进 round_119 hash 深链与区块恢复",
        ],
    },
    "round_119": {
        "name": "Round 119 - Hash 深链与区块恢复",
        "summary": "#queue/#works/#drafts 深链；刷新恢复区块",
        "acceptance_criteria": [
            "#queue/#works/#drafts 深链与 #articles 别名",
            "刷新后恢复区块并与 queue/collection localStorage 协同",
            "mock@8080 /#queue 直达",
        ],
        "next_actions": [
            "推进 round_120 详情返回保留 hash",
        ],
    },
    "round_120": {
        "name": "Round 120 - 详情返回保留工作台上下文",
        "summary": "详情返回链接保留来源 hash；与 localStorage 协同",
        "acceptance_criteria": [
            "返回工作台链接保留 #queue/#works",
            "与 queue/collection localStorage 协同",
            "mock@8080 队列→详情→返回",
        ],
        "next_actions": [
            "推进 round_121 详情链接统一捕获",
        ],
    },
    "round_121": {
        "name": "Round 121 - 详情链接统一捕获",
        "summary": "队列/作品卡详情链接触发 captureWorkbenchReturnContext",
        "acceptance_criteria": [
            "队列表格与作品卡详情链接触发 capture",
            "refreshWorkbenchDetailLinkBindings 兜底",
            "mock@8080 /#queue 点详情→返回",
        ],
        "next_actions": [
            "推进 round_122 文档同步与维护冒烟",
        ],
    },
    "round_122": {
        "name": "Round 122 - 文档同步与维护冒烟",
        "summary": "登记 108–121 抛光摘要；102 hash/返回断言；README 里程碑",
        "acceptance_criteria": [
            "docs/rounds.md 108–121 摘要表",
            "ROUND_META summary 简述",
            "test_round_102 hash/返回上下文断言",
            "mock@8080 /#queue 冒烟",
        ],
        "next_actions": [
            "推进 round_123 高级面板路线图位置",
        ],
    },
    "round_123": {
        "name": "Round 123 - 高级面板路线图位置",
        "summary": "status 暴露 roadmap_hint/last_completed_round；高级区显示位置与 backlog 链接",
        "acceptance_criteria": [
            "/api/status 只读 roadmap_hint 与 last_completed_round",
            "高级面板 advRoadmap 显示位置与 doc 链接",
            "mock@8080 开启高级信息后可见",
        ],
        "next_actions": [
            "推进 round_124 agent-gate-status API",
        ],
    },
    "round_124": {
        "name": "Round 124 - Agent gate 状态 API",
        "summary": "GET /api/agent-gate-status 只读；高级面板 advAgentGate 展示 gate 摘要",
        "acceptance_criteria": [
            "GET /api/agent-gate-status 与 CLI status 结构一致",
            "高级面板 advAgentGate 展示 gate_summary 与 next_actions",
            "mock@8080 开启高级信息后可见",
        ],
        "next_actions": [
            "推进 round_125 作品卡导出下拉",
        ],
    },
    "round_125": {
        "name": "Round 125 - 作品卡导出下拉",
        "summary": "作品卡导出下拉：generic + manual_export 平台；复用 export-outbox API",
        "acceptance_criteria": [
            "GET /api/manual-export/platforms 驱动导出菜单",
            "POST export-outbox 按所选平台导出",
            "mock@8080 点击导出一种平台",
        ],
        "next_actions": [
            "推进 round_126 详情页导出下拉",
        ],
    },
    "round_126": {
        "name": "Round 126 - 详情页导出下拉",
        "summary": "详情页导出下拉对齐 round_125；复用 platforms + export-outbox",
        "acceptance_criteria": [
            "详情页 export-drop 联动 manual-export/platforms",
            "POST export-outbox 按所选平台导出",
            "mock@8080 /articles/{id} 点击导出一种平台",
        ],
        "next_actions": [
            "推进 round_127 统一 export toast",
        ],
    },
    "round_127": {
        "name": "Round 127 - 统一 export-outbox 成功 toast",
        "summary": "共用 ExportOutboxUi：平台名、路径、未自动发布醒目文案",
        "acceptance_criteria": [
            "/assets/export-outbox-ui.js 工作台与详情共用",
            "成功 toast 含平台中文名与 outbox 路径",
            "mock@8080 作品卡与详情各验证一种平台",
        ],
        "next_actions": [
            "推进 round_128 普通视图 export toast 回归",
        ],
    },
    "round_128": {
        "name": "Round 128 - 普通视图 export toast 回归",
        "summary": "普通视图作品卡导出 toast 含未自动发布；test_128 + E2E",
        "acceptance_criteria": [
            "test_round_128 普通视图导出下拉与 toast 文案",
            "test_round_127 回归",
            "mock@8080 普通视图导出（可选）",
        ],
        "next_actions": [
            "在 docs/rounds.md 规划 round_129 后续能力",
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
        steps = [
            (
                [py, "-m", "pytest", "tests/test_web_ordinary_copy.py", "tests/test_web_app.py", "-q"],
                "pytest web ordinary copy",
            ),
        ]
    elif round_id == "round_035":
        steps = [
            ([py, "-m", "pytest", "tests/test_ui_e2e.py", "-q"], "pytest ui e2e"),
        ]
    elif round_id in {"round_036", "round_037", "round_038"}:
        steps = [([py, "-m", "pytest", "tests/test_agent_gate.py", "-q"], "pytest agent gate")]
    elif round_id == "round_039":
        steps = [([py, "-m", "pytest", "tests/test_scheduler_hardening.py", "tests/test_web_round39_plus.py", "-q"], "pytest review gate")]
    elif round_id == "round_040":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_web_round39_plus.py", "tests/test_web_ordinary_copy.py", "-q"],
                "pytest schedule ux",
            ),
        ]
    elif round_id == "round_041":
        steps = [([py, "-m", "pytest", "tests/test_web_round39_plus.py", "tests/test_web_app.py", "-q"], "pytest preflight")]
    elif round_id == "round_042":
        steps = [([py, "-m", "pytest", "tests/test_agent_gate.py", "-q"], "pytest agent gate")]
    elif round_id == "round_043":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_migrations.py", "tests/test_content_library.py", "tests/test_scheduler_hardening.py", "-q"],
                "pytest review removal",
            ),
        ]
    elif round_id == "round_044":
        steps = [([py, "-m", "pytest", "tests/test_web_upload.py", "-q"], "pytest web upload")]
    elif round_id == "round_045":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_web_app.py", "tests/test_web_ordinary_copy.py", "-q"],
                "pytest web ui",
            ),
        ]
    elif round_id == "round_046":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_agent_gate.py", "tests/test_web_round39_plus.py", "-q"],
                "pytest preflight/matrix",
            ),
        ]
    elif round_id == "round_047":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_web_app.py", "tests/test_web_ordinary_copy.py", "-q"],
                "pytest ui polish",
            ),
        ]
    elif round_id == "round_048":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_parser.py", "tests/test_renderer_markdown.py", "tests/test_real_adapter.py", "-q"],
                "pytest title/body rendering",
            ),
        ]
    elif round_id == "round_049":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_publish_preview.py", "tests/test_web_app.py", "-q"],
                "pytest publish preview",
            ),
        ]
    elif round_id in {"round_050", "round_051"}:
        steps = [([py, "-m", "pytest", "tests/test_web_trash.py", "-q"], "pytest trash")]
    elif round_id == "round_052":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_web_trash.py", "tests/test_ui_e2e.py", "-q"],
                "pytest bulk delete/e2e",
            ),
        ]
    elif round_id == "round_053":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_content_quality.py",
                    "tests/test_web_round39_plus.py",
                    "tests/test_publish_preview.py",
                    "-q",
                ],
                "pytest content quality",
            ),
        ]
    elif round_id == "round_054":
        steps = [
            ([py, "-m", "pytest", "tests/test_real_api_check.py", "-q"], "pytest real_api_check"),
        ]
    elif round_id == "round_055":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_auto_approve_pipeline.py", "-q"],
                "pytest auto_approve_pipeline",
            ),
        ]
    elif round_id == "round_056":
        steps = [
            ([py, "scripts/check_rounds_doc.py"], "check rounds doc"),
            ([py, "-m", "pytest", "tests/test_agent_gate.py", "tests/test_check_rounds_doc.py", "-q"], "pytest governance"),
        ]
    elif round_id == "round_057":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_wechat_chain_stability.py", "tests/test_scheduler_hardening.py", "-q"],
                "pytest wechat chain stability",
            ),
        ]
    elif round_id == "round_058":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_digest_limits.py",
                    "tests/test_wechat_digest_errors_idempotency.py",
                    "tests/test_real_adapter.py",
                    "-q",
                ],
                "pytest digest errors idempotency",
            ),
        ]
    elif round_id == "round_059":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_wechat_renderer.py", "tests/test_publish_preview.py", "-q"],
                "pytest wechat html renderer",
            ),
        ]
    elif round_id == "round_060":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_preview_snapshot.py",
                    "tests/test_web_app.py",
                    "-q",
                    "-k",
                    "preview",
                ],
                "pytest preview snapshot",
            ),
        ]
    elif round_id == "round_061":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_cover_manager.py",
                    "tests/test_cover_assets.py",
                    "-q",
                ],
                "pytest cover asset management",
            ),
        ]
    elif round_id == "round_062":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_cover_crop_preview.py",
                    "tests/test_web_batch_select.py",
                    "-q",
                ],
                "pytest cover crop dual preview",
            ),
        ]
    elif round_id == "round_063":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_multi_collection.py",
                    "tests/test_content_library.py",
                    "-q",
                ],
                "pytest multi collection library",
            ),
        ]
    elif round_id == "round_064":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_collection_schedule.py",
                    "tests/test_web_schedule.py",
                    "-q",
                ],
                "pytest collection schedule rules",
            ),
        ]
    elif round_id == "round_065":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_web_console_mvp.py",
                    "tests/test_web_app.py",
                    "-q",
                ],
                "pytest web console mvp",
            ),
        ]
    elif round_id == "round_066":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_article_detail_page.py",
                    "tests/test_web_app.py",
                    "-q",
                ],
                "pytest article detail preview",
            ),
        ]
    elif round_id == "round_067":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_publish_queue_page.py",
                    "tests/test_web_console_mvp.py",
                    "-q",
                ],
                "pytest publish queue page",
            ),
        ]
    elif round_id == "round_068":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_wechat_drafts_page.py",
                    "tests/test_web_console_mvp.py",
                    "-q",
                ],
                "pytest wechat drafts page",
            ),
        ]
    elif round_id == "round_069":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_scheduler_stability.py",
                    "tests/test_scheduler_hardening.py",
                    "-q",
                ],
                "pytest scheduler stability",
            ),
        ]
    elif round_id == "round_070":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_scheduler_runbook.py",
                    "-q",
                ],
                "pytest scheduler runbook",
            ),
        ]
    elif round_id == "round_071":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_draft_update.py",
                    "tests/test_mock_adapter.py",
                    "tests/test_real_adapter.py",
                    "-q",
                ],
                "pytest draft update",
            ),
        ]
    elif round_id == "round_072":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_wechat_field_matrix.py",
                    "-q",
                ],
                "pytest wechat field matrix",
            ),
        ]
    elif round_id == "round_073":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_browser_assist_workflow.py",
                    "-q",
                ],
                "pytest browser assist workflow",
            ),
        ]
    elif round_id == "round_074":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_publish_proof.py",
                    "-q",
                ],
                "pytest publish proof",
            ),
        ]
    elif round_id == "round_075":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_optional_real_publish.py",
                    "tests/test_publish_config.py",
                    "-q",
                ],
                "pytest optional real publish",
            ),
        ]
    elif round_id == "round_076":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_wechat_mvp_acceptance.py",
                    "tests/test_wechat_chain_stability.py",
                    "-q",
                ],
                "pytest wechat mvp acceptance",
            ),
        ]
    elif round_id == "round_077":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_manual_export.py",
                    "-q",
                ],
                "pytest manual export",
            ),
        ]
    elif round_id == "round_078":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_manual_export_platform.py",
                    "-q",
                ],
                "pytest manual export platform",
            ),
        ]
    elif round_id == "round_079":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_zhihu_publish_pack.py",
                    "-q",
                ],
                "pytest zhihu publish pack",
            ),
        ]
    elif round_id == "round_080":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_douban_publish_pack.py",
                    "-q",
                ],
                "pytest douban publish pack",
            ),
        ]
    elif round_id == "round_081":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_zhihu_browser_assist.py",
                    "-q",
                ],
                "pytest zhihu browser assist",
            ),
        ]
    elif round_id == "round_082":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_browser_assist_platforms.py",
                    "tests/test_browser_assist_workflow.py",
                    "-q",
                ],
                "pytest browser assist platforms",
            ),
        ]
    elif round_id == "round_083":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_douban_browser_assist.py",
                    "-q",
                ],
                "pytest douban browser assist",
            ),
        ]
    elif round_id == "round_084":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_phase2_browser_assist_index.py",
                    "-q",
                ],
                "pytest phase2 browser assist index",
            ),
        ]
    elif round_id == "round_085":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_adapter_registry.py", "-q"],
                "pytest adapter registry",
            ),
        ]
    elif round_id == "round_086":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_manifest_validate.py", "-q"],
                "pytest manifest validate",
            ),
        ]
    elif round_id == "round_087":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_manifest_dry_run.py", "-q"],
                "pytest manifest dry run",
            ),
        ]
    elif round_id == "round_088":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_local_blog_eval.py", "-q"],
                "pytest local blog eval",
            ),
        ]
    elif round_id == "round_089":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_webhook_eval.py", "-q"],
                "pytest webhook eval",
            ),
        ]
    elif round_id == "round_090":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_video_presearch.py", "-q"],
                "pytest video presearch",
            ),
        ]
    elif round_id == "round_091":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_wechat_chain_summary.py",
                    "tests/test_wechat_chain_stability.py",
                    "-q",
                ],
                "pytest wechat chain summary and stability",
            ),
        ]
    elif round_id == "round_092":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_bilibili_publish_pack.py", "-q"],
                "pytest bilibili publish pack",
            ),
        ]
    elif round_id == "round_093":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_bilibili_browser_assist.py", "-q"],
                "pytest bilibili browser assist",
            ),
        ]
    elif round_id == "round_094":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_xiaohongshu_publish_pack.py", "-q"],
                "pytest xiaohongshu publish pack",
            ),
        ]
    elif round_id == "round_095":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_xiaohongshu_browser_assist.py", "-q"],
                "pytest xiaohongshu browser assist",
            ),
        ]
    elif round_id == "round_096":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_wechat_channels_publish_pack.py", "-q"],
                "pytest wechat channels publish pack",
            ),
        ]
    elif round_id == "round_097":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_wechat_channels_browser_assist.py", "-q"],
                "pytest wechat channels browser assist",
            ),
        ]
    elif round_id == "round_098":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_douyin_kuaishou_publish_pack.py", "-q"],
                "pytest douyin kuaishou publish pack",
            ),
        ]
    elif round_id == "round_099":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_short_video_deferred.py", "-q"],
                "pytest short video deferred",
            ),
        ]
    elif round_id == "round_100":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_audio_presearch.py", "-q"],
                "pytest audio presearch",
            ),
        ]
    elif round_id == "round_101":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_workbench_chain_hints.py",
                    "tests/test_web_console_mvp.py",
                    "-q",
                ],
                "pytest workbench chain hints",
            ),
        ]
    elif round_id == "round_102":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_102_maintenance_smoke.py", "-q"],
                "pytest round_102 maintenance smoke",
            ),
            (
                [py, "-m", "pytest", "tests/test_agent_gate.py", "-q"],
                "pytest agent_gate registry",
            ),
        ]
    elif round_id == "round_103":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_multi_project_dry_run.py", "-q"],
                "pytest multi-project dry-run",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_manifest_validate.py",
                    "tests/test_manifest_dry_run.py",
                    "-q",
                ],
                "pytest manifest round_086/087 regression",
            ),
        ]
    elif round_id == "round_104":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_cross_project_calendar.py", "-q"],
                "pytest cross-project calendar",
            ),
            (
                [py, "-m", "pytest", "tests/test_multi_project_dry_run.py", "-q"],
                "pytest multi-project regression",
            ),
        ]
    elif round_id == "round_105":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_unified_outbox_presearch.py", "-q"],
                "pytest unified outbox presearch",
            ),
            (
                [py, "-m", "pytest", "tests/test_cross_project_calendar.py", "-q"],
                "pytest phase5 calendar regression",
            ),
        ]
    elif round_id == "round_106":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_ops_health_presearch.py", "-q"],
                "pytest ops health presearch",
            ),
            (
                [py, "-m", "pytest", "tests/test_scheduler_runbook.py", "-q"],
                "pytest scheduler runbook regression",
            ),
        ]
    elif round_id == "round_107":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_phase5_closure.py", "-q"],
                "pytest phase5 closure",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_multi_project_dry_run.py",
                    "tests/test_unified_outbox_presearch.py",
                    "-q",
                ],
                "pytest phase5 regression",
            ),
        ]
    elif round_id == "round_108":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_108_wechat_p0.py", "-q"],
                "pytest wechat p0 round_108",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_web_console_mvp.py",
                    "tests/test_workbench_chain_hints.py",
                    "-q",
                ],
                "pytest web mvp regression",
            ),
        ]
    elif round_id == "round_109":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_109_wechat_p0.py", "-q"],
                "pytest wechat p0 round_109",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_round_108_wechat_p0.py",
                    "tests/test_web_console_mvp.py",
                    "-q",
                ],
                "pytest wechat regression",
            ),
        ]
    elif round_id == "round_110":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_110_wechat_p0.py", "-q"],
                "pytest wechat p0 round_110",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_round_109_wechat_p0.py",
                    "tests/test_web_console_mvp.py",
                    "-q",
                ],
                "pytest wechat regression",
            ),
        ]
    elif round_id == "round_111":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_111_wechat_p0.py", "-q"],
                "pytest wechat p0 round_111",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_round_110_wechat_p0.py",
                    "tests/test_publish_proof.py",
                    "-q",
                ],
                "pytest wechat regression",
            ),
        ]
    elif round_id == "round_112":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_112_wechat_p0.py", "-q"],
                "pytest wechat p0 round_112",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_wechat_chain_summary.py",
                    "tests/test_web_console_mvp.py",
                    "-q",
                ],
                "pytest wechat regression",
            ),
        ]
    elif round_id == "round_113":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_113_wechat_p0.py", "-q"],
                "pytest wechat p0 round_113",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_publish_proof.py",
                    "tests/test_round_111_wechat_p0.py",
                    "-q",
                ],
                "pytest proof regression",
            ),
        ]
    elif round_id == "round_114":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_114_wechat_p0.py", "-q"],
                "pytest wechat p0 round_114",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_web_upload.py",
                    "tests/test_manual_export.py",
                    "-q",
                ],
                "pytest upload export regression",
            ),
        ]
    elif round_id == "round_115":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_102_maintenance_smoke.py", "-q"],
                "pytest maintenance smoke round_115",
            ),
            (
                [py, "-m", "pytest", "tests/test_round_114_wechat_p0.py", "-q"],
                "pytest round_114 regression",
            ),
        ]
    elif round_id == "round_116":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_116_wechat_p0.py", "-q"],
                "pytest wechat p0 round_116",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_web_ordinary_copy.py",
                    "tests/test_ui_e2e.py::test_ordinary_view_e2e_baseline",
                    "-q",
                ],
                "pytest ordinary view regression",
            ),
        ]
    elif round_id == "round_117":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_117_wechat_p0.py", "-q"],
                "pytest wechat p0 round_117",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_ui_e2e.py::test_ordinary_view_e2e_baseline",
                    "-q",
                ],
                "pytest desktop overflow regression",
            ),
        ]
    elif round_id == "round_118":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_118_wechat_p0.py", "-q"],
                "pytest wechat p0 round_118",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_ui_e2e.py::test_ordinary_view_e2e_baseline",
                    "-q",
                ],
                "pytest ordinary view regression",
            ),
        ]
    elif round_id == "round_119":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_119_wechat_p0.py", "-q"],
                "pytest wechat p0 round_119",
            ),
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_round_118_wechat_p0.py",
                    "tests/test_round_117_wechat_p0.py",
                    "-q",
                ],
                "pytest persistence regression",
            ),
        ]
    elif round_id == "round_120":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_120_wechat_p0.py", "-q"],
                "pytest wechat p0 round_120",
            ),
            (
                [py, "-m", "pytest", "tests/test_round_119_wechat_p0.py", "-q"],
                "pytest hash deep link regression",
            ),
        ]
    elif round_id == "round_121":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_121_wechat_p0.py", "-q"],
                "pytest wechat p0 round_121",
            ),
            (
                [py, "-m", "pytest", "tests/test_round_120_wechat_p0.py", "-q"],
                "pytest return context regression",
            ),
        ]
    elif round_id == "round_122":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_122_wechat_p0.py", "-q"],
                "pytest wechat p0 round_122",
            ),
            (
                [py, "-m", "pytest", "tests/test_round_102_maintenance_smoke.py", "-q"],
                "pytest maintenance smoke round_122",
            ),
        ]
    elif round_id == "round_123":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_123_wechat_p0.py", "-q"],
                "pytest wechat p0 round_123",
            ),
        ]
    elif round_id == "round_124":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_124_wechat_p0.py", "-q"],
                "pytest wechat p0 round_124",
            ),
        ]
    elif round_id == "round_125":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_125_wechat_p0.py", "-q"],
                "pytest wechat p0 round_125",
            ),
            (
                [py, "-m", "pytest", "tests/test_round_114_wechat_p0.py::test_export_outbox_api", "-q"],
                "pytest export-outbox regression",
            ),
        ]
    elif round_id == "round_126":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_126_wechat_p0.py", "-q"],
                "pytest wechat p0 round_126",
            ),
            (
                [py, "-m", "pytest", "tests/test_round_125_wechat_p0.py::test_manual_export_platforms_api", "-q"],
                "pytest platforms api regression",
            ),
        ]
    elif round_id == "round_127":
        steps = [
            (
                [py, "-m", "pytest", "tests/test_round_127_wechat_p0.py", "-q"],
                "pytest wechat p0 round_127",
            ),
            (
                [py, "-m", "pytest", "tests/test_round_126_wechat_p0.py::test_detail_page_export_dropdown_markup", "-q"],
                "pytest detail export regression",
            ),
        ]
    elif round_id == "round_128":
        steps = [
            (
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_round_128_wechat_p0.py",
                    "tests/test_round_127_wechat_p0.py",
                    "-q",
                ],
                "pytest wechat p0 round_128",
            ),
        ]
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


def build_status_payload() -> dict[str, Any]:
    """与 ``agent_gate status`` 一致的只读 JSON（无密钥、无 git 输出）。"""
    data = load_round_state()
    round_id = get_current_round_id()
    cur = data.get("current_round", {}) if isinstance(data.get("current_round"), dict) else {}
    status = str(cur.get("status", "active"))
    acceptance = (
        data.get("acceptance_criteria")
        or ROUND_META.get(round_id, {}).get("acceptance_criteria", [])
    )
    next_actions = (
        data.get("next_actions") or ROUND_META.get(round_id, {}).get("next_actions", [])
    )
    if not isinstance(acceptance, list):
        acceptance = []
    if not isinstance(next_actions, list):
        next_actions = []
    acceptance = [str(x) for x in acceptance]
    next_actions = [str(x) for x in next_actions]

    lcr_raw = data.get("last_completed_round")
    last_completed_round: dict[str, str] | None = None
    if isinstance(lcr_raw, dict) and lcr_raw.get("id"):
        last_completed_round = {
            "id": str(lcr_raw.get("id", "")),
            "completed_at": str(lcr_raw.get("completed_at", "")),
        }

    name = str(cur.get("name") or ROUND_META.get(round_id, {}).get("name", round_id))
    return {
        "current_round": {
            "id": round_id,
            "name": name,
            "status": status,
        },
        "last_completed_round": last_completed_round,
        "next_actions": next_actions,
        "acceptance_criteria": acceptance,
        "protocol_standard_sync_required": bool(
            data.get("protocol_standard_sync_required", False)
        ),
        "suggested_command": suggest_next_command(round_id, status),
        "docs": str(ROUNDS_DOC.relative_to(ROOT)),
        "gate_summary": (
            f"{round_id} · {name}（{status}）— "
            f"{len(acceptance)} 项验收 · {len(next_actions)} 条 next_actions"
        ),
    }


def cmd_status(*, json_out: bool) -> int:
    payload = build_status_payload()
    round_id = payload["current_round"]["id"]
    status = payload["current_round"]["status"]
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
        if yaml is not None:
            data = load_round_state()
            now = datetime.now(timezone.utc).isoformat()
            data["last_completed_round"] = {
                "id": round_id,
                "completed_at": now,
            }
            ROUND_STATE_PATH.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
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
