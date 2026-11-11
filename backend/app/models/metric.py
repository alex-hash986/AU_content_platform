from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, ForeignKeyConstraint, Index, false, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["post_id", "variant_id"],
            ["post_variants.post_id", "post_variants.id"],
            name="metric_post_variant_fk",
        ),
        Index(
            "uq_metrics_simulated_variant", "post_id", "variant_id",
            unique=True, postgresql_where=text("is_simulated"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    variant_id: Mapped[int | None]
    views: Mapped[int] = mapped_column(BigInteger, server_default="0")
    likes: Mapped[int] = mapped_column(BigInteger, server_default="0")
    shares: Mapped[int] = mapped_column(BigInteger, server_default="0")
    clicks: Mapped[int] = mapped_column(BigInteger, server_default="0")
    conversions: Mapped[int] = mapped_column(BigInteger, server_default="0")
    is_simulated: Mapped[bool] = mapped_column(server_default=false())
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
