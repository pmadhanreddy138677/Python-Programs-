from django.contrib import admin
from .models import Comment, Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "community", "author", "kind", "created_at", "is_removed")
    list_filter = ("kind", "is_removed")

admin.site.register(Comment)
