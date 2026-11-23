"""Fill a development database with FICTIONAL people and activity so every screen has something to show.

    python manage.py seed_demo            # 30 students, 4 faculty, 1 admin
    python manage.py seed_demo --students 80

All accounts use @demo.circliq.local addresses and one shared demo password. Never run this against a real campus database.
"""
import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.ask.models import Answer, AnswerVote, Question
from apps.circles.models import Circle, CircleMembership, CircleTask
from apps.communities.models import Community, CommunityMembership
from apps.connections.models import Connection
from apps.discussions.models import Comment, Post, Reaction
from apps.events.models import Event, EventRegistration
from apps.institutions.models import Department, Institution, Program
from apps.messaging import services as chat
from apps.profiles.models import AVAILABILITY, COLLAB_PREFS, Interest, Skill
from apps.projects.models import Project, ProjectMembership, ProjectTask
from apps.study.models import StudyRequest

PASSWORD = "Demo@12345!"
DOMAIN = "demo.circliq.local"
FIRST = ["Aarav", "Diya", "Vihaan", "Anaya", "Reyansh", "Isha", "Kabir", "Meera", "Arjun", "Saanvi", "Rohan", "Tara", "Dev", "Nisha", "Ishaan", "Riya", "Yash", "Kavya", "Aditya", "Pooja"]
LAST = ["Patel", "Shah", "Mehta", "Desai", "Joshi", "Trivedi", "Parmar", "Vyas", "Bhatt", "Solanki", "Gohil", "Jadeja"]
SUBJECTS = ["DBMS", "Python", "Operating Systems", "Maths", "Computer Networks", "Machine Learning", "Statistics", "Java", "Data Structures"]
BIOS = ["Curious about how things work.", "Learning by building small projects.", "Coffee, code and cricket.", "Here to meet people and learn.", "Always up for a hackathon.", "Trying to get better at public speaking."]
POSTS = [("discussion", "", "Anyone else finding the new syllabus a bit packed this semester?"), ("question", "Best way to learn SQL joins?", "I keep mixing up inner and outer joins. Any tips or good practice sets?"),
         ("project", "Looking for a UI designer", "Building a campus lost-and-found app in Django. Need someone who enjoys design."), ("discussion", "", "Weekend cricket at the ground, 7 AM. Who's in?"),
         ("question", "Django vs Flask for a college project?", "Which one is easier to deploy and explain in a viva?"), ("discussion", "", "Sharing my notes on normalization, happy to help anyone preparing.")]
QUESTIONS = [("programming", "How do I debug a recursion error in Python?", "My function keeps hitting the recursion limit and I can't see why."), ("academics", "What's the difference between 3NF and BCNF?", "Both seem similar to me, when does BCNF matter?"),
             ("career", "How should I prepare for my first internship interview?", "Second year, mostly Python and basics of DBMS. Where do I start?"), ("campus", "Where can I find past exam papers?", "Is there an official place or do seniors share them?")]


class Command(BaseCommand):
    help = "Create fictional demo data (development only)."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=30)
        parser.add_argument("--force", action="store_true", help="Allow running with DEBUG off")

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("Refusing to seed demo data while DEBUG is off. Use --force only on a throwaway database.")
        rnd = random.Random(2026)
        inst = Institution.objects.filter(is_active=True).first() or Institution.objects.create(name="Demo University", slug="demo-university")
        depts, progs = list(Department.objects.filter(institution=inst)), list(Program.objects.filter(institution=inst))
        interests, skills = list(Interest.objects.all()), list(Skill.objects.all())

        def mkuser(email, name, role="student", **kw):
            u, created = User.objects.get_or_create(email=email, defaults=dict(full_name=name, institution=inst, role=role, is_email_verified=True, is_approved=True, **kw))
            if created:
                u.set_password(PASSWORD); u.save()
            return u

        students = []
        for i in range(opts["students"]):
            name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
            u = mkuser(f"student{i + 1}@{DOMAIN}", name, department=rnd.choice(depts) if depts else None, program=rnd.choice(progs) if progs else None, academic_year=rnd.randint(1, 4))
            p = u.profile
            p.onboarding_complete, p.bio = True, rnd.choice(BIOS)
            p.goals = rnd.sample(["friends", "study", "projects", "communities", "skills", "campus"], 3)
            p.study_subjects = ", ".join(rnd.sample(SUBJECTS, 2))
            p.availability = [a for a, _ in rnd.sample(AVAILABILITY, 2)]
            p.collab_preferences = [c for c, _ in rnd.sample(COLLAB_PREFS, 2)]
            p.save()
            p.interests.set(rnd.sample(interests, min(4, len(interests)))); p.skills.set(rnd.sample(skills, min(3, len(skills))))
            students.append(u)
        faculty = [mkuser(f"faculty{i + 1}@{DOMAIN}", f"Prof. {rnd.choice(LAST)} {i + 1}", "faculty", department=rnd.choice(depts) if depts else None) for i in range(4)]
        for f in faculty:
            fp = f.faculty_profile
            fp.designation, fp.expertise, fp.research_interests = "Assistant Professor", "Machine Learning, Databases", "Applied ML for education."
            fp.save(); f.profile.onboarding_complete = True; f.profile.save()
        admin = mkuser(f"admin@{DOMAIN}", "Campus Admin", "admin"); admin.profile.onboarding_complete = True; admin.profile.save()

        communities = list(Community.objects.filter(institution=inst))
        for u in students:
            for c in rnd.sample(communities, min(3, len(communities))):
                CommunityMembership.objects.get_or_create(community=c, user=u, defaults={"status": "active"})
        for c in [c for c in communities[:6] if not c.posts.exists()]:
            for kind, title, body in rnd.sample(POSTS, 3):
                author = rnd.choice(students)
                post = Post.objects.create(community=c, author=author, kind=kind, title=title, body=body)
                CommunityMembership.objects.get_or_create(community=c, user=author, defaults={"status": "active"})
                for _ in range(rnd.randint(0, 3)):
                    Comment.objects.create(post=post, author=rnd.choice(students), body=rnd.choice(["Count me in!", "Good point.", "I can help with this.", "Same here."]))
                for u in rnd.sample(students, min(rnd.randint(0, 6), len(students))):
                    Reaction.objects.get_or_create(post=post, user=u)

        for _ in range(len(students) * 2):
            a, b = rnd.sample(students, 2)
            if not Connection.objects.filter(requester=a, receiver=b).exists() and not Connection.objects.filter(requester=b, receiver=a).exists():
                Connection.objects.create(requester=a, receiver=b, status=rnd.choice(["accepted", "accepted", "pending"]))
        accepted = list(Connection.objects.filter(status="accepted")[:6])
        for conn in accepted:
            conv = chat.get_or_create_direct(conn.requester, conn.receiver)
            if not conv.messages.exists():
                chat.post_message(conv, conn.requester, "Hey! Saw we share a few interests. Want to study together?")
                chat.post_message(conv, conn.receiver, "Sure, I'm free on weekday evenings.")

        for i, (name, purpose) in enumerate([("Python Beginners Circle", "Weekly practice sessions for new Python learners"), ("DBMS Exam Prep", "Revise normalization, SQL and transactions together"), ("Weekend Cricket", "Friendly matches every Sunday morning")]):
            owner = students[i]
            c, made = Circle.objects.get_or_create(institution=inst, name=name, defaults=dict(purpose=purpose, created_by=owner, max_members=8, category="study" if i < 2 else "sports"))
            if made:
                CircleMembership.objects.create(circle=c, user=owner, role="owner")
                for m in students[i + 3:i + 6]:
                    CircleMembership.objects.get_or_create(circle=c, user=m)
                CircleTask.objects.create(circle=c, title="Pick a time that works for everyone", created_by=owner, status="doing")
        owner = students[0]
        if not StudyRequest.objects.exists():
            circle = Circle.objects.create(institution=inst, name="DBMS · Joins and keys", purpose="Prepare for the mid-sem", created_by=owner, kind="study", category="study", max_members=4)
            CircleMembership.objects.create(circle=circle, user=owner, role="owner")
            StudyRequest.objects.create(circle=circle, subject="DBMS", topic="Joins and keys", goal="Prepare for the mid-sem", schedule="Weekday evenings", mode="online")

        for title, cat, kind in [("Campus Lost & Found App", "web", "project"), ("Study Planner with AI Suggestions", "ai_ml", "project")]:
            p, made = Project.objects.get_or_create(institution=inst, title=title, defaults=dict(creator=students[1], description="A student-built tool to make campus life easier.", category=cat, team_size=4, technologies="Django, Python", goals="Ship a working demo."))
            if made:
                p.required_skills.set(rnd.sample(skills, min(3, len(skills))))
                ProjectMembership.objects.create(project=p, user=students[1], role="lead")
                ProjectTask.objects.create(project=p, title="Sketch the data model", created_by=students[1])
        if faculty and not Project.objects.filter(kind="research").exists():
            Project.objects.create(institution=inst, creator=faculty[0], title="Research assistant: ML for education", kind="research", category="research", description="Help analyse learning data.", team_size=3)
            ProjectMembership.objects.create(project=Project.objects.get(kind="research"), user=faculty[0], role="lead")

        now = timezone.now()
        for i, (t, cat, v) in enumerate([("Hack Night", "technology", "Lab 2"), ("Cultural Fest Auditions", "arts", "Auditorium"), ("Guest Lecture: Careers in AI", "academics", "Seminar Hall")]):
            e, made = Event.objects.get_or_create(institution=inst, title=t, defaults=dict(organizer=faculty[0] if i == 2 else students[2], description="Fictional demo event.", category=cat, venue=v, start_at=now + timedelta(days=3 + i * 4), is_official=(i == 2)))
            if made:
                for u in rnd.sample(students, min(5, len(students))):
                    EventRegistration.objects.get_or_create(event=e, user=u)

        for cat, title, body in QUESTIONS:
            q, made = Question.objects.get_or_create(institution=inst, title=title, defaults=dict(author=rnd.choice(students), category=cat, body=body))
            if made:
                helper = rnd.choice([s for s in students if s != q.author])
                a = Answer.objects.create(question=q, author=helper, body="Start small: reproduce it with the smallest example, then check the base case and what changes each call.")
                for u in rnd.sample(students, min(4, len(students))):
                    if u != helper:
                        AnswerVote.objects.get_or_create(answer=a, user=u)
        self.stdout.write(self.style.SUCCESS(f"Demo data ready: {len(students)} students, {len(faculty)} faculty, 1 admin on '{inst.name}'."))
        self.stdout.write(f"Log in with student1@{DOMAIN}, faculty1@{DOMAIN} or admin@{DOMAIN}  ·  password: {PASSWORD}")
