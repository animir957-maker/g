from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, ProjectStatsView, TaskAttachmentView, AttachmentDownloadView, TaskWebhookView

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("", include(router.urls)),
    path("projects/<int:project_id>/stats/", ProjectStatsView.as_view(), name="project-stats"),
    path("tasks/<int:task_id>/attachments/", TaskAttachmentView.as_view(), name="task-attachments"),
    path("attachments/<int:attachment_id>/", AttachmentDownloadView.as_view(), name="attachment-detail"),
    path("webhooks/task-events/", TaskWebhookView.as_view(), name="task-webhook"),
]
