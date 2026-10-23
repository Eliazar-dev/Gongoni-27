import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gongoni.settings')

# Initialize Django
import django
django.setup()

# Import WSGI app
from gongoni.wsgi import application

# Vercel expects this
app = application
