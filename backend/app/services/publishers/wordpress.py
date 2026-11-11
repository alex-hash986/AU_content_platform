import httpx

from app.services.publishers.base import (
    BasePublisher, PublishError, PublishResult, content_html, external_id, mock_result, request,
    required,
)


class WordPressPublisher(BasePublisher):
    credential_key = "application_password"
    required_credentials = ("site_url", "username")

    async def publish(self, title: str, text: str, cta: str, credentials: dict) -> PublishResult:
        password = credentials.get(self.credential_key)
        if not password:
            return mock_result("mock_wp_123")
        try:
            required(credentials, *self.required_credentials)
            site = str(credentials["site_url"]).rstrip("/")
            if httpx.URL(site).scheme != "https":
                raise PublishError("WordPress site_url must use HTTPS")
            async with httpx.AsyncClient(timeout=15, auth=(credentials["username"], password)) as client:
                data = await request(
                    client, "POST", f"{site}/wp-json/wp/v2/posts",
                    json={"title": title, "content": content_html(text, cta), "status": "publish"},
                )
            return PublishResult(success=True, external_id=external_id(data.get("id")))
        except (PublishError, httpx.InvalidURL) as exc:
            error = str(exc) if isinstance(exc, PublishError) else "Invalid WordPress site_url"
            return PublishResult(success=False, error=error)
