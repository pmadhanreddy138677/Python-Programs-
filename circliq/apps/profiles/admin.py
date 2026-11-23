from django.contrib import admin
from .models import Interest, Profile, Skill

admin.site.register(Interest)
admin.site.register(Skill)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_discoverable", "onboarding_complete")
