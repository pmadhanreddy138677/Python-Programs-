from django.conf import settings
from django.db import migrations

INTERESTS = {
    "Technology": ["Python", "Artificial Intelligence", "Machine Learning", "Web Development", "Cybersecurity", "Robotics", "Data Science"],
    "Creative": ["Photography", "Design", "Music", "Video Editing", "Writing", "Art"],
    "Lifestyle": ["Gaming", "Anime", "Reading", "Travel", "Movies", "Fitness"],
    "Sports": ["Cricket", "Football", "Badminton", "Basketball"],
    "Career": ["Entrepreneurship", "Public Speaking", "Finance"],
}
SKILLS = ["Python", "Java", "C/C++", "JavaScript", "HTML & CSS", "Django", "SQL", "Git", "UI/UX Design",
          "Machine Learning", "Data Analysis", "Video Editing", "Writing", "Public Speaking"]


def forward(apps, schema_editor):
    Interest = apps.get_model("profiles", "Interest")
    Skill = apps.get_model("profiles", "Skill")
    Profile = apps.get_model("profiles", "Profile")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    for cat, names in INTERESTS.items():
        for n in names:
            Interest.objects.get_or_create(name=n, defaults={"category": cat})
    for n in SKILLS:
        Skill.objects.get_or_create(name=n)
    for u in User.objects.filter(profile__isnull=True):
        Profile.objects.create(user=u, onboarding_complete=(u.role == "admin"))


class Migration(migrations.Migration):
    dependencies = [("profiles", "0001_initial"), ("accounts", "0001_initial")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
