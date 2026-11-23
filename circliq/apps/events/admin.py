from django.contrib import admin
from .models import Event, EventRegistration

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "institution", "start_at", "is_official", "organizer")
    list_filter = ("institution", "is_official", "category")

admin.site.register(EventRegistration)
