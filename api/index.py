import os
import sys

# Add backend to path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gongoni.settings')

# Import and setup Django
import django
django.setup()

# Import Django's ASGI handler (better for serverless)
from django.core.asgi import get_asgi_application
asgi_app = get_asgi_application()

# For Vercel - use ASGI
app = asgi_app
