import os
import sys
from pathlib import Path

# Add backend directory and repo root to sys.path so config and apps can be imported on Vercel
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

repo_root = backend_dir.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application

# On Vercel serverless: ensure tables exist in SQLite if needed
if os.getenv("VERCEL"):
    try:
        from django.db import connection
        tables = connection.introspection.table_names()
        if "django_session" not in tables:
            from django.core.management import call_command
            call_command("migrate", interactive=False)
            try:
                call_command("seed_careers")
            except Exception:
                pass
    except Exception as e:
        print("Vercel DB initialization note:", e)

