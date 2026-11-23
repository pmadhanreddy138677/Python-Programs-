# Circliq production image (ASGI via Daphne: HTTP + WebSockets in one process)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Collect static files at build time. These two values exist only for this command and are not kept in the image.
RUN SECRET_KEY=build-only-build-only-build-only-build-only-0123456789 ALLOWED_HOSTS=build.invalid \
    DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 circliq && mkdir -p /app/media && chown -R circliq /app/media
USER circliq

ENV DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=4).status==200 else 1)"
CMD ["sh", "-c", "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p 8000 config.asgi:application"]
