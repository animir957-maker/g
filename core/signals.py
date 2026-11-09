from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Task, NotificationDelivery
from .cache_utils import invalidate_project_stats

@receiver(pre_save, sender=Task)
def remember_old_task_project(sender, instance, **kwargs):
    if instance.pk:
        instance._old_project_id = sender.objects.filter(pk=instance.pk).values_list("project_id", flat=True).first()
        instance._old_assignee_id = sender.objects.filter(pk=instance.pk).values_list("assigned_to_id", flat=True).first()
    else:
        instance._old_project_id = None
        instance._old_assignee_id = None

@receiver(post_save, sender=Task)
def task_saved(sender, instance, created, **kwargs):
    invalidate_project_stats(instance.project_id)
    old_project_id = getattr(instance, "_old_project_id", None)
    if old_project_id and old_project_id != instance.project_id:
        invalidate_project_stats(old_project_id)

    old_assignee = getattr(instance, "_old_assignee_id", None)
    if instance.assigned_to_id and instance.assigned_to_id != old_assignee:
        delivery = NotificationDelivery.objects.create(
            task=instance, assignee_id=instance.assigned_to_id
        )
        event_id = str(delivery.event_id)
        from .tasks import send_assignment_notification
        task_id = instance.pk
        assignee_id = instance.assigned_to_id
        transaction.on_commit(
            lambda task_id=task_id, assignee_id=assignee_id, event_id=event_id:
                send_assignment_notification.delay(task_id, assignee_id, event_id)
        )

@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
    invalidate_project_stats(instance.project_id)
