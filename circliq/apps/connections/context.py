from .models import Connection

UPCOMING = [("Events", 5), ("Messages", 5), ("Notifications", 5)]


def pending_requests(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"pending_requests_count": Connection.objects.filter(receiver=user, status="pending").count(),
            "coming_soon": UPCOMING}
