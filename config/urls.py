from django.contrib import admin
from django.urls import path, include
from core.views import live, ready

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("health/live/", live),
    path("health/ready/", ready),
]
