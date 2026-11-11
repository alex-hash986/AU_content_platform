from app.models.enums import ChannelType
from app.schemas.generation import (
    GeneratedContentSchema,
    GeneratedPlanSchema,
    GeneratedPostItem,
    GeneratedVariantItem,
)


def mock_monthly_plan(
    niche: str, audience: str, month: int, year: int, last_day: int, goals: str | None
) -> GeneratedPlanSchema:
    slots = [
        (2, ChannelType.TELEGRAM, "Три шага, чтобы начать", "Дать быстрый первый результат."),
        (5, ChannelType.VK, "Опрос о главной трудности", "Собрать вопросы для следующих постов."),
        (8, ChannelType.INSTAGRAM, "Карусель с типичной ошибкой", "Показать решение наглядно."),
        (12, ChannelType.WORDPRESS, "Пошаговое руководство с чек-листом", "Ответить на частые вопросы."),
        (15, ChannelType.MAILCHIMP, "Письмо с заданием на неделю", "Помочь применить совет на практике."),
        (19, ChannelType.TELEGRAM, "Сезонный чек-лист на вторую половину месяца", "Связать советы с календарём."),
        (22, ChannelType.VK, "Разбор практической ситуации", "Обсудить варианты решения в комментариях."),
        (25, ChannelType.INSTAGRAM, "Визуальный чек-лист перед стартом", "Дать материал, который удобно сохранить."),
        (last_day, ChannelType.MAILCHIMP, "Итоги месяца и один следующий шаг", "Закрепить результат и собрать обратную связь."),
    ]
    summary = f"План для аудитории «{audience}». От первых шагов к практике и итогам месяца."
    if goals:
        summary += f" Цель кампании — {goals}."
    return GeneratedPlanSchema(
        title=f"{month:02d}.{year:04d} — {niche}"[:255],
        summary=summary,
        items=[
            GeneratedPostItem(
                day_of_month=day,
                channel_type=channel,
                topic=f"{angle} — {niche}",
                rationale=rationale,
            )
            for day, channel, angle, rationale in slots
        ],
    )


def mock_post_variants(
    channel: ChannelType, topic: str, audience: str
) -> GeneratedContentSchema:
    steps = (
        f"Если вы ищете ответ на вопрос «{topic}», начните с одной ситуации, "
        "которую хотите изменить. Запишите ожидаемый результат, выберите действие "
        "на 15 минут и отметьте, что стало проще после первого шага."
    )
    experiment = (
        f"Для аудитории «{audience}» в теме «{topic}» легко переоценить объём первого шага. "
        "Проведите небольшой эксперимент: сравните привычный способ с одним изменением "
        "и оцените результат по тому же критерию. Если разницы нет, попробуйте другой шаг."
    )
    copy = {
        ChannelType.TELEGRAM: (
            f"**Проверка за 15 минут**\n\n{steps}", "Сохраните пост и выделите 15 минут сегодня.",
            f"**Что мешает сдвинуться с места?**\n\n{experiment}", "Расскажите в комментариях, что сравнили бы.",
        ),
        ChannelType.VK: (
            f"{steps}\n\nПример: вместо «разобраться за выходные» запланируйте один пробный шаг на сегодня.",
            "Напишите в комментариях, с какого шага начнёте.",
            f"{experiment}\n\nВ обсуждении сравним, какие изменения проще повторить.",
            "Отправьте пост тому, с кем можно провести эксперимент.",
        ),
        ChannelType.INSTAGRAM: (
            f"Один шаг сегодня.\n\n{steps}\n\nНа карточках: цель → действие → результат.",
            "Сохраните карусель, чтобы вернуться к ней вечером.",
            f"Что вы делаете по привычке?\n\n{experiment}\n\nНа карточках: привычка → замена → проверка.",
            "Поделитесь постом в сторис и добавьте свой пример.",
        ),
        ChannelType.WORDPRESS: (
            f"## Как выбрать задачу\n\n{steps}\n\n## Как оценить результат\n\n"
            "Запишите, сколько времени занял шаг и что получилось. Повторите через неделю.",
            "Скопируйте чек-лист и отметьте выполненные пункты.",
            f"## Где теряется время\n\n{experiment}\n\n## Как сравнить подходы\n\n"
            "Проверьте оба подхода на похожих задачах и сравните затраты времени.",
            "Опишите результат сравнения в комментариях к статье.",
        ),
        ChannelType.MAILCHIMP: (
            f"Прехедер: короткое задание на сегодня.\n\nЗдравствуйте!\n\n{steps}",
            "Запланируйте 15 минут в календаре.",
            f"Прехедер: проверим привычный подход на практике.\n\nЗдравствуйте!\n\n{experiment}",
            "Ответьте на письмо и расскажите, какой подход сработал лучше.",
        ),
    }
    body_a, cta_a, body_b, cta_b = copy[channel]
    return GeneratedContentSchema(variants=[
        GeneratedVariantItem(
            variant_label="A", title=f"Первый шаг за 15 минут — {topic}"[:255],
            body_text=body_a, cta=cta_a,
        ),
        GeneratedVariantItem(
            variant_label="B", title=f"Где теряется время? — {topic}"[:255],
            body_text=body_b, cta=cta_b,
        ),
    ])
