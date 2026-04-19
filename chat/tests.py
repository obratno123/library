from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, Mock
import json
from datetime import datetime
from django.test import TestCase
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser, User

from chat.consumers import ChatConsumer
from chat.models import Dialog, Message
from datetime import timedelta
from django.utils import timezone
from django.test import SimpleTestCase
from chat.routing import websocket_urlpatterns

class ModelsChatTests(TestCase):
    def test_dialog_str_returns_correct_string(self):
        user1 = User.objects.create_user(
            username="alice_dialog",
            password="testpass123"
        )
        user2 = User.objects.create_user(
            username="bob_dialog",
            password="testpass123"
        )

        dialog = Dialog.objects.create(
            user1=user1,
            user2=user2
        )

        self.assertEqual(str(dialog), "alice_dialog ↔ bob_dialog")

    def test_dialog_get_other_user_returns_user2_for_user1(self):
        user1 = User.objects.create_user(
            username="alice_other_1",
            password="testpass123"
        )
        user2 = User.objects.create_user(
            username="bob_other_1",
            password="testpass123"
        )

        dialog = Dialog.objects.create(
            user1=user1,
            user2=user2
        )

        self.assertEqual(dialog.get_other_user(user1), user2)
        
    def test_dialog_get_other_user_returns_user1_for_user2(self):
        user1 = User.objects.create_user(
            username="alice_other_2",
            password="testpass123"
        )
        user2 = User.objects.create_user(
            username="bob_other_2",
            password="testpass123"
        )

        dialog = Dialog.objects.create(
            user1=user1,
            user2=user2
        )

        self.assertEqual(dialog.get_other_user(user2), user1)
        
    def test_message_str_returns_sender_and_first_30_characters(self):
        user1 = User.objects.create_user(
            username="sender_user",
            password="testpass123"
        )
        user2 = User.objects.create_user(
            username="receiver_user",
            password="testpass123"
        )

        dialog = Dialog.objects.create(
            user1=user1,
            user2=user2
        )

        text = "a" * 50

        message = Message.objects.create(
            dialog=dialog,
            sender=user1,
            text=text
        )

        self.assertEqual(str(message), f"sender_user: {text[:30]}")
        
    def test_message_str_returns_full_text_if_shorter_than_30_characters(self):
        user1 = User.objects.create_user(
            username="short_sender",
            password="testpass123"
        )
        user2 = User.objects.create_user(
            username="short_receiver",
            password="testpass123"
        )

        dialog = Dialog.objects.create(
            user1=user1,
            user2=user2
        )

        message = Message.objects.create(
            dialog=dialog,
            sender=user1,
            text="Привет"
        )

        self.assertEqual(str(message), "short_sender: Привет")
        
        
class ChatRoutingTest(SimpleTestCase):
    def setUp(self):
        self.pattern = websocket_urlpatterns[0]

    def test_chat_websocket_url_resolves(self):
        match = self.pattern.resolve("ws/chat/123/")

        self.assertIsNotNone(match)
        self.assertEqual(match.kwargs["dialog_id"], "123")

    def test_chat_websocket_url_does_not_resolve_without_id(self):
        match = self.pattern.resolve("ws/chat/")

        self.assertIsNone(match)

    def test_chat_websocket_url_does_not_resolve_with_non_numeric_id(self):
        match = self.pattern.resolve("ws/chat/abc/")

        self.assertIsNone(match)

    def test_chat_websocket_url_does_not_resolve_without_trailing_slash(self):
        match = self.pattern.resolve("ws/chat/123")

        self.assertIsNone(match)


class ChatConsumerConnectTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = User(username="client")
        self.dialog = object()

    def build_consumer(self, user, dialog_id="1"):
        consumer = ChatConsumer()
        consumer.scope = {
            "user": user,
            "url_route": {
                "kwargs": {
                    "dialog_id": dialog_id
                }
            }
        }
        consumer.channel_layer = MagicMock()
        consumer.channel_layer.group_add = AsyncMock()
        consumer.channel_name = "test-channel"

        consumer.close = AsyncMock()
        consumer.accept = AsyncMock()
        consumer.get_dialog = AsyncMock()
        consumer.user_has_access = AsyncMock()

        return consumer

    async def test_connect_closes_for_unauthenticated_user(self):
        consumer = self.build_consumer(AnonymousUser())

        await consumer.connect()

        consumer.close.assert_awaited_once()
        consumer.get_dialog.assert_not_awaited()
        consumer.user_has_access.assert_not_awaited()
        consumer.channel_layer.group_add.assert_not_awaited()
        consumer.accept.assert_not_awaited()

    async def test_connect_closes_if_dialog_not_found(self):
        consumer = self.build_consumer(self.user, dialog_id="5")
        consumer.get_dialog.return_value = None

        await consumer.connect()

        self.assertEqual(consumer.dialog_id, "5")
        self.assertEqual(consumer.room_group_name, "user_dialog_5")
        consumer.get_dialog.assert_awaited_once_with("5")
        consumer.close.assert_awaited_once()
        consumer.user_has_access.assert_not_awaited()
        consumer.channel_layer.group_add.assert_not_awaited()
        consumer.accept.assert_not_awaited()

    async def test_connect_closes_if_user_has_no_access(self):
        consumer = self.build_consumer(self.user, dialog_id="7")
        consumer.get_dialog.return_value = self.dialog
        consumer.user_has_access.return_value = False

        await consumer.connect()

        self.assertEqual(consumer.dialog_id, "7")
        self.assertEqual(consumer.room_group_name, "user_dialog_7")
        consumer.get_dialog.assert_awaited_once_with("7")
        consumer.user_has_access.assert_awaited_once_with(self.dialog)
        consumer.close.assert_awaited_once()
        consumer.channel_layer.group_add.assert_not_awaited()
        consumer.accept.assert_not_awaited()

    async def test_connect_accepts_and_adds_user_to_group(self):
        consumer = self.build_consumer(self.user, dialog_id="12")
        consumer.get_dialog.return_value = self.dialog
        consumer.user_has_access.return_value = True

        await consumer.connect()

        self.assertEqual(consumer.dialog_id, "12")
        self.assertEqual(consumer.room_group_name, "user_dialog_12")
        consumer.get_dialog.assert_awaited_once_with("12")
        consumer.user_has_access.assert_awaited_once_with(self.dialog)
        consumer.channel_layer.group_add.assert_awaited_once_with(
            "user_dialog_12",
            "test-channel"
        )
        consumer.accept.assert_awaited_once()
        consumer.close.assert_not_awaited()
       
        
class ChatConsumerDisconnectTest(IsolatedAsyncioTestCase):
    def build_consumer(self):
        consumer = ChatConsumer()
        consumer.channel_layer = MagicMock()
        consumer.channel_layer.group_discard = AsyncMock()
        consumer.channel_name = "test-channel"
        consumer.room_group_name = "user_dialog_15"
        return consumer

    async def test_disconnect_removes_user_from_group(self):
        consumer = self.build_consumer()

        await consumer.disconnect(1000)

        consumer.channel_layer.group_discard.assert_awaited_once_with(
            "user_dialog_15",
            "test-channel"
        )
        

class ChatConsumerReceiveTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = User(username="client")
        self.user.id = 10
        self.dialog = object()

    def build_consumer(self):
        consumer = ChatConsumer()
        consumer.user = self.user
        consumer.dialog_id = "5"
        consumer.room_group_name = "user_dialog_5"

        consumer.channel_layer = MagicMock()
        consumer.channel_layer.group_send = AsyncMock()

        consumer.get_dialog = AsyncMock()
        consumer.user_has_access = AsyncMock()
        consumer.create_message = AsyncMock()

        return consumer

    async def test_receive_does_nothing_if_message_is_empty(self):
        consumer = self.build_consumer()

        await consumer.receive(json.dumps({"message": ""}))

        consumer.get_dialog.assert_not_awaited()
        consumer.user_has_access.assert_not_awaited()
        consumer.create_message.assert_not_awaited()
        consumer.channel_layer.group_send.assert_not_awaited()

    async def test_receive_does_nothing_if_message_contains_only_spaces(self):
        consumer = self.build_consumer()

        await consumer.receive(json.dumps({"message": "   "}))

        consumer.get_dialog.assert_not_awaited()
        consumer.user_has_access.assert_not_awaited()
        consumer.create_message.assert_not_awaited()
        consumer.channel_layer.group_send.assert_not_awaited()

    async def test_receive_uses_empty_string_if_message_key_is_missing(self):
        consumer = self.build_consumer()

        await consumer.receive(json.dumps({}))

        consumer.get_dialog.assert_not_awaited()
        consumer.user_has_access.assert_not_awaited()
        consumer.create_message.assert_not_awaited()
        consumer.channel_layer.group_send.assert_not_awaited()

    async def test_receive_does_nothing_if_dialog_not_found(self):
        consumer = self.build_consumer()
        consumer.get_dialog.return_value = None

        await consumer.receive(json.dumps({"message": "Привет"}))

        consumer.get_dialog.assert_awaited_once_with("5")
        consumer.user_has_access.assert_not_awaited()
        consumer.create_message.assert_not_awaited()
        consumer.channel_layer.group_send.assert_not_awaited()

    async def test_receive_does_nothing_if_user_has_no_access(self):
        consumer = self.build_consumer()
        consumer.get_dialog.return_value = self.dialog
        consumer.user_has_access.return_value = False

        await consumer.receive(json.dumps({"message": "Привет"}))

        consumer.get_dialog.assert_awaited_once_with("5")
        consumer.user_has_access.assert_awaited_once_with(self.dialog)
        consumer.create_message.assert_not_awaited()
        consumer.channel_layer.group_send.assert_not_awaited()

    async def test_receive_creates_message_and_sends_event_to_group(self):
        consumer = self.build_consumer()
        consumer.get_dialog.return_value = self.dialog
        consumer.user_has_access.return_value = True

        message = MagicMock()
        message.text = "Привет"
        message.created_at = datetime(2026, 4, 19, 18, 30)
        consumer.create_message.return_value = message

        await consumer.receive(json.dumps({"message": "  Привет  "}))

        consumer.get_dialog.assert_awaited_once_with("5")
        consumer.user_has_access.assert_awaited_once_with(self.dialog)
        consumer.create_message.assert_awaited_once_with(
            self.dialog,
            self.user,
            "Привет"
        )
        consumer.channel_layer.group_send.assert_awaited_once_with(
            "user_dialog_5",
            {
                "type": "chat_message",
                "message": "Привет",
                "sender_id": 10,
                "sender_username": "client",
                "created_at": "19.04.2026 18:30",
            }
        )
        
        
class ChatConsumerChatMessageTest(IsolatedAsyncioTestCase):
    async def test_chat_message_sends_json_to_websocket(self):
        consumer = ChatConsumer()
        consumer.send = AsyncMock()

        event = {
            "message": "Привет",
            "sender_id": 3,
            "sender_username": "operator",
            "created_at": "19.04.2026 18:45",
        }

        await consumer.chat_message(event)

        consumer.send.assert_awaited_once_with(
            text_data=json.dumps({
                "message": "Привет",
                "sender_id": 3,
                "sender_username": "operator",
                "created_at": "19.04.2026 18:45",
            })
        )
        

class ChatConsumerHelpersTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="other_user",
            password="testpass123"
        )

        self.dialog = Dialog.objects.create(
            user1=self.user1,
            user2=self.user2
        )

        self.consumer = ChatConsumer()

    def test_get_dialog_returns_dialog_if_exists(self):
        result = async_to_sync(self.consumer.get_dialog)(self.dialog.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.dialog.id)
        self.assertEqual(result.user1, self.user1)
        self.assertEqual(result.user2, self.user2)

    def test_get_dialog_returns_none_if_dialog_not_exists(self):
        result = async_to_sync(self.consumer.get_dialog)(999999)

        self.assertIsNone(result)

    def test_user_has_access_returns_true_for_user1(self):
        self.consumer.user = self.user1

        result = async_to_sync(self.consumer.user_has_access)(self.dialog)

        self.assertTrue(result)

    def test_user_has_access_returns_true_for_user2(self):
        self.consumer.user = self.user2

        result = async_to_sync(self.consumer.user_has_access)(self.dialog)

        self.assertTrue(result)

    def test_user_has_access_returns_false_for_other_user(self):
        self.consumer.user = self.other_user

        result = async_to_sync(self.consumer.user_has_access)(self.dialog)

        self.assertFalse(result)

    def test_create_message_creates_message_and_returns_it(self):
        message = async_to_sync(self.consumer.create_message)(
            self.dialog,
            self.user1,
            "Привет"
        )

        self.assertIsInstance(message, Message)
        self.assertEqual(message.dialog, self.dialog)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.text, "Привет")
        self.assertFalse(message.is_read)

        self.assertTrue(
            Message.objects.filter(
                id=message.id,
                dialog=self.dialog,
                sender=self.user1,
                text="Привет"
            ).exists()
        )

    def test_create_message_calls_dialog_save_with_updated_at(self):
        original_save = self.dialog.save
        self.dialog.save = Mock(wraps=original_save)

        async_to_sync(self.consumer.create_message)(
            self.dialog,
            self.user1,
            "Новое сообщение"
        )

        self.dialog.save.assert_called_once_with(update_fields=["updated_at"])
        
    def test_create_message_updates_dialog_updated_at_in_db(self):

        old_time = timezone.now() - timedelta(days=1)

        Dialog.objects.filter(id=self.dialog.id).update(updated_at=old_time)
        self.dialog.refresh_from_db()

        self.assertEqual(self.dialog.updated_at, old_time)

        async_to_sync(self.consumer.create_message)(
            self.dialog,
            self.user1,
            "Проверка updated_at"
        )

        self.dialog.refresh_from_db()

        self.assertGreater(self.dialog.updated_at, old_time)