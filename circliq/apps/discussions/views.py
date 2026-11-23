from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.communities.services import can_manage, can_view_content, is_active_member
from apps.connections.services import blocked_ids
from apps.notifications.services import notify
from .feed import annotate_posts
from .forms import CommentForm, PostEditForm, PostForm
from .models import Bookmark, Comment, Post, Reaction


def _post_or_404(user, pk, include_removed=False):
    """Visible post only: same institution, community content viewable, not removed, author not blocked."""
    post = get_object_or_404(Post.objects.select_related("community", "author__profile", "author__department"), pk=pk)
    if not can_view_content(user, post.community) or (post.is_removed and not include_removed) or post.author_id in blocked_ids(user):
        raise Http404
    return post


def _back(request, post):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/app/") and not nxt.startswith("//") else post.get_absolute_url() if hasattr(post, "get_absolute_url") else f"/app/posts/{post.pk}/")


@login_required
@require_POST
@rate_limit("post", 30, 600)
def create_post(request):
    form = PostForm(request.POST, request.FILES, user=request.user)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, "Posted!")
        return redirect("discussions:detail", pk=post.pk)
    for field, errs in form.errors.items():
        messages.error(request, f"{field.title()}: {errs[0]}")
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/app/") and not nxt.startswith("//") else "dashboard:home")


@login_required
def post_detail(request, pk):
    me = request.user
    post = _post_or_404(me, pk)
    post = annotate_posts(Post.objects.filter(pk=post.pk).select_related("community", "author__profile", "author__department"), me).get()
    comments = list(post.comments.filter(is_removed=False, parent=None).select_related("author__profile")
                    .prefetch_related("replies__author__profile"))
    for c in comments:
        c.visible_replies = [r for r in c.replies.all() if not r.is_removed]
    return render(request, "discussions/detail.html", {
        "post": post, "comments": comments, "form": CommentForm(), "is_member": is_active_member(me, post.community),
        "manage": can_manage(me, post.community), "mine": post.author_id == me.id})


@login_required
def post_edit(request, pk):
    post = _post_or_404(request.user, pk)
    if post.author_id != request.user.id:
        raise Http404
    form = PostEditForm(request.POST or None, instance=post)
    if request.method == "POST" and form.is_valid():
        p = form.save(commit=False); p.edited_at = timezone.now(); p.save()
        messages.success(request, "Post updated.")
        return redirect("discussions:detail", pk=post.pk)
    return render(request, "discussions/edit.html", {"form": form, "post": post})


@login_required
@require_POST
def post_delete(request, pk):
    post = _post_or_404(request.user, pk)
    if post.author_id != request.user.id:
        raise Http404
    cid = post.community_id
    post.delete()
    messages.info(request, "Post deleted.")
    return redirect("communities:detail", pk=cid)


def _toggle(request, pk, model, count_attr):
    post = _post_or_404(request.user, pk)
    obj, created = model.objects.get_or_create(post=post, user=request.user)
    if not created:
        obj.delete()
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"active": created, "count": getattr(post, count_attr).count()})
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/app/") and not nxt.startswith("//") else f"/app/posts/{post.pk}/")


@login_required
@require_POST
def post_react(request, pk):
    return _toggle(request, pk, Reaction, "reactions")


@login_required
@require_POST
def post_save(request, pk):
    return _toggle(request, pk, Bookmark, "bookmarks")


@login_required
@require_POST
@rate_limit("comment", 60, 600)
def comment_add(request, pk):
    post = _post_or_404(request.user, pk)
    if not is_active_member(request.user, post.community):
        messages.error(request, "Join this community to comment.")
        return redirect("discussions:detail", pk=post.pk)
    form = CommentForm(request.POST)
    parent = None
    if request.POST.get("parent"):
        parent = get_object_or_404(Comment, pk=request.POST["parent"], post=post, is_removed=False, parent=None)  # one reply level
    if form.is_valid() and form.cleaned_data["body"].strip():
        c = form.save(commit=False)
        c.post, c.author, c.parent = post, request.user, parent
        c.save()
        link = f"/app/posts/{post.pk}/#c{c.pk}"
        what = post.title or "your post"
        notify(post.author, "reply", f"{request.user.full_name} commented on {what}", c.body[:120], link, actor=request.user)
        if parent is not None and parent.author_id != post.author_id:
            notify(parent.author, "reply", f"{request.user.full_name} replied to your comment", c.body[:120], link, actor=request.user)
    else:
        messages.error(request, "Comment can't be empty.")
    return redirect("discussions:detail", pk=post.pk)


@login_required
@require_POST
def comment_delete(request, pk):
    c = get_object_or_404(Comment.objects.select_related("post__community"), pk=pk)
    if not can_view_content(request.user, c.post.community) or c.author_id != request.user.id:
        raise Http404
    post_id = c.post_id
    c.delete()
    messages.info(request, "Comment deleted.")
    return redirect("discussions:detail", pk=post_id)


@login_required
@require_POST
def accept_answer(request, pk, cid):
    post = _post_or_404(request.user, pk)
    if post.author_id != request.user.id or post.kind != "question":
        raise Http404
    c = get_object_or_404(Comment, pk=cid, post=post, is_removed=False)
    post.accepted_comment = None if post.accepted_comment_id == c.id else c
    post.save(update_fields=["accepted_comment"])
    return redirect("discussions:detail", pk=post.pk)


@login_required
def saved_posts(request):
    me = request.user
    ids = Bookmark.objects.filter(user=me).values_list("post_id", flat=True)
    from apps.communities.services import my_active_ids
    from django.db.models import Q
    qs = (Post.objects.filter(pk__in=ids, is_removed=False, community__institution_id=me.institution_id)
          .filter(Q(community__visibility="public") | Q(community_id__in=my_active_ids(me)))
          .exclude(author_id__in=blocked_ids(me)).select_related("author__profile", "author__department", "community"))
    page = Paginator(annotate_posts(qs, me).order_by("-created_at"), 10).get_page(request.GET.get("page"))
    return render(request, "discussions/saved.html", {"page": page})
