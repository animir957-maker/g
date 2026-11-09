from django.core.cache import cache
from django.db import transaction

STATS_TTL = 60

def stats_key(project_id):
    return f"project-stats:v1:{project_id}"

def invalidate_project_stats(project_id):
    transaction.on_commit(lambda: cache.delete(stats_key(project_id)))

def get_project_stats(project):
    key = stats_key(project.pk)
    cached = cache.get(key)
    if cached is not None:
        return cached
    qs = project.tasks
    result = {
        "total": qs.count(),
        "todo": qs.filter(status="todo").count(),
        "progress": qs.filter(status="progress").count(),
        "done": qs.filter(status="done").count(),
    }
    cache.set(key, result, STATS_TTL)
    return result
