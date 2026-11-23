from django.contrib import admin
from .models import ModerationAction, Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "community", "reason", "status", "reporter", "created_at")
    list_filter = ("status", "reason")

@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    list_display = ("community", "moderator", "action", "created_at")
