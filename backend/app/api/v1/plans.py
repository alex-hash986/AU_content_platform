from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import ContentPlan, Post
from app.schemas.plan import ContentPlanCreate, ContentPlanResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])
Session = Annotated[AsyncSession, Depends(get_db)]

plans_with_posts = select(ContentPlan).options(
    selectinload(ContentPlan.posts).selectinload(Post.variants)
)


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_plan(payload: ContentPlanCreate, db: Session) -> ContentPlanResponse:
    generated = await ai_service.generate_monthly_plan(
        payload.niche,
        payload.target_audience,
        payload.tone_of_voice,
        payload.month,
        payload.year,
        goals=payload.goals,
    )
    plan = ContentPlan(
        title=generated.title,
        niche=payload.niche,
        month=payload.month,
        year=payload.year,
        target_audience=payload.target_audience,
        tone_of_voice=payload.tone_of_voice,
        posts=[
            Post(
                channel_type=item.channel_type,
                topic=item.topic,
                scheduled_at=datetime(
                    payload.year, payload.month, item.day_of_month, 12, tzinfo=timezone.utc
                ),
                variants=[],
            )
            for item in sorted(generated.items, key=lambda item: item.day_of_month)
        ],
    )
    async with db.begin():
        db.add(plan)
        await db.flush()
        response = ContentPlanResponse.model_validate(plan)
    return response


@router.get("/")
async def list_plans(db: Session) -> list[ContentPlanResponse]:
    plans = await db.scalars(plans_with_posts.order_by(ContentPlan.id.desc()))
    return [ContentPlanResponse.model_validate(plan) for plan in plans]


@router.get("/{plan_id}")
async def get_plan(plan_id: int, db: Session) -> ContentPlanResponse:
    plan = await db.scalar(plans_with_posts.where(ContentPlan.id == plan_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Content plan not found")
    return ContentPlanResponse.model_validate(plan)
