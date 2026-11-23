from django.apps import AppConfig

class FacultyConfig(AppConfig):
    name = "apps.faculty"

    def ready(self):
        from . import signals  # noqa: F401
