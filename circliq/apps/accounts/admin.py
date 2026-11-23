from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "institution", "is_email_verified", "is_approved")
    list_filter = ("role", "is_approved", "is_email_verified", "institution")
    search_fields = ("email", "full_name")
    actions = ["approve_faculty"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "role", "institution", "department", "program", "academic_year")}),
        ("Status", {"fields": ("is_active", "is_email_verified", "is_approved", "is_restricted", "restriction_reason", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),)

    @admin.action(description="Approve selected faculty accounts")
    def approve_faculty(self, request, queryset):
        queryset.filter(role=User.Role.FACULTY).update(is_approved=True)
