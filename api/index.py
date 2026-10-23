"""Vercel entry point: exposes the Django WSGI app as `app`."""
import os
import sys
from urllib.parse import parse_qsl, urlencode

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gongoni.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

_django = get_wsgi_application()


def app(environ, start_response):
    # vercel.json rewrites /api/<x> to /api/index?__p=<x>. Restore the real path for Django.
    if environ.get("PATH_INFO", "").startswith("/api/index"):
        pairs = parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        rest = [(k, v) for k, v in pairs if k != "__p"]
        p = next((v for k, v in pairs if k == "__p"), "")
        environ["PATH_INFO"] = "/api/" + p.lstrip("/")
        environ["QUERY_STRING"] = urlencode(rest)
    return _django(environ, start_response)
