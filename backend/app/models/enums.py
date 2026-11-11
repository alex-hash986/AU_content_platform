from enum import Enum

from sqlalchemy import Enum as SQLEnum


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    VK = "vk"
    INSTAGRAM = "instagram"
    WORDPRESS = "wordpress"
    MAILCHIMP = "mailchimp"


class PostStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class VariantLabel(str, Enum):
    A = "A"
    B = "B"


def enum_values(enum_class: type[Enum]) -> list[str]:
    return [member.value for member in enum_class]


channel_type_enum = SQLEnum(ChannelType, name="channel_type", values_callable=enum_values)
post_status_enum = SQLEnum(PostStatus, name="post_status", values_callable=enum_values)
variant_label_enum = SQLEnum(VariantLabel, name="variant_label", values_callable=enum_values)
