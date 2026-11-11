from datetime import datetime, timezone
from random import Random

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Metric, Post, PostVariant
from app.models.enums import PostStatus, VariantLabel


async def refresh_simulated_metrics(factory: async_sessionmaker) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    async with factory.begin() as db:
        variants = await db.execute(
            select(Post.id, Post.published_at, PostVariant.id, PostVariant.variant_label)
            .join(PostVariant, PostVariant.post_id == Post.id)
            .where(
                Post.status == PostStatus.PUBLISHED,
                Post.external_id.startswith("mock_", autoescape=True),
                Post.published_at.is_not(None),
            )
        )
        rows = []
        for post_id, published_at, variant_id, label in variants:
            intervals = max(0, int((now - published_at).total_seconds()) // 300)
            random = Random(variant_id)
            views = random.randint(1000, 1500) + intervals * random.randint(10, 30)
            favored_label = Random(post_id).choice(list(VariantLabel))
            click_rate = random.uniform(0.08, 0.10) if label == favored_label else random.uniform(0.05, 0.07)
            clicks = int(views * click_rate)
            rows.append({
                "post_id": post_id,
                "variant_id": variant_id,
                "views": views,
                "likes": views // 20,
                "shares": views // 100,
                "clicks": clicks,
                "conversions": clicks // 8,
                "is_simulated": True,
                "recorded_at": now,
            })
        if rows:
            table = Metric.__table__
            statement = insert(table)
            snapshot_columns = ("views", "likes", "shares", "clicks", "conversions", "recorded_at")
            await db.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c.post_id, table.c.variant_id],
                    index_where=table.c.is_simulated,
                    set_={name: statement.excluded[name] for name in snapshot_columns},
                    where=table.c.recorded_at < statement.excluded.recorded_at,
                ),
                rows,
            )
    return {"simulated_variants": len(rows)}
