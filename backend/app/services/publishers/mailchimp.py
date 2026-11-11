import re

import httpx

from app.services.publishers.base import (
    BasePublisher, PublishError, PublishResult, content_html, external_id, mock_result, request,
    required,
)


class MailchimpPublisher(BasePublisher):
    credential_key = "api_key"
    required_credentials = ("list_id", "from_name", "reply_to")

    async def publish(self, title: str, text: str, cta: str, credentials: dict) -> PublishResult:
        key = credentials.get(self.credential_key)
        if not key:
            return mock_result("mock_mc_123")
        campaign_id = None
        try:
            required(credentials, *self.required_credentials)
            region = str(credentials.get("server_prefix") or str(key).rpartition("-")[2])
            if not re.fullmatch(r"[a-z]{2}[0-9]+", region):
                raise PublishError("Invalid Mailchimp server prefix")
            url = f"https://{region}.api.mailchimp.com/3.0/campaigns"
            settings = {
                "subject_line": title,
                "from_name": credentials["from_name"],
                "reply_to": credentials["reply_to"],
            }
            first_line, _, body = text.partition("\n")
            if first_line.lower().startswith(("прехедер:", "preheader:")):
                settings["preview_text"] = first_line.split(":", 1)[1].strip()[:150]
                text = body.lstrip()
            async with httpx.AsyncClient(timeout=15, auth=("marketing", key)) as client:
                data = await request(client, "POST", url, json={
                    "type": "regular",
                    "recipients": {"list_id": credentials["list_id"]},
                    "settings": settings,
                })
                campaign_id = external_id(data.get("id"))
                html = content_html(text, cta) + '<p><a href="*|UNSUB|*">Отписаться</a></p>'
                await request(client, "PUT", f"{url}/{campaign_id}/content", json={"html": html})
                await request(client, "POST", f"{url}/{campaign_id}/actions/send")
            return PublishResult(success=True, external_id=campaign_id)
        except PublishError as exc:
            return PublishResult(success=False, external_id=campaign_id, error=str(exc))
