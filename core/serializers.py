from rest_framework import serializers
from .models import Task, TaskAttachment

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "project", "title", "description", "status", "assigned_to", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class AttachmentUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField()
    class Meta:
        model = TaskAttachment
        fields = ["id", "file", "original_name", "size", "uploaded_at"]
        read_only_fields = ["id", "original_name", "size", "uploaded_at"]

    def validate_file(self, upload):
        from django.conf import settings
        from rest_framework.exceptions import ValidationError
        if upload.size > settings.MAX_ATTACHMENT_SIZE:
            raise ValidationError("Файл больше 5 МБ")
        name = upload.name.lower()
        if name.endswith(".pdf"):
            signature = upload.read(5)
            upload.seek(0)
            if signature != b"%PDF-":
                raise ValidationError("Содержимое не похоже на PDF")
        elif name.endswith(".png"):
            signature = upload.read(8)
            upload.seek(0)
            if signature != b"\x89PNG\r\n\x1a\n":
                raise ValidationError("Содержимое не похоже на PNG")
        else:
            raise ValidationError("Разрешены только PDF и PNG")
        return upload
