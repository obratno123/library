from django.test import TestCase
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
import json
from datetime import datetime
from datetime import timedelta
from django.utils import timezone

from django.contrib.auth.models import AnonymousUser, User
from asgiref.sync import async_to_sync
from unittest.mock import Mock
from support_chat.consumers import SupportChatConsumer
from support_chat.models import SupportDialog, SupportMessage


class SupportChatConsumerConnectTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = User(username="client")
        self.dialog = object()

    def build_consumer(self, user, dialog_id="1"):
        consumer = SupportChatConsumer()
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
        self.assertEqual(consumer.room_group_name, "support_dialog_12")

        consumer.get_dialog.assert_awaited_once_with("12")
        consumer.user_has_access.assert_awaited_once_with(self.dialog)
        consumer.channel_layer.group_add.assert_awaited_once_with(
            "support_dialog_12",
            "test-channel"
        )
        consumer.accept.assert_awaited_once()
        consumer.close.assert_not_awaited()
        

class SupportChatConsumerDisconnectTest(IsolatedAsyncioTestCase):
    def build_consumer(self):
        consumer = SupportChatConsumer()
        consumer.channel_layer = MagicMock()
        consumer.channel_layer.group_discard = AsyncMock()
        consumer.channel_name = "test-channel"
        return consumer

    async def test_disconnect_removes_from_group_if_room_group_name_exists(self):
        consumer = self.build_consumer()
        consumer.room_group_name = "support_dialog_15"

        await consumer.disconnect(1000)

        consumer.channel_layer.group_discard.assert_awaited_once_with(
            "support_dialog_15",
            "test-channel"
        )

    async def test_disconnect_does_nothing_if_room_group_name_not_exists(self):
        consumer = self.build_consumer()

        await consumer.disconnect(1000)

        consumer.channel_layer.group_discard.assert_not_awaited()
        
        
class SupportChatConsumerReceiveTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = User(username="client")
        self.user.id = 10
        self.dialog = object()

    def build_consumer(self):
        consumer = SupportChatConsumer()
        consumer.user = self.user
        consumer.dialog_id = "5"
        consumer.room_group_name = "support_dialog_5"

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
        message.id = 101
        message.text = "Привет"
        message.created_at = datetime(2026, 4, 18, 14, 30)
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
            "support_dialog_5",
            {
                "type": "chat_message",
                "message_id": 101,
                "message": "Привет",
                "sender_id": 10,
                "sender_username": "client",
                "created_at": "18.04.2026 14:30",
            }
        )

    async def test_receive_uses_default_empty_string_if_message_key_missing(self):
        consumer = self.build_consumer()

        await consumer.receive(json.dumps({}))

        consumer.get_dialog.assert_not_awaited()
        consumer.user_has_access.assert_not_awaited()
        consumer.create_message.assert_not_awaited()
        consumer.channel_layer.group_send.assert_not_awaited()
        
    async def test_receive_raises_error_on_invalid_json(self):
        consumer = self.build_consumer()

        with self.assertRaises(json.JSONDecodeError):
            await consumer.receive("not json")
        
        
class SupportChatConsumerChatMessageTest(IsolatedAsyncioTestCase):
    async def test_chat_message_sends_json_to_websocket(self):
        consumer = SupportChatConsumer()
        consumer.send = AsyncMock()

        event = {
            "message_id": 15,
            "message": "Привет",
            "sender_id": 3,
            "sender_username": "operator",
            "created_at": "18.04.2026 15:20",
        }

        await consumer.chat_message(event)

        consumer.send.assert_awaited_once_with(
            text_data=json.dumps({
                "message_id": 15,
                "message": "Привет",
                "sender_id": 3,
                "sender_username": "operator",
                "created_at": "18.04.2026 15:20",
            })
        )
        

class SupportChatConsumerHelpersTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self.support_user = User.objects.create_user(
            username="operator",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="testpass123"
        )

        self.dialog = SupportDialog.objects.create(
            user=self.client_user,
            support_user=self.support_user
        )

        self.consumer = SupportChatConsumer()

    def test_get_dialog_returns_dialog_if_exists(self):
        result = async_to_sync(self.consumer.get_dialog)(self.dialog.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.dialog.id)
        self.assertEqual(result.user, self.client_user)
        self.assertEqual(result.support_user, self.support_user)

    def test_get_dialog_returns_none_if_dialog_not_exists(self):
        result = async_to_sync(self.consumer.get_dialog)(999999)

        self.assertIsNone(result)

    def test_user_has_access_returns_true_for_dialog_user(self):
        self.consumer.user = self.client_user

        result = async_to_sync(self.consumer.user_has_access)(self.dialog)

        self.assertTrue(result)

    def test_user_has_access_returns_true_for_support_user(self):
        self.consumer.user = self.support_user

        result = async_to_sync(self.consumer.user_has_access)(self.dialog)

        self.assertTrue(result)

    def test_user_has_access_returns_false_for_other_user(self):
        self.consumer.user = self.other_user

        result = async_to_sync(self.consumer.user_has_access)(self.dialog)

        self.assertFalse(result)

    def test_create_message_creates_message_and_returns_it(self):
        message = async_to_sync(self.consumer.create_message)(
            self.dialog,
            self.client_user,
            "Привет, нужна помощь"
        )

        self.assertIsInstance(message, SupportMessage)
        self.assertEqual(message.dialog, self.dialog)
        self.assertEqual(message.sender, self.client_user)
        self.assertEqual(message.text, "Привет, нужна помощь")
        self.assertFalse(message.is_read)

        self.assertTrue(
            SupportMessage.objects.filter(
                id=message.id,
                dialog=self.dialog,
                sender=self.client_user,
                text="Привет, нужна помощь"
            ).exists()
        )

    def test_create_message_calls_dialog_save_with_updated_at(self):
        original_save = self.dialog.save
        self.dialog.save = Mock(wraps=original_save)

        async_to_sync(self.consumer.create_message)(
            self.dialog,
            self.client_user,
            "Новое сообщение"
        )

        self.dialog.save.assert_called_once_with(update_fields=["updated_at"])
        
    def test_create_message_updates_dialog_updated_at_in_db(self):
        old_time = timezone.now() - timedelta(days=1)

        SupportDialog.objects.filter(id=self.dialog.id).update(updated_at=old_time)
        self.dialog.refresh_from_db()

        self.assertEqual(self.dialog.updated_at, old_time)

        async_to_sync(self.consumer.create_message)(
            self.dialog,
            self.client_user,
            "Проверка updated_at"
        )

        self.dialog.refresh_from_db()

        self.assertGreater(self.dialog.updated_at, old_time)