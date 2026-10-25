from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import include, path
from django.utils import timezone


def home(request):
    data = {"status": "ok", "service": "Gongoni 27 API"}
    # Keep JSON for health checks / API clients; show the status page in browsers.
    if "text/html" not in request.headers.get("Accept", ""):
        return JsonResponse(data)
    return render(
        request,
        "server_status.html",
        {**data, "debug": settings.DEBUG, "server_time": timezone.now()},
    )


urlpatterns = [
    path("", home),
    path("django-admin/", admin.site.urls),
    path("api/", include("tracker.urls")),
]
