import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User

from .models import SupportDialog, SupportMessage


class SupportChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.dialog_id = self.scope["url_route"]["kwargs"]["dialog_id"]

        dialog = await self.get_dialog(self.dialog_id)
        if dialog is None:
            await self.close()
            return

        # Доступ только участникам диалога
        allowed = await self.user_has_access(dialog)
        if not allowed:
            await self.close()
            return

        self.room_group_name = f"support_dialog_{self.dialog_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get("message", "").strip()

        if not message_text:
            return

        dialog = await self.get_dialog(self.dialog_id)
        if dialog is None:
            return

        allowed = await self.user_has_access(dialog)
        if not allowed:
            return

        message = await self.create_message(dialog, self.user, message_text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message_id": message.id,
                "message": message.text,
                "sender_id": self.user.id,
                "sender_username": self.user.username,
                "created_at": message.created_at.strftime("%d.%m.%Y %H:%M"),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message_id": event["message_id"],
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_username": event["sender_username"],
            "created_at": event["created_at"],
        }))

    @sync_to_async
    def get_dialog(self, dialog_id):
        try:
            return SupportDialog.objects.select_related("user", "support_user").get(id=dialog_id)
        except SupportDialog.DoesNotExist:
            return None

    @sync_to_async
    def user_has_access(self, dialog):
        return self.user.id in [dialog.user_id, dialog.support_user_id]

    @sync_to_async
    def create_message(self, dialog, sender, text):
        message = SupportMessage.objects.create(
            dialog=dialog,
            sender=sender,
            text=text
        )
        dialog.save(update_fields=["updated_at"])
        return message