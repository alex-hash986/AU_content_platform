from celery import Celery

from app.core.config import settings

celery_app = Celery("content_marketing", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.autodiscover_tasks(["app.tasks"], related_name="publishing")
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "publish-scheduled-posts": {
            "task": "app.tasks.publishing.check_and_publish_scheduled_posts",
            "schedule": 30.0,
            "options": {"expires": 30},
        },
        "collect-post-metrics": {
            "task": "app.tasks.publishing.collect_post_metrics",
            "schedule": 300.0,
            "options": {"expires": 300},
        },
    },
)
