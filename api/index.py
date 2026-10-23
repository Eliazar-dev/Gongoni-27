import os
import sys

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gongoni.settings')

# Initialize Django
import django
django.setup()

# Import WSGI app
from gongoni.wsgi import application

# Vercel serverless function handler
def handler(event, context):
    return application

# For Vercel compatibility
app = application
