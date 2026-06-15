"""Development settings."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Allow all origins in development for convenience.
CORS_ALLOW_ALL_ORIGINS = True
