import logging
from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import NotificationDelivery

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_assignment_notification(self, task_id, user_id, event_id):
    try:
        # Блокировка строки сериализует параллельные повторы одного event_id.
        with transaction.atomic():
            delivery = NotificationDelivery.objects.select_for_update().get(event_id=event_id)
            if delivery.state == NotificationDelivery.State.SENT:
                return "duplicate"
            delivery.attempts += 1
            delivery.save(update_fields=["attempts"])
            email = delivery.assignee.email
            if not email:
                delivery.state = NotificationDelivery.State.FAILED
                delivery.last_error = "У пользователя не указан email"
                delivery.save(update_fields=["state", "last_error"])
                return "no-email"
            send_mail(
                subject="Вам назначена задача",
                message=f"Вам назначена задача #{task_id}.",
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
            delivery.state = NotificationDelivery.State.SENT
            delivery.sent_at = timezone.now()
            delivery.last_error = ""
            delivery.save(update_fields=["state", "sent_at", "last_error"])
        return "sent"
    except Exception as exc:
        logger.exception("Assignment notification failed", extra={"event_id": event_id})
        NotificationDelivery.objects.filter(event_id=event_id).update(last_error=str(exc)[:500])
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries * 5, 60))
