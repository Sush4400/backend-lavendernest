"""WSGI config for LavenderNest project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lavendernest.settings.development")
application = get_wsgi_application()
