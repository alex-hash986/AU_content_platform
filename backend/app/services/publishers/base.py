import logging
from abc import ABC, abstractmethod
from html import escape

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PublishResult(BaseModel):
    success: bool
    external_id: str | None = None
    error: str | None = None


class PublishError(Exception):
    """An error message safe to store and return through the API."""


class BasePublisher(ABC):
    credential_key: str
    required_credentials: tuple[str, ...]

    @abstractmethod
    async def publish(
        self, title: str, text: str, cta: str, credentials: dict
    ) -> PublishResult:
        raise NotImplementedError


def mock_result(external_id: str) -> PublishResult:
    logger.info("Simulating publication (%s)", external_id)
    return PublishResult(success=True, external_id=external_id)


def required(credentials: dict, *keys: str) -> None:
    missing = [key for key in keys if not credentials.get(key)]
    if missing:
        raise PublishError("Missing channel settings: " + ", ".join(missing))


def content_html(text: str, cta: str) -> str:
    blocks = (text.strip() + "\n\n" + cta.strip()).split("\n\n")
    return "".join(
        f"<p>{escape(block).replace(chr(10), '<br>')}</p>" for block in blocks if block
    )


async def request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> dict:
    try:
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise PublishError(f"Channel API returned HTTP {exc.response.status_code}") from None
    except (httpx.RequestError, httpx.InvalidURL):
        raise PublishError("Channel API connection failed") from None

    if response.status_code == 204:
        return {}
    try:
        result = response.json()
    except ValueError:
        raise PublishError("Channel API returned invalid JSON") from None
    if not isinstance(result, dict):
        raise PublishError("Channel API returned an unexpected response")
    return result


def external_id(value: object) -> str:
    if not isinstance(value, (int, str)) or isinstance(value, bool) or not str(value).strip():
        raise PublishError("Channel API did not return a publication ID")
    return str(value)
