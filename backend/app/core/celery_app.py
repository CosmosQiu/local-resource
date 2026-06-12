"""
Celery application configuration.
Worker: celery -A app.core.celery_app worker --loglevel=info
Beat:   celery -A app.core.celery_app beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "ai_resource_hub",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_always_eager=settings.APP_ENV == "development",
    imports=["app.tasks.cookie_checker"],
)

# Beat schedule — cookie verification daily at 2 AM
celery_app.conf.beat_schedule = {
    "verify-ai-account-cookies": {
        "task": "app.tasks.cookie_checker.verify_all_account_cookies",
        "schedule": crontab(hour=2, minute=0),
    },
}
