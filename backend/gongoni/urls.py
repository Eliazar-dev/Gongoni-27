from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import include, path, re_path


def home(request):
    if (settings.FRONTEND_DIST / "index.html").exists():
        return render(request, "index.html")
    return JsonResponse({"status": "ok", "service": "Gongoni 27 API"})


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("tracker.urls")),
    re_path(r"^(?!api/|django-admin/|static/).*$", home),
]
