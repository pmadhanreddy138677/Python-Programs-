def badges(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    from apps.messaging.services import total_unread
    from .services import unread_count
    return {"unread_notifications": unread_count(user), "unread_messages": total_unread(user)}
