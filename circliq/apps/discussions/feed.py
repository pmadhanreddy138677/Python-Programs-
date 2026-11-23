from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Value, When

from apps.communities.services import my_active_ids
from apps.connections.services import blocked_ids
from .models import Bookmark, Post, Reaction


def annotate_posts(qs, user):
    return qs.annotate(
        reaction_count=Count("reactions", distinct=True),
        comment_count=Count("comments", filter=Q(comments__is_removed=False), distinct=True),
        i_reacted=Exists(Reaction.objects.filter(post=OuterRef("pk"), user=user)),
        i_saved=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=user)),
    )


def feed_for(user, kind="for_you"):
    """Posts I'm allowed to see: public communities in my institution plus private ones I belong to."""
    mine = my_active_ids(user)
    qs = (Post.objects.filter(community__institution_id=user.institution_id, is_removed=False)
          .filter(Q(community__visibility="public") | Q(community_id__in=mine))
          .exclude(author_id__in=blocked_ids(user))
          .select_related("author__profile", "author__department", "community"))
    if kind == "mine":
        qs = qs.filter(community_id__in=mine)
    elif kind == "questions":
        qs = qs.filter(kind="question")
    elif kind == "projects":
        qs = qs.filter(kind="project")
    qs = annotate_posts(qs, user)
    if kind == "for_you":  # deterministic relevance: my communities first, then newest
        qs = qs.annotate(rank=Case(When(community_id__in=mine, then=Value(1)), default=Value(0), output_field=IntegerField())).order_by("-rank", "-created_at")
    else:
        qs = qs.order_by("-created_at")
    return qs
