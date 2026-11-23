from django.contrib import admin
from .models import Conversation

# Message bodies are intentionally NOT registered here: admins don't browse private messages by default.
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "name", "institution", "created_at")
