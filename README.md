# Backend Labs 7–12 — Django REST Framework

Учебный backend-проект, в котором объединены лабораторные №7–12:
Redis cache, Celery notifications, task attachments, signed webhooks, Docker Compose, CI и production observability.

> **Важно об интеграции с лабораторными №1–6:** исходники твоего проекта №1–6 не были приложены к сообщению. Поэтому здесь создан самостоятельный совместимый scaffold с моделями `Project`, `ProjectMembership` и `Task`. Если у тебя уже есть эти модели, перенеси функции/сервисы и адаптируй поля, не создавай дублирующие таблицы.

## 1. Запуск через Docker

1. Скопируй `.env.example` в `.env`.
2. Измени `DJANGO_SECRET_KEY` и `WEBHOOK_SECRET` на свои случайные значения.
3. Запусти:

```bash
docker compose up --build
```

API: `http://localhost:8000/`

Создать администратора:

```bash
docker compose exec web python manage.py createsuperuser
```

Тесты:

```bash
docker compose exec web python manage.py test
```

Остановить:

```bash
docker compose down
```

Удалить также данные PostgreSQL (ОСТОРОЖНО):

```bash
docker compose down -v
```

## 2. Локальный запуск без Docker

Нужны PostgreSQL и Redis. Создай виртуальное окружение, установи зависимости и задай переменные из `.env.example`.

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py runserver
```

В отдельном терминале:

```bash
celery -A config worker -l info
```

Для учебной отправки email можно добавить в `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@example.local
```

Настройка email backend уже читается из переменной `EMAIL_BACKEND` в `config/settings.py`.

## 3. API endpoints

| Метод | Endpoint | Назначение |
|---|---|---|
| GET | `/api/projects/{id}/stats/` | Статистика проекта с Redis cache |
| GET/POST | `/api/tasks/` | Список и создание задач |
| GET/PATCH/DELETE | `/api/tasks/{id}/` | Работа с задачей |
| POST | `/api/tasks/{id}/attachments/` | Загрузить PDF/PNG |
| GET/DELETE | `/api/attachments/{id}/` | Скачать/удалить вложение |
| POST | `/api/webhooks/task-events/` | Приём подписанного webhook |
| GET | `/health/live/` | Liveness |
| GET | `/health/ready/` | Readiness: PostgreSQL + Redis |

Для API-запросов требуется аутентификация DRF. Для простоты в учебном scaffold включены Session и Basic Authentication; в реальном проекте лучше подключить JWT или другой выбранный способ авторизации.

## 4. Что где реализовано

- `core/cache_utils.py` — cache-aside, TTL 60 секунд, ключ `project-stats:v1:{project_id}`.
- `core/signals.py` — инвалидизация статистики после commit; создание события назначения.
- `core/tasks.py` — Celery task, ограниченные retries, журнал NotificationDelivery.
- `core/serializers.py` — проверка размера и сигнатуры PDF/PNG.
- `core/views.py` — stats, attachments, HMAC webhook, health endpoints.
- `core/middleware.py` — request_id, метод, путь, HTTP status и duration в логах.
- `Dockerfile`, `compose.yaml` — приложение, PostgreSQL, Redis и worker.
- `.github/workflows/ci.yml` — тесты в GitHub Actions.

## 5. Проверка webhook

Подпись — hex HMAC-SHA256 от **сырых байтов тела** запроса. Заголовок: `X-Signature`.

Пример Python для генерации подписи:

```python
import hashlib, hmac, json, time
body = json.dumps({
    "event_id": "evt-001",
    "task_id": 1,
    "status": "progress",
    "timestamp": int(time.time())
}).encode()
signature = hmac.new(
    b"your-webhook-secret", body, hashlib.sha256
).hexdigest()
print(signature)
```

Разрешённые переходы: `todo -> progress -> done`. Повторный `event_id` возвращает `200` и не выполняет действие повторно.

## 6. Важные замечания для защиты

1. **Доступ проверяется до кеша.** Endpoint статистики сначала проверяет членство пользователя, затем читает Redis.
2. **Кеш инвалидируется после commit.** Создание, обновление и удаление задачи сбрасывает статистику.
3. **Уведомления ставятся после commit.** При rollback Celery-задача не отправляется.
4. **Файлы закрыты проверкой членства.** Нельзя скачать вложение только по известному ID.
5. **Webhook проверяет подпись и timestamp.** Уникальный `event_id` защищает от повторной обработки.
6. **Не храни `.env` в Git.** Для production используй секреты окружения и отдельное хранилище файлов.
7. Перед реальным production-развёртыванием добавь HTTPS reverse proxy, rate limiting, JWT, антивирусную проверку файлов и полноценные интеграционные тесты.

## 7. Миграции

После изменения моделей:

```bash
python manage.py makemigrations
python manage.py migrate
```

В Docker:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```
