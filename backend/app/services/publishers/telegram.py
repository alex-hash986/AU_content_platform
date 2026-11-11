import logging
from html import escape

import httpx

from app.services.publishers.base import (
    BasePublisher, PublishError, PublishResult, external_id, mock_result, request, required,
)


class TelegramTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # HTTPX includes the request URL in its INFO logs, including the Bot API token.
        return "https://api.telegram.org/bot" not in record.getMessage()


logging.getLogger("httpx").addFilter(TelegramTokenFilter())


class TelegramPublisher(BasePublisher):
    credential_key = "bot_token"
    required_credentials = ("chat_id",)

    async def publish(self, title: str, text: str, cta: str, credentials: dict) -> PublishResult:
        token = credentials.get(self.credential_key)
        if not token:
            return mock_result("mock_tg_123")
        try:
            required(credentials, *self.required_credentials)
            message = f"<b>{escape(title)}</b>\n\n{escape(text)}\n\n{escape(cta)}"
            async with httpx.AsyncClient(timeout=15) as client:
                data = await request(
                    client, "POST", f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": credentials["chat_id"], "text": message, "parse_mode": "HTML"},
                )
            result = data.get("result")
            if not data.get("ok") or not isinstance(result, dict):
                raise PublishError("Telegram rejected the message")
            return PublishResult(success=True, external_id=external_id(result.get("message_id")))
        except PublishError as exc:
            return PublishResult(success=False, error=str(exc))
