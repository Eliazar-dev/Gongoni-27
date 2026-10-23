from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path, re_path


def spa(request):
    """Serve the React app for every page that is not the API."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return HttpResponse(
            "Frontend not built yet. Run 'npm install && npm run build' inside the frontend folder.",
            status=503,
            content_type="text/plain",
        )
    return render(request, "index.html")


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("tracker.urls")),
    re_path(r"^(?!api/|django-admin/|static/).*$", spa),
]
