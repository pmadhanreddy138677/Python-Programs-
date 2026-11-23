"""Small cache-based rate limiter (fixed window). Uses the configured cache: set REDIS_URL in production so limits are shared across processes."""
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render


def client_ip(request):
    if getattr(settings, "TRUST_PROXY_HEADERS", False):
        fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def hit(key, limit, window):
    """Count one event. Returns True while the caller is still under the limit."""
    cache.add(key, 0, window)
    try:
        n = cache.incr(key)
    except ValueError:  # key expired between add and incr
        cache.set(key, 1, window)
        n = 1
    return n <= limit


def over_limit(request, scope, limit, window, per="user"):
    who = request.user.pk if per == "user" and request.user.is_authenticated else client_ip(request)
    return not hit(f"rl:{scope}:{who}", limit, window)


def rate_limit(scope, limit, window, per="user", methods=("POST",)):
    """View decorator. Returns the friendly 429 page when exceeded."""
    def deco(view):
        @wraps(view)
        def wrapped(request, *a, **kw):
            if request.method in methods and over_limit(request, scope, limit, window, per):
                return render(request, "errors/429.html", status=429)
            return view(request, *a, **kw)
        return wrapped
    return deco
