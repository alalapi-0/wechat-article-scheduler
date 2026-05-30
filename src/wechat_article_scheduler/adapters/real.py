"""真实微信公众平台 API 适配器骨架（默认不启用）。"""

from __future__ import annotations

from wechat_article_scheduler.adapters.base import DraftResult, WechatAdapter


class RealWechatAdapter(WechatAdapter):
    """
    真实 API 调用占位实现。

    Round 3 起可在此接入 access_token、draft/add、freepublish/submit。
    当前调用会抛出 NotImplementedError，避免误发真实请求。
    """

    def __init__(self, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret

    def _ensure_credentials(self) -> None:
        if not self._app_id or not self._app_secret:
            raise RuntimeError("WECHAT_APP_ID / WECHAT_APP_SECRET 未配置，无法使用 real 模式")

    def build_token_request_url(self) -> str:
        """
        构造获取 access_token 的 URL（Round 3 占位，不自动请求）。

        文档：https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
        """
        self._ensure_credentials()
        return (
            "https://api.weixin.qq.com/cgi-bin/token"
            f"?grant_type=client_credential&appid={self._app_id}&secret=***REDACTED***"
        )

    def create_draft(self, *, title: str, summary: str, body: str) -> DraftResult:
        self._ensure_credentials()
        # 待实现：GET token -> POST cgi-bin/draft/add
        raise NotImplementedError(
            "RealWechatAdapter.create_draft 尚未实现；请保持 WECHAT_MODE=mock 或完成 Round 3 集成"
        )

    def submit_publish(self, media_id: str) -> dict:
        self._ensure_credentials()
        raise NotImplementedError(
            "RealWechatAdapter.submit_publish 尚未实现；发布请使用 mock 或完成 Round 3"
        )
