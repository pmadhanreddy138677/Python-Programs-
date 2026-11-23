from apps.core.ratelimit import rate_limit
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.connections.services import blocked_ids
from apps.notifications.services import notify
from .badges import BADGES, badges_for
from .forms import AnswerForm, CommentForm, QuestionForm, ReportForm
from .models import ASK_CATEGORIES, Answer, AnswerComment, AnswerVote, AskReport, Question, QuestionBookmark


def _is_admin(u):
    return u.role == "admin" or u.is_superuser


def _question(user, pk, allow_removed=False):
    q = get_object_or_404(Question.objects.select_related("author__profile", "author__department"), pk=pk, institution_id=user.institution_id)
    if (q.is_removed and not allow_removed) or q.author_id in blocked_ids(user) and q.author_id != user.id:
        raise Http404
    return q


@login_required
def ask_list(request):
    me, g = request.user, request.GET
    q, cat, status, sort, scope = (g.get("q") or "").strip(), g.get("category", ""), g.get("status", ""), g.get("sort", "new"), g.get("scope", "")
    qs = (Question.objects.filter(institution_id=me.institution_id, is_removed=False).exclude(author_id__in=blocked_ids(me))
          .select_related("author__profile", "accepted_answer")
          .annotate(answer_count=Count("answers", filter=Q(answers__is_removed=False), distinct=True),
                    helpful=Count("answers__votes", filter=Q(answers__is_removed=False), distinct=True),
                    i_saved=Exists(QuestionBookmark.objects.filter(question=OuterRef("pk"), user=me))))
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
    if cat in dict(ASK_CATEGORIES):
        qs = qs.filter(category=cat)
    if status == "unanswered":
        qs = qs.filter(answer_count=0)
    elif status == "solved":
        qs = qs.filter(accepted_answer__isnull=False)
    elif status == "open":
        qs = qs.filter(accepted_answer__isnull=True)
    if scope == "mine":
        qs = qs.filter(author=me)
    elif scope == "answered":
        qs = qs.filter(answers__author=me)
    elif scope == "saved":
        qs = qs.filter(i_saved=True)
    qs = qs.order_by("-helpful", "-created_at") if sort == "helpful" else qs.order_by("-created_at")
    page = Paginator(qs, 10).get_page(g.get("page"))
    params = g.copy(); params.pop("page", None)
    return render(request, "ask/list.html", {"page": page, "q": q, "cat": cat, "status": status, "sort": sort, "scope": scope,
                  "categories": ASK_CATEGORIES, "querystring": params.urlencode(), "badge_info": BADGES})


@login_required
@rate_limit("ask_new", 20, 600)
def ask_new(request):
    me = request.user
    if not me.is_approved:
        messages.error(request, "Your account must be approved before you can ask questions.")
        return redirect("ask:list")
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        q = form.save(commit=False)
        q.institution, q.author = me.institution, me
        q.save()
        messages.success(request, "Question posted.")
        return redirect("ask:detail", pk=q.pk)
    return render(request, "ask/form.html", {"form": form})


@login_required
def ask_detail(request, pk):
    me = request.user
    q = _question(me, pk)
    blocked = blocked_ids(me)
    answers = (Answer.objects.filter(question=q, is_removed=False).exclude(author_id__in=blocked).select_related("author__profile", "author__department")
               .annotate(helpful=Count("votes", distinct=True), i_voted=Exists(AnswerVote.objects.filter(answer=OuterRef("pk"), user=me))))
    answers = sorted(answers, key=lambda a: (a.pk != q.accepted_answer_id, -a.helpful, a.created_at))
    comments = {}
    for c in AnswerComment.objects.filter(answer__in=answers).select_related("author__profile"):
        comments.setdefault(c.answer_id, []).append(c)
    top_badge = {}
    for a in answers:
        if a.author_id not in top_badge:
            earned = [b for b in badges_for(a.author) if b["earned"]]
            top_badge[a.author_id] = earned[0] if earned else None
    for a in answers:
        a.comment_list, a.top_badge = comments.get(a.pk, []), top_badge[a.author_id]
    return render(request, "ask/detail.html", {
        "q": q, "answers": answers, "mine": q.author_id == me.id, "i_answered": any(a.author_id == me.id for a in answers),
        "saved": QuestionBookmark.objects.filter(question=q, user=me).exists(), "form": AnswerForm(), "comment_form": CommentForm(),
        "report_form": ReportForm(), "is_admin": _is_admin(me)})


@login_required
@require_POST
def question_delete(request, pk):
    q = _question(request.user, pk)
    if q.author_id != request.user.id and not _is_admin(request.user):
        raise Http404
    q.delete()
    messages.info(request, "Question deleted.")
    return redirect("ask:list")


@login_required
@require_POST
@rate_limit("answer_new", 30, 600)
def answer_new(request, pk):
    me, q = request.user, None
    q = _question(me, pk)
    if not me.is_approved:
        raise Http404
    form = AnswerForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Write a bit more before posting.")
    else:
        try:
            with transaction.atomic():
                a = form.save(commit=False)
                a.question, a.author = q, me
                a.save()
        except IntegrityError:
            messages.info(request, "You've already answered this question.")
        else:
            notify(q.author, "reply", f"{me.full_name} answered your question", q.title, f"/app/ask/{q.pk}/#a{a.pk}", actor=me)
            messages.success(request, "Answer posted. Thank you for helping!")
    return redirect("ask:detail", pk=q.pk)


def _answer(user, pk):
    a = get_object_or_404(Answer.objects.select_related("question", "author"), pk=pk, is_removed=False, question__institution_id=user.institution_id, question__is_removed=False)
    if a.author_id in blocked_ids(user) and a.author_id != user.id:
        raise Http404
    return a


@login_required
@require_POST
def answer_delete(request, pk):
    a = _answer(request.user, pk)
    if a.author_id != request.user.id and not _is_admin(request.user):
        raise Http404
    qid = a.question_id
    a.delete()
    return redirect("ask:detail", pk=qid)


@login_required
@require_POST
def answer_helpful(request, pk):
    a = _answer(request.user, pk)
    if a.author_id == request.user.id:
        raise Http404  # no self-votes
    v, created = AnswerVote.objects.get_or_create(answer=a, user=request.user)
    if not created:
        v.delete()
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"active": created, "count": a.votes.count()})
    return redirect("ask:detail", pk=a.question_id)


@login_required
@require_POST
def answer_accept(request, pk):
    a = _answer(request.user, pk)
    q = a.question
    if q.author_id != request.user.id:
        raise Http404
    if q.accepted_answer_id == a.pk:
        q.accepted_answer = None
    else:
        q.accepted_answer = a
        notify(a.author, "reply", f"{request.user.full_name} accepted your answer", q.title, f"/app/ask/{q.pk}/#a{a.pk}", actor=request.user)
    q.save(update_fields=["accepted_answer"])
    return redirect("ask:detail", pk=q.pk)


@login_required
@require_POST
def comment_new(request, pk):
    a = _answer(request.user, pk)
    form = CommentForm(request.POST)
    if form.is_valid() and form.cleaned_data["body"].strip():
        c = form.save(commit=False)
        c.answer, c.author = a, request.user
        c.save()
        notify(a.author, "reply", f"{request.user.full_name} commented on your answer", c.body[:120], f"/app/ask/{a.question_id}/#a{a.pk}", actor=request.user)
    return redirect("ask:detail", pk=a.question_id)


@login_required
@require_POST
def comment_delete(request, pk):
    c = get_object_or_404(AnswerComment.objects.select_related("answer__question"), pk=pk, answer__question__institution_id=request.user.institution_id)
    if c.author_id != request.user.id and not _is_admin(request.user):
        raise Http404
    qid = c.answer.question_id
    c.delete()
    return redirect("ask:detail", pk=qid)


@login_required
@require_POST
def bookmark(request, pk):
    q = _question(request.user, pk)
    obj, created = QuestionBookmark.objects.get_or_create(question=q, user=request.user)
    if not created:
        obj.delete()
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"active": created, "count": q.bookmarks.count()})
    return redirect("ask:detail", pk=q.pk)


def _report(request, question=None, answer=None):
    form = ReportForm(request.POST)
    target = question or answer
    if target.author_id == request.user.id:
        messages.error(request, "You can't report your own content.")
    elif form.is_valid():
        try:
            with transaction.atomic():
                AskReport.objects.create(reporter=request.user, institution=request.user.institution, question=question, answer=answer, reason=form.cleaned_data["reason"])
            messages.success(request, "Thanks. An administrator will review this.")
        except IntegrityError:
            messages.info(request, "You've already reported this.")
    return redirect("ask:detail", pk=(question or answer.question).pk)


@login_required
@require_POST
def report_question(request, pk):
    return _report(request, question=_question(request.user, pk))


@login_required
@require_POST
def report_answer(request, pk):
    return _report(request, answer=_answer(request.user, pk))


@login_required
def moderation(request):
    if not _is_admin(request.user):
        raise Http404
    reports = AskReport.objects.filter(institution_id=request.user.institution_id, status="open").select_related("reporter", "question__author", "answer__author", "answer__question")
    return render(request, "ask/moderation.html", {"reports": reports})


@login_required
@require_POST
def resolve_report(request, pk, action):
    if not _is_admin(request.user):
        raise Http404
    r = get_object_or_404(AskReport.objects.select_related("question", "answer"), pk=pk, status="open", institution_id=request.user.institution_id)
    if action == "remove":
        t = r.question or r.answer
        t.is_removed = True
        t.save(update_fields=["is_removed"])
        r.status = "resolved"
    elif action == "dismiss":
        r.status = "dismissed"
    else:
        raise Http404
    r.handled_by = request.user
    r.save(update_fields=["status", "handled_by"])
    return redirect("ask:moderation")
