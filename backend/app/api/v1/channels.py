from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import ChannelType
from app.services.publication import active_channels
from app.services.publishers.factory import get_publisher

router = APIRouter(prefix="/api/v1/channels", tags=["channels"])
Session = Annotated[AsyncSession, Depends(get_db)]


class ChannelReadiness(BaseModel):
    channel_type: ChannelType
    mode: Literal["demo", "real", "incomplete"]
    required_keys: list[str]
    missing_keys: list[str]


@router.get("/status")
async def channel_status(db: Session) -> list[ChannelReadiness]:
    credentials_by_type = {}
    for channel_type, credentials in await db.execute(active_channels):
        credentials_by_type.setdefault(channel_type, credentials)

    readiness = []
    for channel_type in ChannelType:
        publisher = get_publisher(channel_type)
        keys = [publisher.credential_key, *publisher.required_credentials]
        credentials = credentials_by_type.get(channel_type, {})
        missing = [key for key in keys if not credentials.get(key)]
        mode: Literal["demo", "real", "incomplete"] = "real"
        if publisher.credential_key in missing:
            mode = "demo"
        elif missing:
            mode = "incomplete"
        readiness.append(ChannelReadiness(
            channel_type=channel_type, mode=mode, required_keys=keys, missing_keys=missing
        ))
    return readiness
