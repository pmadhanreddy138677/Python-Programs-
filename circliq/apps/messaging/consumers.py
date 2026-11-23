from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import PermissionDenied, ValidationError

from . import services
from .models import Conversation


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.conv_id = int(self.scope["url_route"]["kwargs"]["conv_id"])
        self.conv = await self._authorize(user)
        if self.conv is None:  # not a participant, other campus, or doesn't exist: all look the same
            await self.close(code=4403)
            return
        self.user = user
        self.group = f"chat_{self.conv_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    @database_sync_to_async
    def _authorize(self, user):
        conv = Conversation.objects.filter(pk=self.conv_id, institution_id=user.institution_id).first()
        if conv and services.participant(user, conv):
            return conv
        return None

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")
        if kind == "message":
            try:
                await database_sync_to_async(services.post_message)(self.conv, self.user, content.get("body", ""))
            except ValidationError as e:
                await self.send_json({"type": "error", "message": " ".join(e.messages)})
            except PermissionDenied as e:
                await self.send_json({"type": "error", "message": str(e) or "Not allowed."})
        elif kind == "typing":
            await self.channel_layer.group_send(self.group, {"type": "chat.typing", "user_id": self.user.pk, "name": self.user.first_name})
        elif kind == "read":
            await database_sync_to_async(services.mark_read)(self.conv, self.user)

    async def chat_message(self, event):
        await self.send_json({"type": "message", **{"message": event["message"]}})

    async def chat_typing(self, event):
        if event["user_id"] != self.user.pk:
            await self.send_json({"type": "typing", "name": event["name"]})
