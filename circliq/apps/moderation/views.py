from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.communities.models import Community
from apps.communities.services import can_manage, can_view_content
from apps.discussions.models import Comment, Post
from .models import ModerationAction, Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "details"]
        widgets = {"details": forms.Textarea(attrs={"rows": 3, "maxlength": 500, "placeholder": "Optional: tell moderators what's wrong"})}


def _report(request, post=None, comment=None):
    community = (post or comment.post).community
    if not can_view_content(request.user, community):
        raise Http404
    target = post or comment
    if target.author_id == request.user.id:
        messages.error(request, "You can't report your own content.")
        return redirect("discussions:detail", pk=(post or comment.post).pk)
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        r = form.save(commit=False)
        r.community, r.reporter, r.post, r.comment = community, request.user, post, comment
        if Report.objects.filter(reporter=request.user, post=post, comment=comment).exists():
            messages.info(request, "You've already reported this.")
        else:
            r.save()
            messages.success(request, "Thanks. A moderator will review this report.")
        return redirect("discussions:detail", pk=(post or comment.post).pk)
    return render(request, "moderation/report.html", {"form": form, "target": target, "is_comment": comment is not None})


@login_required
def report_post(request, pk):
    return _report(request, post=get_object_or_404(Post.objects.select_related("community"), pk=pk, is_removed=False))


@login_required
def report_comment(request, pk):
    return _report(request, comment=get_object_or_404(Comment.objects.select_related("post__community"), pk=pk, is_removed=False))


@login_required
def queue(request, pk):
    c = get_object_or_404(Community, pk=pk, institution_id=request.user.institution_id)
    if not can_manage(request.user, c):
        raise Http404
    reports = c.reports.select_related("reporter", "post__author", "comment__author", "comment__post").filter(status="open")
    history = c.moderation_actions.select_related("moderator")[:15]
    return render(request, "moderation/queue.html", {"c": c, "reports": reports, "history": history})


@login_required
@require_POST
def resolve(request, pk, action):
    r = get_object_or_404(Report.objects.select_related("community", "post", "comment"), pk=pk, status="open")
    if r.community.institution_id != request.user.institution_id and not request.user.is_superuser:
        raise Http404
    if not can_manage(request.user, r.community):
        raise Http404
    if action == "remove":
        t = r.post or r.comment
        t.is_removed = True
        t.save(update_fields=["is_removed"])
        r.status, log = "resolved", ("remove_post" if r.post else "remove_comment")
        Report.objects.filter(status="open", post=r.post, comment=r.comment).exclude(pk=r.pk).update(
            status="resolved", handled_by=request.user, handled_at=timezone.now())
    elif action == "dismiss":
        r.status, log = "dismissed", "dismiss_report"
    else:
        raise Http404
    r.handled_by, r.handled_at = request.user, timezone.now()
    r.save(update_fields=["status", "handled_by", "handled_at"])
    ModerationAction.objects.create(community=r.community, moderator=request.user, action=log, report=r)
    messages.success(request, "Report handled.")
    return redirect("moderation:queue", pk=r.community_id)


@login_required
@require_POST
def remove_post(request, pk):
    """Moderators/owners/admins can remove a post directly; it is logged in the audit trail."""
    post = get_object_or_404(Post.objects.select_related("community"), pk=pk, is_removed=False)
    if post.community.institution_id != request.user.institution_id and not request.user.is_superuser:
        raise Http404
    if not can_manage(request.user, post.community):
        raise Http404
    post.is_removed = True
    post.save(update_fields=["is_removed"])
    post.reports.filter(status="open").update(status="resolved", handled_by=request.user, handled_at=timezone.now())
    ModerationAction.objects.create(community=post.community, moderator=request.user, action="remove_post", note=f"post {post.pk}")
    messages.success(request, "Post removed.")
    return redirect("communities:detail", pk=post.community_id)
