"""微信公众号字段能力矩阵（Round 17 / round_072）。"""

from __future__ import annotations

from typing import Any, TypedDict


class FieldCapability(TypedDict):
    field_id: str
    label: str
    api_support: str  # supported | partial | unsupported | unverified | n/a
    implemented: str  # yes | partial | no | n/a
    gap: str
    handling: str
    code_refs: str


# api_support: 微信官方草稿/发布 API 是否覆盖该字段（据当前文档与实现，非法律结论）
# implemented: 本仓库是否已接线
WECHAT_FIELD_MATRIX: list[FieldCapability] = [
    {
        "field_id": "title",
        "label": "标题",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "无",
        "handling": "draft/add 与 draft/update 的 articles.title",
        "code_refs": "adapters/real.py, publish_preview",
    },
    {
        "field_id": "digest",
        "label": "摘要",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "超长自动截断至 120 字",
        "handling": "clamp_summary + digest_truncated_warning 事件",
        "code_refs": "parser.py, scheduler/domain.py",
    },
    {
        "field_id": "body",
        "label": "正文 HTML",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "Markdown 渲染与标题去重需预检",
        "handling": "render_for_publish 后写入 content",
        "code_refs": "publish_preview.py, renderers/",
    },
    {
        "field_id": "author",
        "label": "作者",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "无",
        "handling": "PublishConfig.author → DraftOptions",
        "code_refs": "publish_config.py, adapters/real.py",
    },
    {
        "field_id": "content_source_url",
        "label": "原文链接",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "无",
        "handling": "PublishConfig.content_source_url",
        "code_refs": "publish_config.py",
    },
    {
        "field_id": "need_open_comment",
        "label": "开启留言",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "无",
        "handling": "草稿 articles.need_open_comment",
        "code_refs": "publish_config.py",
    },
    {
        "field_id": "only_fans_can_comment",
        "label": "仅粉丝可留言",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "依赖开启留言",
        "handling": "articles.only_fans_can_comment",
        "code_refs": "publish_config.py",
    },
    {
        "field_id": "cover_thumb",
        "label": "封面素材",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "缺封面时用默认图或占位 PNG",
        "handling": "material/add_material → thumb_media_id",
        "code_refs": "adapters/real.py, articles.cover_path",
    },
    {
        "field_id": "cover_crop",
        "label": "封面裁剪区域",
        "api_support": "unverified",
        "implemented": "partial",
        "gap": "cover_config_json 仅存本地，未确认写入微信 API",
        "handling": "工作台可设裁剪；发布前需人工核对后台效果",
        "code_refs": "articles.cover_config_json, web/covers",
    },
    {
        "field_id": "local_schedule",
        "label": "本地排期时间",
        "api_support": "n/a",
        "implemented": "yes",
        "gap": "非微信字段，仅存 publish_jobs.scheduled_at",
        "handling": "本地 scheduler 到点执行",
        "code_refs": "plan.py, scheduler/runtime.py",
    },
    {
        "field_id": "wechat_backend_schedule",
        "label": "公众号后台定时群发",
        "api_support": "unverified",
        "implemented": "no",
        "gap": "未写入微信后台定时字段",
        "handling": "待核验官方 API；不支持则 browser_assist + 人工确认",
        "code_refs": "docs/wechat_capability_matrix.md",
    },
    {
        "field_id": "draft_create",
        "label": "草稿创建",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "无",
        "handling": "draft/add；mock 本地 media_id",
        "code_refs": "adapters/real.py, adapters/mock.py",
    },
    {
        "field_id": "draft_update",
        "label": "草稿更新",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "需已有 media_id；内容未变则跳过",
        "handling": "draft/update + draft_update.py",
        "code_refs": "draft_update.py",
    },
    {
        "field_id": "freepublish",
        "label": "正式发布",
        "api_support": "supported",
        "implemented": "yes",
        "gap": "受 WECHAT_ENABLE_PUBLISH 与任务级 draft 限制",
        "handling": "freepublish/submit；二次确认",
        "code_refs": "adapters/real.py, web/publish_preflight",
    },
    {
        "field_id": "show_cover_pic",
        "label": "封面显示在正文中",
        "api_support": "unverified",
        "implemented": "no",
        "gap": "未单独映射微信 show_cover_pic 等字段",
        "handling": "标记待核验；默认不声称支持",
        "code_refs": "—",
    },
]

REQUIRED_KEYS = frozenset(FieldCapability.__annotations__.keys())
API_SUPPORT_VALUES = frozenset({"supported", "partial", "unsupported", "unverified", "n/a"})
IMPLEMENTED_VALUES = frozenset({"yes", "partial", "no", "n/a"})


def list_field_matrix() -> list[dict[str, Any]]:
    return [dict(row) for row in WECHAT_FIELD_MATRIX]


def field_gaps() -> list[dict[str, Any]]:
    """需关注或人工处理的字段。"""
    out: list[dict[str, Any]] = []
    for row in WECHAT_FIELD_MATRIX:
        if row["api_support"] in ("unsupported", "unverified") or row["implemented"] in (
            "no",
            "partial",
        ):
            out.append(dict(row))
    return out


def matrix_summary() -> dict[str, Any]:
    rows = WECHAT_FIELD_MATRIX
    return {
        "total": len(rows),
        "implemented_yes": sum(1 for r in rows if r["implemented"] == "yes"),
        "gaps_count": len(field_gaps()),
        "unverified_api": [r["field_id"] for r in rows if r["api_support"] == "unverified"],
    }
