"""Celery application — Redis broker, task autodiscovery (FR-023, cascade lock, cycle detection)."""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "doce_erp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.cascade_lock",
        "app.tasks.cycle_detection",
        "app.tasks.obsolete_scan",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.cascade_lock.*": {"queue": "high_priority"},
        "app.tasks.cycle_detection.*": {"queue": "low_priority"},
        "app.tasks.obsolete_scan.*": {"queue": "low_priority"},
    },
)

# Periodic task: expire wizard sessions (FR-043)
celery_app.conf.beat_schedule = {
    "expire-wizard-sessions": {
        "task": "app.tasks.cascade_lock.expire_wizard_sessions",
        "schedule": 3600.0,  # every hour
    },
    "audit-package-storage-check": {
        "task": "app.tasks.obsolete_scan.check_audit_package_storage",
        "schedule": 86400.0,  # daily
    },
}
