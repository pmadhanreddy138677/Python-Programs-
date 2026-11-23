from django.contrib import admin
from .models import Project, ProjectApplication, ProjectMembership

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "institution", "kind", "status", "creator")
    list_filter = ("institution", "kind", "status")

admin.site.register(ProjectMembership)
admin.site.register(ProjectApplication)
