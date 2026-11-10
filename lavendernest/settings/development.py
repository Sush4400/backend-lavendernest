"""Development settings for LavenderNest."""

import os
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'lavnest',
        'USER': 'postgres',
        'PASSWORD': 'root',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 5,
        },
    }
}


# Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Disable throttling in development
REST_FRAMEWORK = {
    **globals().get("REST_FRAMEWORK", {}),  # type: ignore[arg-type]
}
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
