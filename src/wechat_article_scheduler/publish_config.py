"""发布任务级配置：批量预设置、到点自动发布。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from wechat_article_scheduler.config import AppConfig

VALID_PUBLISH_ACTIONS = frozenset({"draft", "publish", "inherit"})


@dataclass
class PublishConfig:
    """单篇发布任务的微信参数与执行策略。"""

    publish_action: str = "draft"
    auto_execute: bool = False
    need_open_comment: bool = False
    only_fans_can_comment: bool = False
    author: str = ""
    content_source_url: str = ""
    fixed_collection: str = ""

    def normalized(self) -> PublishConfig:
        action = (self.publish_action or "draft").strip().lower()
        if action not in VALID_PUBLISH_ACTIONS:
            action = "draft"
        return PublishConfig(
            publish_action=action,
            auto_execute=bool(self.auto_execute),
            need_open_comment=bool(self.need_open_comment),
            only_fans_can_comment=bool(self.only_fans_can_comment),
            author=(self.author or "").strip(),
            content_source_url=(self.content_source_url or "").strip(),
            fixed_collection=(self.fixed_collection or "").strip(),
        )


def defaults_from_rules(config: AppConfig) -> PublishConfig:
    """从 rules.yaml 的 publish 段读取默认配置。"""
    pub = config.rules.get("publish") if isinstance(config.rules.get("publish"), dict) else {}
    action = str(pub.get("default_action", "draft")).strip().lower()
    if action not in VALID_PUBLISH_ACTIONS:
        action = "draft"
    return PublishConfig(
        publish_action=action,
        auto_execute=bool(pub.get("auto_execute", False)),
        need_open_comment=bool(pub.get("need_open_comment", False)),
        only_fans_can_comment=bool(pub.get("only_fans_can_comment", False)),
        author=str(pub.get("author", "") or "").strip(),
        content_source_url=str(pub.get("content_source_url", "") or "").strip(),
    )


def parse_publish_config(
    raw: str | dict[str, Any] | None,
    *,
    defaults: PublishConfig | None = None,
) -> PublishConfig:
    """解析 publish_jobs.publish_config_json 或 API 请求体。"""
    base = (defaults or PublishConfig()).normalized()
    data: dict[str, Any] = {}
    if isinstance(raw, str) and raw.strip():
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                data = loaded
        except json.JSONDecodeError:
            return base
    elif isinstance(raw, dict):
        data = raw

    merged = PublishConfig(
        publish_action=str(data.get("publish_action", base.publish_action)),
        auto_execute=bool(data.get("auto_execute", base.auto_execute)),
        need_open_comment=bool(data.get("need_open_comment", base.need_open_comment)),
        only_fans_can_comment=bool(
            data.get("only_fans_can_comment", base.only_fans_can_comment)
        ),
        author=str(data.get("author", base.author) or ""),
        content_source_url=str(data.get("content_source_url", base.content_source_url) or ""),
        fixed_collection=str(data.get("fixed_collection", base.fixed_collection) or ""),
    )
    return merged.normalized()


def publish_config_to_json(config: PublishConfig) -> str:
    return json.dumps(asdict(config.normalized()), ensure_ascii=False)


def publish_config_from_payload(payload: dict[str, Any]) -> PublishConfig:
    """从 API 请求提取发布配置字段。"""
    keys = (
        "publish_action",
        "auto_execute",
        "need_open_comment",
        "only_fans_can_comment",
        "author",
        "content_source_url",
        "fixed_collection",
    )
    subset = {k: payload[k] for k in keys if k in payload}
    return parse_publish_config(subset)


def should_submit_publish(*, app_config: AppConfig, job_config: PublishConfig) -> bool:
    """是否应对该任务调用 freepublish/submit。"""
    action = job_config.publish_action
    if action == "draft":
        return False
    if action == "publish":
        return app_config.wechat_mode == "real" and bool(app_config.wechat_enable_publish)
    return app_config.wechat_mode == "real" and bool(app_config.wechat_enable_publish)


def human_publish_action_label(config: PublishConfig) -> str:
    action = config.publish_action
    if action == "publish":
        return "正式发布"
    if action == "draft":
        return "仅草稿"
    return "跟随全局"


def human_publish_config_summary(config: PublishConfig) -> list[str]:
    lines = [human_publish_action_label(config)]
    if config.auto_execute:
        lines.append("到点自动执行")
    if config.need_open_comment:
        lines.append("开启评论")
        if config.only_fans_can_comment:
            lines.append("仅粉丝可评")
    if config.author:
        lines.append(f"作者：{config.author[:20]}")
    if config.fixed_collection:
        lines.append(f"固定合集：{config.fixed_collection[:24]}")
    return lines
