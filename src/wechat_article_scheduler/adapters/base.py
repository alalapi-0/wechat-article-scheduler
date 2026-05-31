"""微信适配器抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DraftResult:
    """创建草稿后的结果（mock 也会返回假 media_id）。"""

    media_id: str
    raw_response: dict


class WechatAdapter(ABC):
    """公众号草稿/发布适配器接口。"""

    @abstractmethod
    def create_draft(
        self, *, title: str, summary: str, body: str, cover_path: str | None = None
    ) -> DraftResult:
        """将图文写入草稿箱（或 mock 记录）。cover_path 为该篇作品的本地封面，缺省回退默认封面。"""

    @abstractmethod
    def submit_publish(self, media_id: str) -> dict:
        """提交发布（mock 仅返回成功结构）。"""
