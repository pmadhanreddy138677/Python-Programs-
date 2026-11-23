from django.db import migrations

# Fictional starter groups so a fresh install isn't empty. They have no owner; manage them in the admin site.
STARTERS = [
    ("Python Learners", "technology", "Questions, tips and projects for everyone learning Python."),
    ("AI & ML Club", "technology", "Artificial Intelligence and Machine Learning: papers, projects and study notes."),
    ("Web Dev Corner", "technology", "HTML, CSS, JavaScript and Django. Show what you're building."),
    ("Gaming Zone", "gaming", "Find squads, talk games and organise friendly tournaments."),
    ("Anime & Manga", "gaming", "Recommendations, discussions and watch-alongs."),
    ("Cricket Circle", "sports", "Weekend matches, scores and everything cricket."),
    ("Photography Club", "arts", "Share your shots, swap tips and plan photo walks."),
    ("Music Jam", "music", "Jam sessions, playlists and finding band members."),
    ("Startup Ideas", "entrepreneurship", "Pitch ideas, find co-founders and learn from each other."),
    ("Exam Prep Hub", "academics", "Study material, doubt-solving and revision tips."),
    ("Campus Talk", "general", "Everything else happening around campus."),
]


def seed(apps, schema_editor):
    Institution = apps.get_model("institutions", "Institution")
    Community = apps.get_model("communities", "Community")
    inst = Institution.objects.filter(slug="marwadi-university").first()
    if inst is None:
        return
    for name, cat, desc in STARTERS:
        Community.objects.get_or_create(institution=inst, name=name, defaults={"category": cat, "description": desc})


class Migration(migrations.Migration):
    dependencies = [("communities", "0001_initial"), ("institutions", "0002_seed_marwadi")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
