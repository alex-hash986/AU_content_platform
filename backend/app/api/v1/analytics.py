from collections import defaultdict
from math import erfc, sqrt
from statistics import fmean
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.models import Metric, Post
from app.models.enums import ChannelType, PostStatus, VariantLabel
from app.schemas.analytics import ABTestAnalytics, AnalyticsSummary, VariantAnalytics
from app.services.publication import posts_with_variants

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
Session = Annotated[AsyncSession, Depends(get_db)]


def latest_metrics(post_id: int | None = None, *, published_only: bool = False):
    # Each row is a cumulative snapshot. Measured data takes priority over demo data.
    snapshots = select(
        Metric,
        func.row_number().over(
            partition_by=(Metric.post_id, Metric.variant_id),
            order_by=(Metric.is_simulated, Metric.recorded_at.desc(), Metric.id.desc()),
        ).label("snapshot_rank"),
    )
    if post_id is not None:
        snapshots = snapshots.where(Metric.post_id == post_id)
    if published_only:
        snapshots = snapshots.join(Post, Post.id == Metric.post_id).where(
            Post.status == PostStatus.PUBLISHED
        )
    ranked = snapshots.subquery()
    return select(aliased(Metric, ranked)).where(ranked.c.snapshot_rank == 1)


def ctr(clicks: int, views: int) -> float:
    return clicks / views * 100 if views else 0.0


def compare_ctr(a: VariantAnalytics, b: VariantAnalytics) -> tuple[float | None, float | None]:
    if a.source is None or a.source != b.source or min(a.views, b.views) <= 0:
        return None, None
    difference = b.ctr - a.ctr
    if not (0 <= a.clicks <= a.views and 0 <= b.clicks <= b.views):
        return difference, None
    pooled_rate = (a.clicks + b.clicks) / (a.views + b.views)
    # A two-sided z-test uses the normal approximation when expected counts suffice.
    if min(a.views, b.views) * min(pooled_rate, 1 - pooled_rate) < 5:
        return difference, None
    standard_error = sqrt(pooled_rate * (1 - pooled_rate) * (1 / a.views + 1 / b.views))
    z_score = abs(difference / 100) / standard_error
    return difference, erfc(z_score / sqrt(2))


@router.get("/ab-test/{post_id}")
async def ab_test(post_id: int, db: Session) -> ABTestAnalytics:
    post = await db.scalar(posts_with_variants.where(Post.id == post_id))
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    snapshots = {
        metric.variant_id: metric for metric in await db.scalars(latest_metrics(post_id))
    }
    variants = {}
    for variant in post.variants:
        metric = snapshots.get(variant.id)
        stats = VariantAnalytics(variant_id=variant.id)
        if metric is not None:
            stats = VariantAnalytics(
                variant_id=variant.id,
                source="simulated" if metric.is_simulated else "measured",
                views=metric.views,
                likes=metric.likes,
                shares=metric.shares,
                clicks=metric.clicks,
                ctr=ctr(metric.clicks, metric.views),
                conversions=metric.conversions,
            )
        variants[variant.variant_label] = stats

    a, b = variants.get(VariantLabel.A), variants.get(VariantLabel.B)
    difference, p_value = compare_ctr(a, b) if a is not None and b is not None else (None, None)
    winner = None
    if p_value is not None and p_value < 0.05:
        winner = VariantLabel.B if difference > 0 else VariantLabel.A
    return ABTestAnalytics(
        post_id=post_id,
        variants=variants,
        ctr_difference_percentage_points=difference,
        p_value=p_value,
        statistical_winner=winner,
    )


def average_post_ctr(snapshots_by_post: dict[int, list[Metric]]) -> float | None:
    rates = []
    for snapshots in snapshots_by_post.values():
        post_snapshot = next((metric for metric in snapshots if metric.variant_id is None), None)
        if post_snapshot is not None:
            snapshots = [post_snapshot]
        views = sum(metric.views for metric in snapshots)
        if views > 0:
            rates.append(ctr(sum(metric.clicks for metric in snapshots), views))
    return fmean(rates) if rates else None


@router.get("/summary")
async def summary(db: Session) -> AnalyticsSummary:
    counts = await db.execute(select(Post.channel_type, func.count()).group_by(Post.channel_type))
    posts_by_channel = dict.fromkeys(ChannelType, 0)
    posts_by_channel.update(dict(counts.all()))
    snapshots = await db.scalars(latest_metrics(published_only=True))
    measured: dict[int, list[Metric]] = defaultdict(list)
    simulated: dict[int, list[Metric]] = defaultdict(list)
    for metric in snapshots:
        group = simulated if metric.is_simulated else measured
        group[metric.post_id].append(metric)
    measured_ctr = average_post_ctr(measured)
    simulated_ctr = average_post_ctr(simulated)
    average = measured_ctr if measured_ctr is not None else simulated_ctr
    source = "measured" if measured_ctr is not None else "simulated" if simulated_ctr is not None else None
    return AnalyticsSummary(
        total_posts=sum(posts_by_channel.values()),
        posts_by_channel=posts_by_channel,
        average_ctr=average,
        average_ctr_source=source,
        measured_average_ctr=measured_ctr,
        simulated_average_ctr=simulated_ctr,
    )
