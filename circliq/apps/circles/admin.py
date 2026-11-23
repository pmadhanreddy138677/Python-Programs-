from django.contrib import admin
from .models import Circle, CircleMembership

@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "kind", "status", "max_members", "created_by")
    list_filter = ("institution", "kind", "status")

admin.site.register(CircleMembership)
