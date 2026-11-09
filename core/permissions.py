from rest_framework.permissions import BasePermission
from .models import ProjectMembership

def user_can_access_project(user, project):
    if not user or not user.is_authenticated:
        return False
    return project.owner_id == user.id or ProjectMembership.objects.filter(
        project=project, user=user
    ).exists()

class IsProjectMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        project = getattr(obj, "project", obj)
        return user_can_access_project(request.user, project)
