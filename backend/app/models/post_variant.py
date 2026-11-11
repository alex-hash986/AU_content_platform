from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import VariantLabel, variant_label_enum


class PostVariant(Base):
    __tablename__ = "post_variants"
    __table_args__ = (
        UniqueConstraint("post_id", "variant_label", name="unique_post_variant_label"),
        UniqueConstraint("post_id", "id", name="unique_post_variant_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    title: Mapped[str] = mapped_column(String(255))
    body_text: Mapped[str] = mapped_column(Text)
    cta: Mapped[str] = mapped_column(Text)
    variant_label: Mapped[VariantLabel] = mapped_column(variant_label_enum)
    is_selected: Mapped[bool] = mapped_column(server_default=false())
