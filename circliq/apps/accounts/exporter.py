"""'Download my data': everything Circliq holds about the signed-in person that is theirs to take. Other people's personal data is deliberately left out."""
from django.utils import timezone


def export_user_data(user):
    from apps.ask.models import Answer, Question
    from apps.circles.models import CircleMembership
    from apps.communities.models import CommunityMembership
    from apps.connections.models import Connection
    from apps.discussions.models import Comment, Post
    from apps.events.models import EventRegistration
    from apps.projects.models import ProjectMembership
    from django.db.models import Q
    p = user.profile
    return {
        "exported_at": timezone.now().isoformat(),
        "account": {"email": user.email, "full_name": user.full_name, "role": user.role, "institution": str(user.institution or ""),
                    "department": str(user.department or ""), "program": str(user.program or ""), "academic_year": user.academic_year,
                    "joined": user.date_joined.isoformat(), "email_verified": user.is_email_verified},
        "profile": {"bio": p.bio, "interests": [i.name for i in p.interests.all()], "skills": [s.name for s in p.skills.all()], "goals": p.goals,
                    "study_subjects": p.subject_list(), "availability": p.availability, "collaboration_preferences": p.collab_preferences,
                    "discoverable": p.is_discoverable, "campus_match_enabled": p.match_enabled},
        "communities": [m.community.name for m in CommunityMembership.objects.filter(user=user, status="active").select_related("community")],
        "circles": [m.circle.name for m in CircleMembership.objects.filter(user=user, status="active").select_related("circle")],
        "projects": [m.project.title for m in ProjectMembership.objects.filter(user=user).select_related("project")],
        "events_registered": [r.event.title for r in EventRegistration.objects.filter(user=user).select_related("event")],
        "posts": [{"community": x.community.name, "kind": x.kind, "title": x.title, "body": x.body, "created": x.created_at.isoformat()}
                  for x in Post.objects.filter(author=user).select_related("community")],
        "comments": [{"body": c.body, "created": c.created_at.isoformat()} for c in Comment.objects.filter(author=user)],
        "questions": [{"category": q.category, "title": q.title, "body": q.body, "created": q.created_at.isoformat()} for q in Question.objects.filter(author=user)],
        "answers": [{"question": a.question.title, "body": a.body, "created": a.created_at.isoformat()} for a in Answer.objects.filter(author=user).select_related("question")],
        "connection_count": Connection.objects.filter(Q(requester=user) | Q(receiver=user), status="accepted").count(),
        "note": "Private messages and other people's details are not included.",
    }
