from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FacultyProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_faculty_profile(sender, instance, **kwargs):
    if instance.role == "faculty":
        FacultyProfile.objects.get_or_create(user=instance)
