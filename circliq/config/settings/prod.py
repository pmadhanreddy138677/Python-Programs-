from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa

DEBUG = False

# Refuse to start with unsafe defaults.
if SECRET_KEY.startswith("dev-insecure") or len(SECRET_KEY) < 40:
    raise ImproperlyConfigured("Set a long random SECRET_KEY in the environment (see .env.production.example).")
if not ALLOWED_HOSTS or set(ALLOWED_HOSTS) <= {"localhost", "127.0.0.1"}:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS to your real domain name(s).")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # opt in deliberately once you're sure every subdomain stays on HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=True)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Circliq <no-reply@example.com>")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
