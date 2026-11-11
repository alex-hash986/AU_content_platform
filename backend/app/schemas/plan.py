from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.post import PostResponse


class ContentPlanCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    niche: str = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    tone_of_voice: str = Field(min_length=1)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=1, le=9999)
    goals: str | None = None


class ContentPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    niche: str
    month: int
    year: int
    created_at: datetime
    posts: list[PostResponse]
