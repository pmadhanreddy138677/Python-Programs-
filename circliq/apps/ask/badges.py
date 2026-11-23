"""Contribution badges. Defined rules, computed from real activity; recognition within Circliq only (not a university certificate)."""
from apps.discussions.models import Post
from apps.projects.models import ProjectMembership
from .models import Answer, AnswerVote, Question

BADGES = [
    {"key": "helpful_peer", "name": "Helpful Peer", "target": 5, "rule": "Receive 5 'helpful' votes on your answers", "icon": "heart", "tile": "t-violet"},
    {"key": "community_contributor", "name": "Community Contributor", "target": 10, "rule": "Write 10 community posts or answers", "icon": "chat", "tile": "t-indigo"},
    {"key": "study_mentor", "name": "Study Mentor", "target": 3, "rule": "Have 3 of your answers accepted by other students", "icon": "book", "tile": "t-cyan"},
    {"key": "project_collaborator", "name": "Project Collaborator", "target": 2, "rule": "Join 2 projects", "icon": "rocket", "tile": "t-amber"},
]


def counts(user):
    return {
        "helpful_peer": AnswerVote.objects.filter(answer__author=user, answer__is_removed=False).exclude(user=user).count(),
        "community_contributor": Answer.objects.filter(author=user, is_removed=False).count() + Post.objects.filter(author=user, is_removed=False).count(),
        "study_mentor": Question.objects.filter(accepted_answer__author=user, is_removed=False).exclude(author=user).count(),
        "project_collaborator": ProjectMembership.objects.filter(user=user).count(),
    }


def badges_for(user):
    c = counts(user)
    out = []
    for b in BADGES:
        v = c[b["key"]]
        out.append({**b, "value": v, "earned": v >= b["target"], "pct": min(100, int(100 * v / b["target"]))})
    return out
