from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification
from .services import unread_count


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user).select_related("actor__profile")
    tab = request.GET.get("tab", "all")
    if tab == "unread":
        qs = qs.filter(is_read=False)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {"page": page, "tab": tab})


@login_required
def preview(request):
    items = Notification.objects.filter(user=request.user).select_related("actor__profile")[:6]
    return render(request, "notifications/_preview.html", {"items": items})


@login_required
def count(request):
    return JsonResponse({"unread": unread_count(request.user)})


@login_required
def open_notification(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    return redirect(n.url or "notifications:list")


@login_required
@require_POST
def mark_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"unread": 0})
    return redirect("notifications:list")
