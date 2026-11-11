from app.models.enums import ChannelType
from app.services.publishers.base import BasePublisher
from app.services.publishers.instagram import InstagramPublisher
from app.services.publishers.mailchimp import MailchimpPublisher
from app.services.publishers.telegram import TelegramPublisher
from app.services.publishers.vk import VKPublisher
from app.services.publishers.wordpress import WordPressPublisher

PUBLISHERS: dict[ChannelType, type[BasePublisher]] = {
    ChannelType.TELEGRAM: TelegramPublisher,
    ChannelType.VK: VKPublisher,
    ChannelType.WORDPRESS: WordPressPublisher,
    ChannelType.MAILCHIMP: MailchimpPublisher,
    ChannelType.INSTAGRAM: InstagramPublisher,
}


def get_publisher(channel_type: ChannelType) -> BasePublisher:
    return PUBLISHERS[channel_type]()
