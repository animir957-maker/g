import hashlib
import hmac
import json
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import Project, ProjectMembership, Task, WebhookEvent, NotificationDelivery
from .cache_utils import stats_key

User = get_user_model()

class BackendLabsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass", email="owner@example.com")
        self.member = User.objects.create_user(username="member", password="pass", email="member@example.com")
        self.outsider = User.objects.create_user(username="outsider", password="pass")
        self.project = Project.objects.create(name="Demo", owner=self.owner, allow_external_updates=True)
        ProjectMembership.objects.create(project=self.project, user=self.member)
        self.task = Task.objects.create(project=self.project, title="Task")
        self.client = APIClient()
        cache.clear()

    def test_stats_access_checked_and_cached(self):
        self.client.force_authenticate(self.owner)
        url = f"/api/projects/{self.project.id}/stats/"
        first = self.client.get(url)
        second = self.client.get(url)
        self.assertEqual(first.data, second.data)
        self.assertEqual(second.data["total"], 1)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_task_status_change_invalidates_stats(self):
        cache.set(stats_key(self.project.id), {"total": 99}, 60)
        self.task.status = Task.Status.DONE
        with self.captureOnCommitCallbacks(execute=True):
            self.task.save()
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/projects/{self.project.id}/stats/")
        self.assertEqual(response.data["done"], 1)

    @patch("core.tasks.send_assignment_notification.delay")
    def test_assignment_notification_scheduled_after_commit(self, delay):
        self.task.assigned_to = self.member
        with self.captureOnCommitCallbacks(execute=True):
            self.task.save()
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        delay.assert_called_once()

    def test_attachment_upload_and_access_control(self):
        self.client.force_authenticate(self.member)
        png = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"
        upload = SimpleUploadedFile("picture.png", png, content_type="image/png")
        response = self.client.post(f"/api/tasks/{self.task.id}/attachments/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 201)
        attachment_id = response.data["id"]
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(f"/api/attachments/{attachment_id}/").status_code, 403)

    @override_settings(WEBHOOK_SECRET="test-secret")
    def test_webhook_signature_and_duplicate(self):
        payload = {"event_id": "evt-001", "task_id": self.task.id,
                   "status": "progress", "timestamp": int(time.time())}
        raw = json.dumps(payload).encode()
        signature = hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
        response = self.client.post("/api/webhooks/task-events/", data=raw,
                                    content_type="application/json", HTTP_X_SIGNATURE=signature)
        self.assertEqual(response.status_code, 202)
        duplicate = self.client.post("/api/webhooks/task-events/", data=raw,
                                     content_type="application/json", HTTP_X_SIGNATURE=signature)
        self.assertEqual(duplicate.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PROGRESS)
        self.assertEqual(WebhookEvent.objects.filter(event_id="evt-001").count(), 1)
