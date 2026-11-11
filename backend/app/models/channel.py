from typing import Any

from sqlalchemy import String, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ChannelType, channel_type_enum


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[ChannelType] = mapped_column(channel_type_enum)
    credentials_json: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), default=dict, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(server_default=true())
