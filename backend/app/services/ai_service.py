import json
import logging
from calendar import monthrange
from typing import TypeVar

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, settings
from app.models.enums import ChannelType
from app.schemas.generation import (
    GeneratedContentSchema,
    GeneratedPlanSchema,
)
from app.services.mock_content import mock_monthly_plan, mock_post_variants

logger = logging.getLogger(__name__)
Output = TypeVar("Output", bound=BaseModel)

CHANNEL_GUIDANCE = {
    ChannelType.TELEGRAM: "Короткий пост, жирные акценты и короткие абзацы.",
    ChannelType.VK: "Пост для сообщества с конкретным примером и поводом обсудить.",
    ChannelType.INSTAGRAM: "Подпись к визуалу с сильной первой строкой и абзацами.",
    ChannelType.WORDPRESS: "Статья с введением, подзаголовками и выводом.",
    ChannelType.MAILCHIMP: "Заголовок — тема письма. Тело начни с прехедера, затем текст письма.",
}


class AIService:
    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    async def _parse(
        self, instructions: str, brief: dict[str, object], schema: type[Output]
    ) -> Output | None:
        secret = self.config.OPENAI_API_KEY
        api_key = secret.get_secret_value().strip() if secret else ""
        if not api_key:
            return None

        try:
            async with AsyncOpenAI(
                api_key=api_key,
                base_url=self.config.OPENAI_BASE_URL or None,
                timeout=30.0,
                max_retries=0,
            ) as client:
                beta_chat = getattr(client.beta, "chat", None)
                chat = beta_chat if beta_chat is not None else client.chat
                completion = await chat.completions.parse(
                    model=self.config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": instructions},
                        {"role": "user", "content": json.dumps(brief, ensure_ascii=False)},
                    ],
                    response_format=schema,
                )
                if completion.choices:
                    return completion.choices[0].message.parsed
        except (OpenAIError, ValidationError) as exc:
            logger.warning("Using demo content after OpenAI error (%s)", type(exc).__name__)
        return None

    async def generate_monthly_plan(
        self, niche: str, audience: str, tone: str, month: int, year: int,
        *, goals: str | None = None,
    ) -> GeneratedPlanSchema:
        last_day = monthrange(year, month)[1]
        result = await self._parse(
            "Составь контент-сетку на указанный месяц. Распредели публикации по "
            "telegram, vk, instagram, wordpress и mailchimp с учётом форматов. "
            "Используй боли аудитории, сезонные инфоповоды и уместные праздники. "
            "Не выдумывай праздники и не угадывай географию аудитории. "
            "Учти цели и тон. Для каждой публикации объясни выбор темы и канала. "
            "Разнеси публикации по всему месяцу и используй только дни из заданного диапазона.",
            {
                "niche": niche,
                "audience": audience,
                "tone": tone,
                "month": month,
                "year": year,
                "last_day": last_day,
                "goals": goals,
            },
            GeneratedPlanSchema,
        )
        if result is not None and all(item.day_of_month <= last_day for item in result.items):
            return result
        return mock_monthly_plan(niche, audience, month, year, last_day, goals)

    async def generate_post_variants(
        self, channel_type: str, topic: str, tone: str, audience: str
    ) -> GeneratedContentSchema:
        channel = ChannelType(channel_type)
        result = await self._parse(
            "Напиши два готовых к публикации варианта, A и B, на одну тему. "
            "В A начни с конкретной пользы или простого шага. В B начни с ошибки, "
            "вопроса или альтернативного взгляда. Используй разные хуки в заголовках "
            "и разные CTA. Учти аудиторию и тон. " + CHANNEL_GUIDANCE[channel],
            {"channel_type": channel, "topic": topic, "tone": tone, "audience": audience},
            GeneratedContentSchema,
        )
        return result if result is not None else mock_post_variants(channel, topic, audience)


ai_service = AIService()
