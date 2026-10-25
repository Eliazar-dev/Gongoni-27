from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def home(request):
    return JsonResponse({"status": "ok", "service": "Gongoni 27 API"})


urlpatterns = [
    path("", home),
    path("django-admin/", admin.site.urls),
    path("api/", include("tracker.urls")),
]
