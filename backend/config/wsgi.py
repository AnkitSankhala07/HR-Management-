import os
import sys
from pathlib import Path

# Add backend directory to sys.path so config and apps can be imported on Vercel
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
