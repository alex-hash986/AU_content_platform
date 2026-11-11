from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ChannelType
from app.schemas.post import PostVariantCreate


class GeneratedPostItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    day_of_month: int = Field(ge=1, le=31)
    channel_type: ChannelType
    topic: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class GeneratedPlanSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1)
    items: list[GeneratedPostItem] = Field(min_length=1)


class GeneratedVariantItem(PostVariantCreate):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    body_text: str = Field(min_length=1)
    cta: str = Field(min_length=1)


class GeneratedContentSchema(BaseModel):
    variants: list[GeneratedVariantItem] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_pair(self) -> "GeneratedContentSchema":
        first, second = self.variants
        if {first.variant_label, second.variant_label} != {"A", "B"}:
            raise ValueError("Expected one A variant and one B variant")
        if first.title.casefold() == second.title.casefold():
            raise ValueError("Variants must have different titles")
        if first.cta.casefold() == second.cta.casefold():
            raise ValueError("Variants must have different calls to action")
        return self
