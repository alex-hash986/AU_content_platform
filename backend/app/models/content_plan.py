from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.post import Post


class ContentPlan(Base):
    __tablename__ = "content_plans"
    __table_args__ = (CheckConstraint("month BETWEEN 1 AND 12", name="valid_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    niche: Mapped[str] = mapped_column(Text)
    month: Mapped[int]
    year: Mapped[int]
    target_audience: Mapped[str] = mapped_column(Text)
    tone_of_voice: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    posts: Mapped[list["Post"]] = relationship(
        back_populates="plan", order_by="(Post.scheduled_at, Post.id)", lazy="raise"
    )
