from django.contrib import admin
from .models import Department, Institution, Program

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "is_active")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "institution")
    list_filter = ("institution",)

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "institution")
    list_filter = ("institution",)
