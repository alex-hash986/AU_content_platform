from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="AI Content Marketing Studio", layout="wide", page_icon="🚀")

CHANNEL_NAMES = {
    "telegram": "Telegram",
    "vk": "VK",
    "instagram": "Instagram",
    "wordpress": "WordPress",
    "mailchimp": "Mailchimp",
}
CHANNEL_HINTS = {
    "telegram": "Бот должен иметь право публиковать сообщения в чате или канале.",
    "vk": "Для стены сообщества укажите отрицательный owner_id. api_version — опционально.",
    "instagram": "Токен Facebook Login и публичный URL фотографии. api_version — опционально.",
    "wordpress": "URL сайта с HTTPS и пароль приложения WordPress.",
    "mailchimp": "Кампания отправляется списку list_id. server_prefix — опционально.",
}
MONTHS = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)
STATUSES = {
    "draft": "Черновик",
    "scheduled": "Запланирован",
    "published": "Опубликован",
    "failed": "Ошибка публикации",
}
LOCAL_TIMEZONE = ZoneInfo("Asia/Novosibirsk")
PLANS_URL = "/api/v1/plans"
POSTS_URL = "/api/v1/posts"
ANALYTICS_URL = "/api/v1/analytics"


class ApiError(Exception):
    pass


def api_request(client: httpx.Client, method: str, path: str, payload: dict | None = None):
    try:
        response = client.request(method, path, json=payload)
    except (httpx.HTTPError, httpx.InvalidURL):
        raise ApiError("Не удалось связаться с API. Проверьте адрес и состояние бэкенда.") from None

    try:
        data = response.json()
    except ValueError:
        raise ApiError(f"API вернул неожиданный ответ (HTTP {response.status_code}).") from None
    if not response.is_success:
        detail = data.get("detail") if isinstance(data, dict) else None
        if isinstance(detail, list):
            detail = "; ".join(str(item.get("msg", "")) for item in detail if isinstance(item, dict))
        message = detail if isinstance(detail, str) and detail else f"HTTP {response.status_code}"
        raise ApiError(f"Ошибка API — {message}")
    return data


def local_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    timestamp = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(timestamp).astimezone(LOCAL_TIMEZONE)


def post_label(post: dict) -> str:
    channel = CHANNEL_NAMES.get(post["channel_type"], post["channel_type"])
    return f"{channel} · {post['topic']}"


def choose_plan(plans: list[dict], key: str) -> dict | None:
    if not plans:
        st.info("Сначала создайте контент-план.")
        return None
    by_id = {plan["id"]: plan for plan in plans}
    if st.session_state.get(key) not in by_id:
        st.session_state.pop(key, None)
    plan_id = st.selectbox(
        "Контент-план", list(by_id),
        format_func=lambda value: f"{by_id[value]['title']} · №{value}",
        key=key,
    )
    return by_id[plan_id]


def render_plan_tab(client: httpx.Client, plans: list[dict] | None) -> None:
    st.subheader("Новый план")
    now = datetime.now(LOCAL_TIMEZONE)
    with st.form("generate_plan"):
        left, right = st.columns(2)
        niche = left.text_input("Ниша", placeholder="Например, онлайн-образование")
        audience = right.text_input("Целевая аудитория")
        tone = left.text_input("Tone of voice", placeholder="Например, дружелюбный и экспертный")
        goals = right.text_input("Бизнес-цели", placeholder="Необязательно")
        month_col, year_col = st.columns(2)
        month = month_col.selectbox("Месяц", range(1, 13), index=now.month - 1, format_func=lambda m: MONTHS[m - 1])
        year = year_col.number_input("Год", min_value=1, max_value=9999, value=now.year, step=1)
        submitted = st.form_submit_button("Сгенерировать контент-план с AI", type="primary")
    if submitted:
        if not all(value.strip() for value in (niche, audience, tone)):
            st.warning("Заполните нишу, целевую аудиторию и Tone of voice.")
        else:
            try:
                with st.spinner("Генерируем контент-план…"):
                    created = api_request(client, "POST", f"{PLANS_URL}/generate", {
                        "niche": niche.strip(), "target_audience": audience.strip(),
                        "tone_of_voice": tone.strip(), "month": month, "year": int(year),
                        "goals": goals.strip() or None,
                    })
            except ApiError as exc:
                st.error(str(exc))
            else:
                st.session_state["plan_overview"] = created["id"]
                st.session_state["plan_content"] = created["id"]
                st.session_state["notice"] = "Контент-план создан"
                st.rerun()

    if plans is None:
        return
    st.subheader("Календарь публикаций")
    plan = choose_plan(plans, "plan_overview")
    if plan is None:
        return
    st.write(plan["title"])
    st.caption(f"{plan['month']:02d}.{plan['year']} · {plan['niche']}")
    posts = plan["posts"]
    post_count, channel_count = st.columns(2)
    post_count.metric("Посты в плане", len(posts))
    channel_count.metric("Каналы", len({post["channel_type"] for post in posts}))
    rows = []
    for post in posts:
        scheduled = local_datetime(post["scheduled_at"])
        rows.append({
            "День": scheduled.strftime("%d.%m.%Y") if scheduled else "—",
            "Канал": CHANNEL_NAMES.get(post["channel_type"], post["channel_type"]),
            "Тема": post["topic"],
            "Статус": STATUSES.get(post["status"], post["status"]),
        })
    st.dataframe(pd.DataFrame(rows, columns=["День", "Канал", "Тема", "Статус"]), hide_index=True)


def mutate(
    client: httpx.Client, method: str, path: str, notice: str, payload: dict | None = None,
) -> None:
    try:
        result = api_request(client, method, path, payload)
    except ApiError as exc:
        st.error(str(exc))
        return
    if result.get("status") != "failed":
        st.session_state["notice"] = notice
    st.rerun()


def render_variants(client: httpx.Client, post: dict) -> None:
    post_id = post["id"]
    variants = {variant["variant_label"]: variant for variant in post["variants"]}
    if st.button("Сгенерировать A/B варианты", disabled=len(variants) == 2, key=f"generate_{post_id}"):
        with st.spinner("Генерируем варианты…"):
            mutate(client, "POST", f"{POSTS_URL}/{post_id}/generate-variants", "Варианты A/B готовы")
    if not variants:
        return
    for column, label in zip(st.columns(2), ("A", "B")):
        with column, st.container(border=True):
            st.subheader(f"Вариант {label}")
            variant = variants.get(label)
            if variant is None:
                st.caption("Вариант ещё не сгенерирован.")
                continue
            if variant["is_winner"]:
                st.markdown(":green[● Победитель]")
            st.write(variant["title"])
            st.markdown(variant["body_text"])
            st.caption("Призыв к действию / CTA")
            st.text(variant["cta"])
            if st.button(
                "Назначить победителем", key=f"winner_{variant['id']}", disabled=variant["is_winner"],
            ):
                mutate(client, "PATCH", f"{POSTS_URL}/variants/{variant['id']}/select-winner",
                       f"Вариант {label} выбран победителем")


def render_publication(client: httpx.Client, post: dict) -> None:
    post_id = post["id"]
    st.subheader("Публикация")
    status = post["status"]
    st.write(f"Статус — {STATUSES.get(status, status)}")
    if post.get("external_id"):
        st.text(f"Внешний ID: {post['external_id']}")
    if post.get("publication_error"):
        st.error(post["publication_error"])
    scheduled = local_datetime(post["scheduled_at"])
    if status == "scheduled" and scheduled is not None:
        st.caption(f"По расписанию · {scheduled:%d.%m.%Y %H:%M} · {LOCAL_TIMEZONE.key}")
    if status == "published":
        return

    has_publishable_variant = any(
        variant["is_winner"] or variant["variant_label"] == "A" for variant in post["variants"]
    )
    if not has_publishable_variant:
        st.caption("Сгенерируйте варианты A/B перед мгновенной публикацией.")
    if st.button("Опубликовать сейчас", type="primary", disabled=not has_publishable_variant, key=f"publish_{post_id}"):
        with st.spinner("Публикуем пост…"):
            mutate(client, "POST", f"{POSTS_URL}/{post_id}/publish-now", "Пост опубликован")
    now = datetime.now(LOCAL_TIMEZONE)
    default = scheduled if scheduled and scheduled > now else now + timedelta(hours=1)
    with st.form(f"schedule_{post_id}"):
        date_column, time_column = st.columns(2)
        date = date_column.date_input("Дата публикации", value=default.date(), min_value=now.date())
        time = time_column.time_input("Время публикации", value=default.time())
        st.caption(f"Часовой пояс · {LOCAL_TIMEZONE.key}")
        submitted = st.form_submit_button("Запланировать")
    if submitted:
        due = datetime.combine(date, time, tzinfo=LOCAL_TIMEZONE)
        if due <= datetime.now(LOCAL_TIMEZONE):
            st.warning("Выберите будущее время.")
        else:
            mutate(client, "POST", f"{POSTS_URL}/{post_id}/schedule", "Пост запланирован",
                   {"scheduled_at": due.isoformat()})


def render_content_tab(client: httpx.Client, plans: list[dict]) -> None:
    plan = choose_plan(plans, "plan_content")
    if plan is None:
        return
    posts = {post["id"]: post for post in plan["posts"]}
    if not posts:
        st.info("В этом плане пока нет постов.")
        return
    post_id = st.selectbox("Пост", list(posts), format_func=lambda value: post_label(posts[value]),
                           key=f"content_post_{plan['id']}")
    post = posts[post_id]
    render_variants(client, post)
    render_publication(client, post)


def render_analytics_tab(client: httpx.Client, plans: list[dict]) -> None:
    summary = api_request(client, "GET", f"{ANALYTICS_URL}/summary")
    counts = summary["posts_by_channel"]
    total, ctr, channel_count = st.columns(3)
    total.metric("Всего постов", summary["total_posts"])
    average = summary["average_ctr"]
    ctr.metric("Средний CTR", f"{average:.2f}%" if average is not None else "—")
    if summary.get("average_ctr_source") == "simulated":
        ctr.caption("Демонстрационные данные")
    channel_count.metric("Количество каналов", sum(count > 0 for count in counts.values()))
    rows = pd.DataFrame([
        {"Канал": CHANNEL_NAMES.get(channel, channel), "Посты": count}
        for channel, count in counts.items()
    ], columns=["Канал", "Посты"])
    st.subheader("Посты по каналам")
    if not rows.empty:
        figure = px.bar(rows, x="Посты", y="Канал", orientation="h", color_discrete_sequence=["#2156D9"])
        figure.update_layout(height=300, margin=dict(l=0, r=12, t=12, b=0))
        figure.update_yaxes(autorange="reversed")
        st.plotly_chart(figure, config={"displayModeBar": False})

    st.subheader("A/B Анализ поста")
    posts = {
        post["id"]: post for plan in plans for post in plan["posts"] if post["status"] == "published"
    }
    if not posts:
        st.info("Сравнение появится после публикации поста.")
        return
    post_id = st.selectbox(
        "Опубликованный пост", list(posts), format_func=lambda value: post_label(posts[value]),
        key="analytics_post",
    )
    report = api_request(client, "GET", f"{ANALYTICS_URL}/ab-test/{post_id}")
    variants = report["variants"]
    if not any(variant.get("source") for variant in variants.values()):
        st.info("Метрики для этого поста ещё не собраны.")
    if any(variant.get("source") == "simulated" for variant in variants.values()):
        st.caption("Сравнение содержит демонстрационные данные.")
    comparison = {"Метрика": ["Показы", "Клики", "CTR", "Конверсии"]}
    for label in ("A", "B"):
        stats = variants.get(label)
        comparison[label] = (
            [str(stats["views"]), str(stats["clicks"]), f"{stats['ctr']:.2f}%", str(stats["conversions"])]
            if stats and stats.get("source") else ["—"] * 4
        )
    st.dataframe(pd.DataFrame(comparison), hide_index=True)
    difference = report["ctr_difference_percentage_points"]
    if difference is not None:
        st.metric("Разница CTR (B − A)", f"{difference:+.2f} п. п.")
    p_value = report["p_value"]
    if p_value is not None:
        st.caption(f"p-value · {p_value:.4g}")
        if p_value < 0.05 and report["statistical_winner"]:
            st.success(f"Статистический победитель — вариант {report['statistical_winner']}")


def render_channels_tab(client: httpx.Client) -> None:
    readiness = api_request(client, "GET", "/api/v1/channels/status")
    by_type = {channel["channel_type"]: channel for channel in readiness}
    labels = {
        "demo": ":blue[● Demo]",
        "real": ":green[● Real API]",
        "incomplete": ":orange[● Требуется настройка]",
    }
    for index, (channel, name) in enumerate(CHANNEL_NAMES.items()):
        if index % 3 == 0:
            columns = st.columns(3)
        state = by_type.get(channel)
        with columns[index % 3], st.container(border=True):
            st.subheader(name)
            if state is not None:
                st.markdown(labels[state["mode"]])
                st.caption("Ключи в credentials_json")
                st.code(", ".join(state["required_keys"]), language=None)
                if state["mode"] == "incomplete":
                    st.warning("Заполните " + ", ".join(state["missing_keys"]))
            st.caption(CHANNEL_HINTS[channel])


def main() -> None:
    st.title("AI Content Marketing Studio")
    api_url = st.sidebar.text_input("API URL", value="http://127.0.0.1:8000").strip().rstrip("/")
    try:
        parsed_url = httpx.URL(api_url)
        valid_url = parsed_url.scheme in {"http", "https"} and parsed_url.host
    except httpx.InvalidURL:
        valid_url = False
    if st.session_state.get("connected_url") != api_url:
        for key in ("plan_overview", "plan_content", "analytics_post", "notice"):
            st.session_state.pop(key, None)
        st.session_state["connected_url"] = api_url
    with httpx.Client(base_url=api_url if valid_url else "", timeout=10.0) as client:
        online = False
        if valid_url:
            try:
                online = api_request(client, "GET", "/health").get("status") == "ok"
            except (ApiError, AttributeError):
                pass
        st.sidebar.markdown(":green[● Online]" if online else ":red[● Offline]")
        st.sidebar.button("Обновить данные")
        tabs = st.tabs([
            "Генерация контент-плана", "Контент & A/B тестирование",
            "Сквозная аналитика", "Каналы публикации",
        ])
        if not online:
            st.info("Подключите бэкенд через API URL в боковой панели.")
            return
        notice = st.session_state.pop("notice", None)
        if notice:
            st.toast(notice)
        plans = None
        try:
            plans = api_request(client, "GET", f"{PLANS_URL}/")
        except ApiError as exc:
            st.error(str(exc))
        with tabs[0]:
            render_plan_tab(client, plans)
        with tabs[1]:
            if plans is not None:
                render_content_tab(client, plans)
        with tabs[2]:
            try:
                render_analytics_tab(client, plans or [])
            except ApiError as exc:
                st.error(str(exc))
        with tabs[3]:
            try:
                render_channels_tab(client)
            except ApiError as exc:
                st.error(str(exc))


if __name__ == "__main__":
    main()
