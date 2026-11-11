import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Channel, Post, PostVariant
from app.models.enums import PostStatus, VariantLabel
from app.services.publishers.base import PublishResult
from app.services.publishers.factory import get_publisher

logger = logging.getLogger(__name__)
posts_with_variants = select(Post).options(selectinload(Post.variants))
active_channels = (
    select(Channel.type, Channel.credentials_json)
    .where(Channel.is_active.is_(True))
    .order_by(Channel.id)
)


def publication_variant(post: Post) -> PostVariant | None:
    selected = next((variant for variant in post.variants if variant.is_selected), None)
    return selected or next(
        (variant for variant in post.variants if variant.variant_label == VariantLabel.A), None
    )


async def publish_locked_post(db: AsyncSession, post: Post) -> None:
    """Publish while the caller holds the post row lock."""
    variant = publication_variant(post)
    if variant is None:
        result = PublishResult(success=False, error="Post has neither a selected variant nor variant A")
    else:
        channel = (
            await db.execute(active_channels.where(Channel.type == post.channel_type).limit(1))
        ).first()
        credentials = channel.credentials_json if channel is not None else {}
        try:
            result = await get_publisher(post.channel_type).publish(
                variant.title, variant.body_text, variant.cta, credentials
            )
        except Exception as exc:
            # Keep vendor request details out of logs and stored errors.
            logger.error("Publisher failed for post %s (%s)", post.id, type(exc).__name__)
            result = PublishResult(success=False, error="Unexpected channel publisher error")

    post.external_id = result.external_id
    if result.success and variant is not None:
        post.status = PostStatus.PUBLISHED
        post.published_variant_id = variant.id
        post.published_at = datetime.now(timezone.utc)
        post.publication_error = None
    else:
        post.status = PostStatus.FAILED
        post.publication_error = result.error or "Publication failed"
