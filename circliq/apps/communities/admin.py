from django.contrib import admin
from .models import Community, CommunityMembership


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "category", "visibility", "is_official", "created_by")
    list_filter = ("institution", "category", "visibility", "is_official")
    search_fields = ("name",)
    actions = ["mark_official", "unmark_official"]

    @admin.action(description="Mark as official")
    def mark_official(self, request, qs):
        qs.update(is_official=True)

    @admin.action(description="Remove official badge")
    def unmark_official(self, request, qs):
        qs.update(is_official=False)


@admin.register(CommunityMembership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "community", "role", "status")
    list_filter = ("role", "status")
