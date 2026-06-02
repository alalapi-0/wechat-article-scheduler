"""微信适配器抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DraftResult:
    """创建草稿后的结果（mock 也会返回假 media_id）。"""

    media_id: str
    raw_response: dict


@dataclass
class DraftOptions:
    """创建草稿时的微信图文参数。"""

    need_open_comment: int = 0
    only_fans_can_comment: int = 0
    author: str = ""
    content_source_url: str = ""


class WechatAdapter(ABC):
    """公众号草稿/发布适配器接口。"""

    @abstractmethod
    def create_draft(
        self,
        *,
        title: str,
        summary: str,
        body: str,
        cover_path: str | None = None,
        options: DraftOptions | None = None,
    ) -> DraftResult:
        """将图文写入草稿箱（或 mock 记录）。cover_path 为该篇作品的本地封面，缺省回退默认封面。"""

    @abstractmethod
    def update_draft(
        self,
        *,
        media_id: str,
        title: str,
        summary: str,
        body: str,
        cover_path: str | None = None,
        options: DraftOptions | None = None,
        index: int = 0,
    ) -> DraftResult:
        """更新已有草稿（微信 draft/update；mock 仅更新本地记录语义）。"""

    @abstractmethod
    def submit_publish(self, media_id: str, *, force: bool = False) -> dict:
        """提交发布（mock 仅返回成功结构）。force=True 只能由全局开关和任务级确认共同决定。"""
