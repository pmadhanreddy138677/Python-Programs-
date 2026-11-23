from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services as s
from .models import Conversation, ConversationParticipant as CP, Message

User = get_user_model()
PAGE = 40


def _conv(user, pk):
    conv = get_object_or_404(Conversation, pk=pk, institution_id=user.institution_id)
    if not s.participant(user, conv):
        raise Http404
    return conv


@login_required
def inbox(request, pk=None):
    me = request.user
    rows = list(s.conversations_for(me))
    for r in rows:
        r.title = s.title_for(r.conversation, me)
        r.other = s.other_party(r.conversation, me)
    ctx = {"rows": rows, "active": None}
    if pk:
        conv = _conv(me, pk)
        before = request.GET.get("before", "")
        qs = conv.messages.select_related("sender__profile")
        if before.isdigit():
            qs = qs.filter(pk__lt=int(before))
        chunk = list(qs.order_by("-created_at", "-id")[:PAGE + 1])
        has_more = len(chunk) > PAGE
        msgs = list(reversed(chunk[:PAGE]))
        s.mark_read(conv, me)
        for r in rows:
            if r.conversation_id == conv.pk:
                r.unread = 0
        ctx.update(active=conv, title=s.title_for(conv, me), other=s.other_party(conv, me), msgs=msgs, has_more=has_more,
                   oldest=msgs[0].pk if msgs else None, last_id=msgs[-1].pk if msgs else 0,
                   members=[p.user for p in conv.participants.select_related("user__profile")],
                   blocked=s.direct_blocked(conv, me), chat_max=2000)
    return render(request, "messaging/inbox.html", ctx)


@login_required
@require_POST
def start(request, user_id):
    other = get_object_or_404(User, pk=user_id, institution_id=request.user.institution_id, is_active=True)
    if not s.can_message(request.user, other):
        messages.error(request, "You can't message this person. Connect with them first.")
        return redirect("profiles:detail", pk=other.pk)
    conv = s.get_or_create_direct(request.user, other)
    return redirect("messaging:chat", pk=conv.pk)


class GroupForm(forms.Form):
    name = forms.CharField(max_length=80, label="Group name")
    members = forms.ModelMultipleChoiceField(User.objects.none(), widget=forms.CheckboxSelectMultiple, label="Add people")

    def __init__(self, *a, user, **kw):
        super().__init__(*a, **kw)
        self.fields["members"].queryset = s.connections_of(user)

    def clean_members(self):
        m = self.cleaned_data["members"]
        if len(m) < 2:
            raise forms.ValidationError("Pick at least two people for a group (use a direct message for one).")
        if len(m) > 19:
            raise forms.ValidationError("Groups are limited to 20 people.")
        return m


@login_required
def new_group(request):
    form = GroupForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        conv = s.create_group(request.user, form.cleaned_data["name"].strip(), form.cleaned_data["members"])
        return redirect("messaging:chat", pk=conv.pk)
    return render(request, "messaging/new_group.html", {"form": form, "connections": s.connections_of(request.user)})


@login_required
@require_POST
def send(request, pk):
    """HTTP fallback used when the WebSocket is unavailable."""
    conv = _conv(request.user, pk)
    try:
        msg = s.post_message(conv, request.user, request.POST.get("body", ""))
    except ValidationError as e:
        return JsonResponse({"error": " ".join(e.messages)}, status=400)
    except PermissionDenied as e:
        return JsonResponse({"error": str(e) or "Not allowed."}, status=403)
    return JsonResponse({"message": s.serialize(msg)})


@login_required
def poll(request, pk):
    conv = _conv(request.user, pk)
    after = request.GET.get("after", "0")
    after = int(after) if after.isdigit() else 0
    new = list(conv.messages.filter(pk__gt=after).select_related("sender")[:100])
    if new:
        s.mark_read(conv, request.user)
    return JsonResponse({"messages": [s.serialize(m) for m in new]})


@login_required
@require_POST
def read(request, pk):
    s.mark_read(_conv(request.user, pk), request.user)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def leave(request, pk):
    conv = _conv(request.user, pk)
    if conv.kind != "group":
        raise Http404
    CP.objects.filter(conversation=conv, user=request.user).delete()
    if not conv.participants.exists():
        conv.delete()
    messages.info(request, "You left the group.")
    return redirect("messaging:inbox")
