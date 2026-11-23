from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Liveness/readiness probe for load balancers and uptime monitors. Reveals nothing sensitive."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
