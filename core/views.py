import hashlib
import hmac
import json
import logging
import time
import uuid
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction, connection
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .cache_utils import get_project_stats
from .models import Project, Task, TaskAttachment, WebhookEvent
from .permissions import user_can_access_project
from .serializers import TaskSerializer, AttachmentUploadSerializer

logger = logging.getLogger(__name__)

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(
            project__owner=self.request.user
        ) | Task.objects.filter(project__memberships__user=self.request.user)

    def perform_create(self, serializer):
        project = get_object_or_404(Project, pk=self.request.data.get("project"))
        if not user_can_access_project(self.request.user, project):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Нет доступа к проекту")
        serializer.save()

    def perform_update(self, serializer):
        task = self.get_object()
        target_project = serializer.validated_data.get("project", task.project)
        if not user_can_access_project(self.request.user, target_project):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Нет доступа к целевому проекту")
        serializer.save()

class ProjectStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        if not user_can_access_project(request.user, project):
            return Response({"detail": "Нет доступа к проекту"}, status=403)
        # Проверка доступа выполняется до обращения к кешу.
        return Response(get_project_stats(project))

class TaskAttachmentView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        if not user_can_access_project(request.user, task.project):
            return Response({"detail": "Нет доступа"}, status=403)
        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        safe_name = get_valid_filename(upload.name)[:200] or "attachment"
        attachment = TaskAttachment.objects.create(
            task=task, uploaded_by=request.user, file=upload,
            original_name=safe_name, size=upload.size
        )
        return Response({"id": attachment.id, "original_name": attachment.original_name,
                         "size": attachment.size}, status=201)

class AttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = get_object_or_404(TaskAttachment, pk=attachment_id)
        if not user_can_access_project(request.user, attachment.task.project):
            return Response({"detail": "Нет доступа"}, status=403)
        response = FileResponse(attachment.file.open("rb"), as_attachment=True,
                                filename=attachment.original_name)
        return response

    def delete(self, request, attachment_id):
        attachment = get_object_or_404(TaskAttachment, pk=attachment_id)
        if not user_can_access_project(request.user, attachment.task.project):
            return Response({"detail": "Нет доступа"}, status=403)
        attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=204)

class TaskWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        raw = request.body
        if len(raw) > settings.MAX_WEBHOOK_BODY:
            return Response({"detail": "Payload слишком большой"}, status=413)
        secret = settings.WEBHOOK_SECRET
        signature = request.headers.get("X-Signature", "")
        if not secret or not signature:
            return Response({"detail": "Webhook signature required"}, status=401)
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return Response({"detail": "Invalid signature"}, status=401)
        try:
            payload = json.loads(raw)
            event_id = str(payload["event_id"])
            task_id = int(payload["task_id"])
            new_status = payload["status"]
            timestamp = int(payload["timestamp"])
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return Response({"detail": "Invalid payload"}, status=400)
        if abs(time.time() - timestamp) > settings.WEBHOOK_MAX_AGE_SECONDS:
            return Response({"detail": "Expired timestamp"}, status=400)
        if new_status not in Task.Status.values:
            return Response({"detail": "Invalid status"}, status=400)

        try:
            with transaction.atomic():
                task = Task.objects.select_for_update().select_related("project").get(pk=task_id)
                if not task.project.allow_external_updates:
                    return Response({"detail": "Integration is disabled"}, status=403)
                allowed = {
                    Task.Status.TODO: {Task.Status.PROGRESS},
                    Task.Status.PROGRESS: {Task.Status.DONE},
                    Task.Status.DONE: set(),
                }
                if new_status != task.status and new_status not in allowed[task.status]:
                    return Response({"detail": "Invalid status transition"}, status=409)
                WebhookEvent.objects.create(
                    event_id=event_id, task=task, payload_hash=hashlib.sha256(raw).hexdigest()
                )
                task.status = new_status
                task.save(update_fields=["status", "updated_at"])
        except IntegrityError:
            return Response({"status": "duplicate"}, status=200)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found"}, status=404)
        return Response({"status": "accepted"}, status=202)

def live(request):
    return JsonResponse({"status": "ok"})

def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        cache.set("health-check", "ok", timeout=5)
        if cache.get("health-check") != "ok":
            raise RuntimeError("Redis unavailable")
        return JsonResponse({"status": "ready"})
    except Exception:
        logger.exception("Readiness check failed")
        return JsonResponse({"status": "not_ready"}, status=503)
