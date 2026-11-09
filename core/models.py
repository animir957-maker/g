import uuid
from django.conf import settings
from django.db import models

class Project(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_projects")
    allow_external_updates = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ProjectMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        MEMBER = "member", "Участник"
        VIEWER = "viewer", "Наблюдатель"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "user"], name="unique_project_member")]

class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "К выполнению"
        PROGRESS = "progress", "В процессе"
        DONE = "done", "Готово"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="assigned_tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class NotificationDelivery(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    state = models.CharField(max_length=20, choices=State.choices, default=State.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(upload_to="task_attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

class WebhookEvent(models.Model):
    event_id = models.CharField(max_length=128, unique=True)
    task = models.ForeignKey(Task, on_delete=models.PROTECT)
    received_at = models.DateTimeField(auto_now_add=True)
    payload_hash = models.CharField(max_length=64)
