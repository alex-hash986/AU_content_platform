import httpx

from app.services.publishers.base import (
    BasePublisher, PublishError, PublishResult, external_id, mock_result, request, required,
)


class VKPublisher(BasePublisher):
    credential_key = "access_token"
    required_credentials = ("owner_id",)

    async def publish(self, title: str, text: str, cta: str, credentials: dict) -> PublishResult:
        token = credentials.get(self.credential_key)
        if not token:
            return mock_result("mock_vk_123")
        try:
            required(credentials, *self.required_credentials)
            owner_id = str(credentials["owner_id"])
            payload = {
                "access_token": token,
                "owner_id": owner_id,
                "message": "\n\n".join((title, text, cta)),
                "v": credentials.get("api_version", "5.199"),
            }
            if owner_id.startswith("-"):
                payload["from_group"] = "1"
            async with httpx.AsyncClient(timeout=15) as client:
                data = await request(client, "POST", "https://api.vk.com/method/wall.post", data=payload)
            result = data.get("response")
            if not isinstance(result, dict):
                raise PublishError("VK rejected the wall post")
            return PublishResult(success=True, external_id=external_id(result.get("post_id")))
        except PublishError as exc:
            return PublishResult(success=False, error=str(exc))
