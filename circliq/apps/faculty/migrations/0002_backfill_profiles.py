from django.conf import settings
from django.db import migrations


def forward(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    FP = apps.get_model("faculty", "FacultyProfile")
    for u in User.objects.filter(role="faculty", faculty_profile__isnull=True):
        FP.objects.create(user=u)


class Migration(migrations.Migration):
    dependencies = [("faculty", "0001_initial"), ("accounts", "0001_initial")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
