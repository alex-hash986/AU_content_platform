from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models.enums import ChannelType, PostStatus


class PostCreate(BaseModel):
    plan_id: int
    channel_type: ChannelType
    topic: str
    scheduled_at: datetime


class PostVariantCreate(BaseModel):
    variant_label: Literal["A", "B"]
    title: str
    body_text: str
    cta: str


class PostVariantResponse(PostVariantCreate):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    is_winner: bool = Field(validation_alias="is_selected")


class PostSchedule(BaseModel):
    scheduled_at: AwareDatetime


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    channel_type: ChannelType
    topic: str
    scheduled_at: datetime | None
    status: PostStatus
    variants: list[PostVariantResponse]
    published_variant_id: int | None = None
    published_at: datetime | None = None
    external_id: str | None = None
    publication_error: str | None = None
