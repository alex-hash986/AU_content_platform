from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Post, PostVariant
from app.models.enums import PostStatus, VariantLabel
from app.schemas.post import PostResponse, PostSchedule, PostVariantResponse
from app.services.ai_service import ai_service
from app.services.publication import posts_with_variants, publish_locked_post

router = APIRouter(prefix="/api/v1/posts", tags=["posts"])
Session = Annotated[AsyncSession, Depends(get_db)]

async def lock_post(db: AsyncSession, post_id: int) -> Post:
    # Serialize edits to the same A/B pair and read variants after obtaining the lock.
    post = await db.scalar(posts_with_variants.where(Post.id == post_id).with_for_update())
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/{post_id}/generate-variants")
async def generate_variants(post_id: int, db: Session) -> PostResponse:
    async with db.begin():
        post = await db.scalar(
            posts_with_variants.options(selectinload(Post.plan)).where(Post.id == post_id)
        )
        if post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        if len(post.variants) == 2:
            return PostResponse.model_validate(post)
        channel, topic = post.channel_type, post.topic
        tone, audience = post.plan.tone_of_voice, post.plan.target_audience

    generated = await ai_service.generate_post_variants(channel, topic, tone, audience)

    async with db.begin():
        # Refresh the earlier snapshot in case another request saved variants meanwhile.
        db.expire_all()
        post = await lock_post(db, post_id)
        existing_labels = {variant.variant_label for variant in post.variants}
        for item in generated.variants:
            label = VariantLabel(item.variant_label)
            if label not in existing_labels:
                post.variants.append(
                    PostVariant(
                        variant_label=label,
                        title=item.title,
                        body_text=item.body_text,
                        cta=item.cta,
                    )
                )
        await db.flush()
        post.variants.sort(key=lambda variant: variant.variant_label.value)
        response = PostResponse.model_validate(post)
    return response


@router.patch("/variants/{variant_id}/select-winner")
async def select_winner(variant_id: int, db: Session) -> PostVariantResponse:
    async with db.begin():
        post_id = await db.scalar(
            select(PostVariant.post_id).where(PostVariant.id == variant_id)
        )
        if post_id is None:
            raise HTTPException(status_code=404, detail="Post variant not found")
        post = await lock_post(db, post_id)
        winner = next((variant for variant in post.variants if variant.id == variant_id), None)
        if winner is None:
            raise HTTPException(status_code=404, detail="Post variant not found")
        for variant in post.variants:
            variant.is_selected = variant.id == variant_id
        response = PostVariantResponse.model_validate(winner)
    return response


@router.post("/{post_id}/publish-now")
async def publish_now(post_id: int, db: Session) -> PostResponse:
    async with db.begin():
        post = await lock_post(db, post_id)
        if post.status != PostStatus.PUBLISHED:
            await publish_locked_post(db, post)
        response = PostResponse.model_validate(post)
    return response


@router.post("/{post_id}/schedule")
async def schedule_post(post_id: int, payload: PostSchedule, db: Session) -> PostResponse:
    scheduled_at = payload.scheduled_at.astimezone(timezone.utc)
    async with db.begin():
        post = await lock_post(db, post_id)
        if post.status == PostStatus.PUBLISHED:
            raise HTTPException(status_code=409, detail="Post is already published")
        if scheduled_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=422, detail="Publication time must be in the future")
        post.scheduled_at = scheduled_at
        post.status = PostStatus.SCHEDULED
        post.publication_error = None
        response = PostResponse.model_validate(post)
    return response
