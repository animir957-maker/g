from django.contrib import admin
from .models import Project, ProjectMembership, Task, TaskAttachment, NotificationDelivery, WebhookEvent

admin.site.register(Project)
admin.site.register(ProjectMembership)
admin.site.register(Task)
admin.site.register(TaskAttachment)
admin.site.register(NotificationDelivery)
admin.site.register(WebhookEvent)
