from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ChannelType, PostStatus, channel_type_enum, post_status_enum

if TYPE_CHECKING:
    from app.models.content_plan import ContentPlan
    from app.models.post_variant import PostVariant


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id", "published_variant_id"],
            ["post_variants.post_id", "post_variants.id"],
            name="post_published_variant_fk",
            use_alter=True,
        ),
        Index("ix_posts_status_scheduled_at", "status", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement="ignore_fk")
    plan_id: Mapped[int] = mapped_column(ForeignKey("content_plans.id"), index=True)
    channel_type: Mapped[ChannelType] = mapped_column(channel_type_enum)
    topic: Mapped[str] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[PostStatus] = mapped_column(
        post_status_enum, server_default=PostStatus.DRAFT.value
    )
    published_variant_id: Mapped[int | None]
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str | None] = mapped_column(Text)
    publication_error: Mapped[str | None] = mapped_column(Text)
    plan: Mapped["ContentPlan"] = relationship(back_populates="posts", lazy="raise")
    variants: Mapped[list["PostVariant"]] = relationship(
        foreign_keys="PostVariant.post_id", order_by="PostVariant.variant_label", lazy="raise"
    )
