# Автопостинг и аналитика

Из папки `backend` установите зависимости и примените миграции к базе проекта.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
```

При запущенных PostgreSQL и Redis запустите API, один воркер и один экземпляр Beat в отдельных терминалах из папки `backend`.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
.\.venv\Scripts\python.exe -m celery -A app.tasks.celery_app:celery_app worker --pool=solo --loglevel=INFO
.\.venv\Scripts\python.exe -m celery -A app.tasks.celery_app:celery_app beat --loglevel=INFO
```

Beat проверяет очередь публикаций каждые 30 секунд и обновляет демометрики каждые пять минут. Для `POST /api/v1/posts/{post_id}/schedule` передайте JSON с будущим временем и часовым поясом, например `{"scheduled_at":"2030-05-21T12:30:00+07:00"}`. `POST /api/v1/posts/{post_id}/publish-now` выполняется сразу. Обе операции используют победителя A/B или вариант A. Ответ о публикации содержит статус, внешний ID и, при сбое, `publication_error`.

## Настройки каналов

Адаптер берёт `credentials_json` первой активной записи `channels` соответствующего типа по порядку ID. При отсутствии ключа или пароля применяется деморежим.

| Канал | Ключи в `credentials_json` |
| --- | --- |
| Telegram | `bot_token`, `chat_id` |
| VK | `access_token`, `owner_id`, опционально `api_version` |
| WordPress | `site_url` с HTTPS, `username`, `application_password` |
| Mailchimp | `api_key`, `list_id`, `from_name`, `reply_to`, опционально `server_prefix` |
| Instagram | `access_token` для Facebook Login, `ig_user_id`, публичный `image_url` для фото, опционально `api_version` |

Mailchimp создаёт кампанию и отправляет её указанному списку. Instagram публикует одну фотографию с подписью.

## Метрики

`GET /api/v1/analytics/ab-test/{post_id}` возвращает последний накопительный снимок по каждому варианту, разницу CTR в процентных пунктах и статистического победителя при `p < 0.05`. Сравнение выполняется для двух вариантов с одним источником данных и достаточной выборкой.

`GET /api/v1/analytics/summary` возвращает число постов по каналам и средний CTR по опубликованным постам с просмотрами. Демоданные помечены `simulated`. Для реальных публикаций аналитика читает измеренные значения из таблицы `metrics`. Получение этих значений из внешних систем требует отдельной интеграции.
