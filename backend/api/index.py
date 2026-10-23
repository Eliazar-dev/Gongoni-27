import os
import sys

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gongoni.settings')

# Import and setup Django
import django
django.setup()

# Import WSGI application
from gongoni.wsgi import application

# Vercel expects this
app = application
