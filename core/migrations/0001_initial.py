import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='Project', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=200)), ('allow_external_updates', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_projects', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='ProjectMembership', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('role', models.CharField(choices=[('admin', 'Администратор'), ('member', 'Участник'), ('viewer', 'Наблюдатель')], default='member', max_length=20)),
            ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='core.project')),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_memberships', to=settings.AUTH_USER_MODEL)),
        ], options={'constraints': [models.UniqueConstraint(fields=('project', 'user'), name='unique_project_member')]}),
        migrations.CreateModel(name='Task', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('title', models.CharField(max_length=250)), ('description', models.TextField(blank=True)),
            ('status', models.CharField(choices=[('todo', 'К выполнению'), ('progress', 'В процессе'), ('done', 'Готово')], default='todo', max_length=20)),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tasks', to=settings.AUTH_USER_MODEL)),
            ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='core.project')),
        ]),
        migrations.CreateModel(name='NotificationDelivery', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('event_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ('state', models.CharField(choices=[('pending', 'Ожидает'), ('sent', 'Отправлено'), ('failed', 'Ошибка')], default='pending', max_length=20)),
            ('attempts', models.PositiveSmallIntegerField(default=0)), ('last_error', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('sent_at', models.DateTimeField(blank=True, null=True)),
            ('assignee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.task')),
        ]),
        migrations.CreateModel(name='TaskAttachment', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('file', models.FileField(upload_to='task_attachments/%Y/%m/')), ('original_name', models.CharField(max_length=255)),
            ('size', models.PositiveBigIntegerField()), ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='core.task')),
            ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='WebhookEvent', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('event_id', models.CharField(max_length=128, unique=True)), ('received_at', models.DateTimeField(auto_now_add=True)),
            ('payload_hash', models.CharField(max_length=64)),
            ('task', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.task')),
        ]),
    ]
