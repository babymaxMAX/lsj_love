from celery import Celery

from core_v2.backend.settings import V2Settings


settings = V2Settings()
celery_app = Celery(
    "ai_kupidon_v2",
    broker=settings.redis_dsn,
    backend=settings.redis_dsn,
)


@celery_app.task(name="core_v2.workers.send_notification")
def send_notification_task(user_id: str, text: str) -> dict:
    return {"ok": True, "user_id": user_id, "text": text}


@celery_app.task(name="core_v2.workers.process_ai_request")
def process_ai_request_task(request_id: str) -> dict:
    return {"ok": True, "request_id": request_id, "status": "processed"}


@celery_app.task(name="core_v2.workers.send_campaign_batch")
def send_campaign_batch_task(campaign_id: str, user_ids: list[str]) -> dict:
    return {"ok": True, "campaign_id": campaign_id, "queued_users": len(user_ids)}
