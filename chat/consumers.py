import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Dialog, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.dialog_id = self.scope["url_route"]["kwargs"]["dialog_id"]
        self.room_group_name = f"user_dialog_{self.dialog_id}"

        dialog = await self.get_dialog(self.dialog_id)
        if dialog is None:
            await self.close()
            return

        allowed = await self.user_has_access(dialog)
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
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
                "message": message.text,
                "sender_id": self.user.id,
                "sender_username": self.user.username,
                "created_at": message.created_at.strftime("%d.%m.%Y %H:%M"),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_username": event["sender_username"],
            "created_at": event["created_at"],
        }))

    @sync_to_async
    def get_dialog(self, dialog_id):
        try:
            return Dialog.objects.select_related("user1", "user2").get(id=dialog_id)
        except Dialog.DoesNotExist:
            return None

    @sync_to_async
    def user_has_access(self, dialog):
        return self.user.id in [dialog.user1_id, dialog.user2_id]

    @sync_to_async
    def create_message(self, dialog, sender, text):
        message = Message.objects.create(
            dialog=dialog,
            sender=sender,
            text=text
        )
        dialog.save(update_fields=["updated_at"])
        return message