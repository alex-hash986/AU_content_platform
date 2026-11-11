import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Post
from app.models.enums import PostStatus
from app.services.metrics import refresh_simulated_metrics
from app.services.publication import posts_with_variants, publish_locked_post
from app.tasks.celery_app import celery_app

Result = TypeVar("Result")


async def run_with_database(operation: Callable[..., Awaitable[Result]]) -> Result:
    # Celery invokes each task on a fresh event loop.
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        return await operation(factory)
    finally:
        await engine.dispose()


async def publish_due_posts(factory: async_sessionmaker, limit: int = 50) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    pending = (
        posts_with_variants.where(Post.status == PostStatus.SCHEDULED, Post.scheduled_at <= now)
        .order_by(Post.scheduled_at, Post.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    counts = {"published": 0, "failed": 0}
    async with factory() as db:
        for _ in range(limit):
            async with db.begin():
                post = await db.scalar(pending)
                if post is None:
                    break
                await publish_locked_post(db, post)
                counts[post.status.value] += 1
    return counts


@celery_app.task
def check_and_publish_scheduled_posts() -> dict[str, int]:
    return asyncio.run(run_with_database(publish_due_posts))


@celery_app.task
def collect_post_metrics() -> dict[str, int]:
    return asyncio.run(run_with_database(refresh_simulated_metrics))
