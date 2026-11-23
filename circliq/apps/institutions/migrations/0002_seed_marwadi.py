from django.db import migrations

DEPARTMENTS = ["Computer Science & Engineering", "Information Technology", "Electronics & Communication",
               "Mechanical Engineering", "Civil Engineering", "Management", "Other"]
PROGRAMS = [("B.Tech CSE (AI & ML)", "Computer Science & Engineering", 4),
            ("B.Tech CSE", "Computer Science & Engineering", 4),
            ("B.Tech IT", "Information Technology", 4),
            ("Other program", "Other", 4)]


def seed(apps, schema_editor):
    Institution = apps.get_model("institutions", "Institution")
    Department = apps.get_model("institutions", "Department")
    Program = apps.get_model("institutions", "Program")
    inst, _ = Institution.objects.get_or_create(
        slug="marwadi-university",
        defaults={"name": "Marwadi University", "city": "Rajkot", "state": "Gujarat", "country": "India"},
    )
    depts = {n: Department.objects.get_or_create(institution=inst, name=n)[0] for n in DEPARTMENTS}
    for name, dept, years in PROGRAMS:
        Program.objects.get_or_create(institution=inst, name=name, defaults={"department": depts[dept], "duration_years": years})


class Migration(migrations.Migration):
    dependencies = [("institutions", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
