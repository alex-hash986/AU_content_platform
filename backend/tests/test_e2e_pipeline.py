import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from celery.beat import ScheduleEntry, Scheduler
from celery.contrib.testing.worker import start_worker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import Settings, settings
from app.core.database import Base, get_db
from app.main import app
from app.models import Post
from app.models.enums import ChannelType
from app.services.ai_service import ai_service
from app.services.publishers.factory import get_publisher
from app.tasks import publishing
from app.tasks.celery_app import celery_app

MOCK_IDS = {
    ChannelType.TELEGRAM: "mock_tg_123",
    ChannelType.VK: "mock_vk_123",
    ChannelType.WORDPRESS: "mock_wp_123",
    ChannelType.MAILCHIMP: "mock_mc_123",
    ChannelType.INSTAGRAM: "mock_ig_123",
}


@pytest_asyncio.fixture
async def isolated_pipeline(monkeypatch):
    schema = f"e2e_{uuid4().hex}"
    admin_engine = create_async_engine(settings.DATABASE_URL)

    def schema_engine(url, **kwargs):
        return create_async_engine(
            url, connect_args={"server_settings": {"search_path": schema}}, **kwargs
        )

    database = schema_engine(settings.DATABASE_URL)
    sessions = async_sessionmaker(database, expire_on_commit=False)

    async def get_test_session():
        async with sessions() as session:
            yield session

    try:
        async with admin_engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
        async with database.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        monkeypatch.setitem(app.dependency_overrides, get_db, get_test_session)
        monkeypatch.setattr(ai_service, "config", Settings(OPENAI_API_KEY=None))
        monkeypatch.setattr(publishing, "create_async_engine", schema_engine)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions, schema
    finally:
        await database.dispose()
        try:
            async with admin_engine.begin() as connection:
                await connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        finally:
            await admin_engine.dispose()


def run_periodic_jobs(queue: str) -> tuple[dict, dict]:
    scheduler = Scheduler(app=celery_app, lazy=True)
    results = []
    try:
        with start_worker(celery_app, pool="solo", queues=[queue], perform_ping_check=False):
            for name in ("publish-scheduled-posts", "collect-post-metrics"):
                config = celery_app.conf.beat_schedule[name]
                entry = ScheduleEntry(
                    name=name, task=config["task"], schedule=config["schedule"],
                    options={**config["options"], "queue": queue}, app=celery_app,
                )
                result = scheduler.apply_async(entry)
                try:
                    results.append(result.get(timeout=15))
                finally:
                    result.forget()
    finally:
        with celery_app.connection_for_write() as connection:
            connection.default_channel.queue_delete(queue)
    return results[0], results[1]


@pytest.mark.asyncio
async def test_content_marketing_pipeline(isolated_pipeline):
    client, sessions, queue = isolated_pipeline
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    print("Health check OK")

    payload = {
        "niche": "Онлайн-курсы",
        "target_audience": "Начинающие дизайнеры",
        "tone_of_voice": "Дружелюбный и практичный",
        "month": 2,
        "year": 2028,
        "goals": "Увеличить число пробных регистраций",
    }
    response = await client.post("/api/v1/plans/generate", json=payload)
    assert response.status_code == 201, response.text
    plan = response.json()
    posts = plan["posts"]
    assert plan["id"] > 0 and plan["niche"] == payload["niche"]
    assert len(posts) >= 2
    assert all(post["topic"].strip() and post["status"] == "draft" for post in posts)
    assert all(post["plan_id"] == plan["id"] for post in posts)
    assert {post["channel_type"] for post in posts} == {channel.value for channel in ChannelType}
    assert (await client.get(f"/api/v1/plans/{plan['id']}")).json() == plan
    assert (await client.get("/api/v1/plans/")).json() == [plan]
    print(f"Content plan created with {len(posts)} draft posts")

    first, second = posts[:2]
    first_id, second_id = first["id"], second["id"]
    response = await client.post(f"/api/v1/posts/{first_id}/generate-variants")
    assert response.status_code == 200, response.text
    pair = response.json()["variants"]
    assert len(pair) == 2
    assert {variant["variant_label"] for variant in pair} == {"A", "B"}
    assert all(variant[field].strip() for variant in pair for field in ("title", "body_text", "cta"))
    variants = {variant["variant_label"]: variant for variant in pair}
    assert variants["A"]["title"] != variants["B"]["title"]
    assert variants["A"]["cta"] != variants["B"]["cta"]

    winner_id = variants["B"]["id"]
    response = await client.patch(f"/api/v1/posts/variants/{winner_id}/select-winner")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == winner_id and response.json()["is_winner"] is True
    persisted = await client.get(f"/api/v1/plans/{plan['id']}")
    assert persisted.status_code == 200, persisted.text
    selection = {
        variant["variant_label"]: variant["is_winner"]
        for variant in persisted.json()["posts"][0]["variants"]
    }
    assert selection == {"A": False, "B": True}
    print("A/B content generated and variant B selected")

    response = await client.post(f"/api/v1/posts/{first_id}/publish-now")
    assert response.status_code == 200, response.text
    published = response.json()
    assert published["status"] == "published"
    assert published["external_id"] == MOCK_IDS[ChannelType(first["channel_type"])]
    assert published["published_variant_id"] == winner_id
    print("Selected variant published via mock adapter")

    generated = await client.post(f"/api/v1/posts/{second_id}/generate-variants")
    assert generated.status_code == 200, generated.text
    default_variant = next(item for item in generated.json()["variants"] if item["variant_label"] == "A")
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    response = await client.post(
        f"/api/v1/posts/{second_id}/schedule", json={"scheduled_at": future.isoformat()}
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "scheduled"
    assert datetime.fromisoformat(response.json()["scheduled_at"]) == future

    # Make the scheduled post due so the worker can process it immediately.
    async with sessions.begin() as session:
        await session.execute(
            update(Post).where(Post.id == second_id)
            .values(scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
    published_counts, metric_counts = await asyncio.to_thread(run_periodic_jobs, queue)
    assert published_counts == {"published": 1, "failed": 0}
    assert metric_counts == {"simulated_variants": 4}
    persisted = await client.get(f"/api/v1/plans/{plan['id']}")
    scheduled_post = next(post for post in persisted.json()["posts"] if post["id"] == second_id)
    assert scheduled_post["status"] == "published"
    assert scheduled_post["published_variant_id"] == default_variant["id"]
    print("Celery published the scheduled post and collected metrics through Redis")

    response = await client.get(f"/api/v1/analytics/ab-test/{first_id}")
    assert response.status_code == 200, response.text
    analytics = response.json()
    assert analytics["post_id"] == first_id
    assert set(analytics["variants"]) == {"A", "B"}
    a, b = (analytics["variants"][label] for label in ("A", "B"))
    for stats in (a, b):
        assert stats["source"] == "simulated"
        assert stats["views"] > 0 and stats["clicks"] >= stats["conversions"] >= 0
        assert stats["ctr"] == pytest.approx(stats["clicks"] / stats["views"] * 100)
    assert analytics["ctr_difference_percentage_points"] == pytest.approx(b["ctr"] - a["ctr"])
    assert 0 <= analytics["p_value"] <= 1
    expected_winner = ("B" if b["ctr"] > a["ctr"] else "A") if analytics["p_value"] < 0.05 else None
    assert analytics["statistical_winner"] == expected_winner

    response = await client.get("/api/v1/analytics/summary")
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["total_posts"] == len(posts)
    assert summary["posts_by_channel"] == dict(Counter(post["channel_type"] for post in posts))
    assert summary["average_ctr_source"] == "simulated"
    assert summary["average_ctr"] == summary["simulated_average_ctr"] > 0
    print("A/B analytics and platform summary verified")


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", list(ChannelType))
async def test_publisher_demo_fallback(channel):
    result = await get_publisher(channel).publish("Заголовок", "Текст", "CTA", {})
    assert result.success is True
    assert result.external_id == MOCK_IDS[channel]
    assert result.error is None
