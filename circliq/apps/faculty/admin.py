from django.contrib import admin
from .models import Announcement, FacultyProfile, MentorshipRequest

admin.site.register(FacultyProfile)
admin.site.register(MentorshipRequest)
admin.site.register(Announcement)
