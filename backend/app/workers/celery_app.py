"""
Responsibility: Celery application instance + configuration.

No task logic lives here -- just the app factory. See
workers/document_tasks.py for the actual background jobs.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ai_support_saas",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # See core/config.py's docstring on celery_task_always_eager: True in
    # tests makes .delay() execute synchronously in-process with no
    # broker connection required, so the ingestion pipeline can be tested
    # end-to-end without Redis or a separate worker process running.
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
)
