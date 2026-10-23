import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gongoni.settings')

# Configure Django
import django
django.setup()

# Import the WSGI application
from gongoni.wsgi import application

# Export for Vercel
app = application
