"""个人博客 / WordPress local_blog 评估干跑（Round 28 / round_088）。"""

from __future__ import annotations

from typing import Any

LOCAL_BLOG_GUARDRAILS: list[str] = [
    "不向公网自动 POST 未经用户确认的 WordPress 站点",
    "凭证仅通过环境变量或本地配置文件读取，不得写入仓库",
    "写文件仅限用户配置的输出目录，禁止覆盖系统路径",
    "dry-run 不创建、不修改真实博客文件",
    "静态站导出成功仍需用户确认部署（CDN/托管）",
    "WordPress REST 需显式 base_url 与 application password",
]

STATIC_SITE_CHECKPOINTS: list[dict[str, str]] = [
    {"id": "outbox", "label": "准备内容", "instruction": "从 articles 或 manual_export 得到 Markdown/HTML"},
    {"id": "frontmatter", "label": "Front matter", "instruction": "标题、日期、标签、slug 与 Hugo/Jekyll 约定对齐"},
    {"id": "assets", "label": "静态资源", "instruction": "封面与图片复制到站点 assets 目录"},
    {"id": "build", "label": "本地构建", "instruction": "用户本地 hugo/jekyll/npm build，Agent 不代跑"},
    {"id": "deploy", "label": "部署", "instruction": "用户自行 rsync/GitHub Pages；记录部署 proof 可选"},
]

WORDPRESS_CHECKPOINTS: list[dict[str, str]] = [
    {"id": "credentials", "label": "凭证检查", "instruction": "WP_BASE_URL + WP_APP_PASSWORD 环境变量，不入库"},
    {"id": "draft_post", "label": "草稿创建", "instruction": "优先 draft 状态 POST /wp/v2/posts"},
    {"id": "media", "label": "特色图", "instruction": "上传媒体至 /wp/v2/media 后关联 featured_media"},
    {"id": "review", "label": "后台预览", "instruction": "用户在 WP 后台确认排版"},
    {"id": "publish", "label": "发布", "instruction": "用户显式发布；禁止无人值守 live"},
]

LOCAL_FILES_CHECKPOINTS: list[dict[str, str]] = [
    {"id": "target_dir", "label": "输出目录", "instruction": "用户配置 LOCAL_BLOG_OUTPUT_DIR"},
    {"id": "write_md", "label": "写入 Markdown", "instruction": "复制正文与元数据到约定文件名"},
    {"id": "symlink", "label": "索引更新", "instruction": "可选更新 posts 索引或 RSS，需人工确认"},
]

DESTINATION_META: dict[str, dict[str, Any]] = {
    "static_site": {
        "label": "静态站（Hugo/Jekyll/Hexo）",
        "platform": "static_site",
        "risk_level": "low",
        "recommendation": "recommended",
        "summary": "低风险：本地生成 Markdown + 用户自行 build/deploy，适合作为 Phase2 首选博客路径。",
        "checkpoints": STATIC_SITE_CHECKPOINTS,
        "output_artifacts": ["post.md", "assets/*", "frontmatter.yaml 片段"],
    },
    "wordpress": {
        "label": "WordPress REST API",
        "platform": "wordpress",
        "risk_level": "medium",
        "recommendation": "conditional",
        "summary": "中等风险：REST 草稿可行，但凭证管理与误发布需二次确认；无凭证时回退 manual_export。",
        "checkpoints": WORDPRESS_CHECKPOINTS,
        "output_artifacts": ["wp_draft_payload.json（干跑示意）", "media_upload_plan.json"],
    },
    "local_files": {
        "label": "本地文件目录",
        "platform": "local_blog",
        "risk_level": "low",
        "recommendation": "recommended",
        "summary": "将文章写入用户指定目录；不触网，适合 Obsidian/本地知识库同步。",
        "checkpoints": LOCAL_FILES_CHECKPOINTS,
        "output_artifacts": ["{slug}.md", "meta.json"],
    },
}

COMMON_STEPS: list[dict[str, str]] = [
    {
        "step_id": "preflight",
        "title": "内容预检",
        "actor": "scheduler",
        "detail": "校验标题、正文、封面路径；不写入目标目录",
    },
    {
        "step_id": "plan_outputs",
        "title": "生成输出计划",
        "actor": "local_blog",
        "detail": "干跑列出将写入的文件与字段映射",
    },
    {
        "step_id": "human_confirm",
        "title": "用户确认",
        "actor": "user",
        "detail": "确认目标路径与部署方式后再执行真实写入",
    },
    {
        "step_id": "optional_write",
        "title": "可选真实写入",
        "actor": "user",
        "detail": "非 dry-run 时由用户触发 CLI；默认 WECHAT_MODE=mock 不联网",
    },
]


def build_local_blog_dry_run_plan(
    *,
    destination: str = "static_site",
    article_id: str | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """local_blog 评估计划（dry-run，不写入、不调用 WordPress）。"""
    key = (destination or "static_site").strip().lower()
    meta = DESTINATION_META.get(key)
    if meta is None:
        raise ValueError(
            f"不支持的 local_blog destination：{destination}；"
            f"可选：{', '.join(DESTINATION_META)}"
        )
    assessment = {
        "risk_level": meta["risk_level"],
        "recommendation": meta["recommendation"],
        "summary": meta["summary"],
        "blockers": [
            "未配置输出目录时仅可干跑",
            "WordPress 需有效凭证与 HTTPS",
            "不得将博客发布等同于微信公众号已发布",
        ],
        "fallback": "优先 manual_export 或 static_site 本地 Markdown；REST 仅在有凭证时评估。",
    }
    return {
        "mode": "dry_run",
        "adapter_type": "local_blog",
        "destination": key,
        "platform": meta["platform"],
        "status": "evaluation_only",
        "terminal_policy": "不得自动标记为跨平台 published",
        "article_id": article_id,
        "output_dir_hint": output_dir or "${LOCAL_BLOG_OUTPUT_DIR:-./outbox/local_blog}",
        "guardrails": LOCAL_BLOG_GUARDRAILS,
        "human_checkpoints": list(meta["checkpoints"]),
        "steps": list(COMMON_STEPS),
        "assessment": assessment,
        "output_artifacts": list(meta["output_artifacts"]),
        "wordpress_env_hints": (
            ["WP_BASE_URL", "WP_APP_PASSWORD", "WP_POST_STATUS=draft"]
            if key == "wordpress"
            else []
        ),
        "proof_placeholder": {
            "public_url": None,
            "deploy_note": None,
            "confirmed_by": None,
        },
    }
