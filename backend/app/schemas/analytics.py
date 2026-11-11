from typing import Literal

from pydantic import BaseModel

from app.models.enums import ChannelType, VariantLabel

MetricSource = Literal["measured", "simulated"]


class VariantAnalytics(BaseModel):
    variant_id: int
    source: MetricSource | None = None
    views: int = 0
    likes: int = 0
    shares: int = 0
    clicks: int = 0
    ctr: float = 0
    conversions: int = 0


class ABTestAnalytics(BaseModel):
    post_id: int
    variants: dict[VariantLabel, VariantAnalytics]
    ctr_difference_percentage_points: float | None = None
    p_value: float | None = None
    statistical_winner: VariantLabel | None = None


class AnalyticsSummary(BaseModel):
    total_posts: int
    posts_by_channel: dict[ChannelType, int]
    average_ctr: float | None
    average_ctr_source: MetricSource | None
    measured_average_ctr: float | None
    simulated_average_ctr: float | None
