import asyncio

import httpx

from app.services.publishers.base import (
    BasePublisher, PublishError, PublishResult, external_id, mock_result, request, required,
)


class InstagramPublisher(BasePublisher):
    credential_key = "access_token"
    required_credentials = ("ig_user_id", "image_url")

    async def publish(self, title: str, text: str, cta: str, credentials: dict) -> PublishResult:
        token = credentials.get(self.credential_key)
        if not token:
            return mock_result("mock_ig_123")
        try:
            required(credentials, *self.required_credentials)
            version = credentials.get("api_version", "v25.0")
            base = f"https://graph.facebook.com/{version}"
            account = f"{base}/{credentials['ig_user_id']}"
            async with httpx.AsyncClient(timeout=10, headers={"Authorization": f"Bearer {token}"}) as client:
                container = await request(client, "POST", f"{account}/media", data={
                    "image_url": credentials["image_url"],
                    "caption": "\n\n".join((title, text, cta)),
                })
                container_id = external_id(container.get("id"))
                for attempt in range(5):
                    status = await request(
                        client, "GET", f"{base}/{container_id}", params={"fields": "status_code"}
                    )
                    state = status.get("status_code")
                    if state == "FINISHED":
                        break
                    if state != "IN_PROGRESS":
                        raise PublishError("Instagram media container failed")
                    if attempt < 4:
                        await asyncio.sleep(2)
                else:
                    raise PublishError("Instagram media container was not ready")
                data = await request(
                    client, "POST", f"{account}/media_publish", data={"creation_id": container_id}
                )
            return PublishResult(success=True, external_id=external_id(data.get("id")))
        except PublishError as exc:
            return PublishResult(success=False, error=str(exc))
