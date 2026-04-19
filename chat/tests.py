from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import json
from datetime import datetime
from django.test import RequestFactory, TestCase
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser, User
from django.urls import reverse

from chat.consumers import ChatConsumer
from chat.models import Dialog, Message
from datetime import timedelta
from django.utils import timezone
from django.test import SimpleTestCase
from chat.routing import websocket_urlpatterns
from chat.views import dialog_list

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


class DialogListViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="main_user",
            password="testpass123"
        )
        self.other_user_1 = User.objects.create_user(
            username="alice",
            password="testpass123"
        )
        self.other_user_2 = User.objects.create_user(
            username="bob",
            password="testpass123"
        )
        self.other_user_3 = User.objects.create_user(
            username="charlie",
            password="testpass123"
        )
        self.url = reverse("chat:dialog_list")

    def test_dialog_list_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_dialog_list_post_method_not_allowed(self):
        self.client.login(username="main_user", password="testpass123")

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    @patch("chat.views.render")
    def test_dialog_list_shows_only_user_dialogs_with_messages(self, mock_render):
        dialog_with_alice = Dialog.objects.create(
            user1=self.user,
            user2=self.other_user_1
        )
        dialog_with_bob = Dialog.objects.create(
            user1=self.other_user_2,
            user2=self.user
        )
        dialog_without_messages = Dialog.objects.create(
            user1=self.user,
            user2=self.other_user_3
        )
        foreign_dialog = Dialog.objects.create(
            user1=self.other_user_1,
            user2=self.other_user_2
        )

        Message.objects.create(
            dialog=dialog_with_alice,
            sender=self.user,
            text="hello alice"
        )
        Message.objects.create(
            dialog=dialog_with_bob,
            sender=self.other_user_2,
            text="hello main"
        )
        Message.objects.create(
            dialog=foreign_dialog,
            sender=self.other_user_1,
            text="foreign"
        )

        request = self.factory.get(self.url)
        request.user = self.user

        dialog_list(request)

        _, template_name, context = mock_render.call_args[0]

        self.assertEqual(template_name, "dialog_list.html")

        dialog_data = context["dialog_data"]
        dialogs = [item["dialog"] for item in dialog_data]
        other_users = [item["other_user"] for item in dialog_data]

        self.assertIn(dialog_with_alice, dialogs)
        self.assertIn(dialog_with_bob, dialogs)
        self.assertNotIn(dialog_without_messages, dialogs)
        self.assertNotIn(foreign_dialog, dialogs)

        self.assertIn(self.other_user_1, other_users)
        self.assertIn(self.other_user_2, other_users)

    @patch("chat.views.render")
    def test_dialog_list_orders_dialogs_by_updated_at_desc(self, mock_render):
        older_dialog = Dialog.objects.create(
            user1=self.user,
            user2=self.other_user_1
        )
        newer_dialog = Dialog.objects.create(
            user1=self.user,
            user2=self.other_user_2
        )

        Message.objects.create(dialog=older_dialog, sender=self.user, text="old")
        Message.objects.create(dialog=newer_dialog, sender=self.user, text="new")

        now = timezone.now()
        Dialog.objects.filter(id=older_dialog.id).update(
            updated_at=now - timedelta(hours=1)
        )
        Dialog.objects.filter(id=newer_dialog.id).update(
            updated_at=now
        )

        request = self.factory.get(self.url)
        request.user = self.user

        dialog_list(request)

        _, _, context = mock_render.call_args[0]
        dialogs = [item["dialog"] for item in context["dialog_data"]]

        self.assertEqual(dialogs[0].id, newer_dialog.id)
        self.assertEqual(dialogs[1].id, older_dialog.id)

    @patch("chat.views.render")
    def test_dialog_list_filters_users_by_query(self, mock_render):
        request = self.factory.get(self.url, {"q": "ali"})
        request.user = self.user

        dialog_list(request)

        _, _, context = mock_render.call_args[0]
        users = list(context["users"])

        self.assertIn(self.other_user_1, users)
        self.assertNotIn(self.other_user_2, users)
        self.assertNotIn(self.user, users)
        self.assertEqual(context["query"], "ali")


class StartDialogViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="main_user",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="alice",
            password="testpass123"
        )
        self.url = reverse("chat:start_dialog", kwargs={"user_id": self.other_user.id})

    def test_start_dialog_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_start_dialog_post_method_not_allowed(self):
        self.client.login(username="main_user", password="testpass123")

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_start_dialog_redirects_to_dialog_list_if_user_tries_to_start_with_self(self):
        self.client.login(username="main_user", password="testpass123")
        url = reverse("chat:start_dialog", kwargs={"user_id": self.user.id})

        response = self.client.get(url)

        self.assertRedirects(
            response,
            reverse("chat:dialog_list"),
            fetch_redirect_response=False
        )
        self.assertEqual(Dialog.objects.count(), 0)

    def test_start_dialog_creates_dialog_if_not_exists(self):
        self.client.login(username="main_user", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(Dialog.objects.count(), 1)
        dialog = Dialog.objects.get()

        self.assertEqual(dialog.user1, self.user)
        self.assertEqual(dialog.user2, self.other_user)
        self.assertRedirects(
            response,
            reverse("chat:dialog_detail", kwargs={"dialog_id": dialog.id}),
            fetch_redirect_response=False
        )

    def test_start_dialog_uses_existing_dialog_if_exists(self):
        dialog = Dialog.objects.create(
            user1=self.other_user,
            user2=self.user
        )

        self.client.login(username="main_user", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(Dialog.objects.count(), 1)
        self.assertRedirects(
            response,
            reverse("chat:dialog_detail", kwargs={"dialog_id": dialog.id}),
            fetch_redirect_response=False
        )


class DialogDetailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="main_user",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="alice",
            password="testpass123"
        )
        self.third_user = User.objects.create_user(
            username="charlie",
            password="testpass123"
        )
        self.dialog = Dialog.objects.create(
            user1=self.user,
            user2=self.other_user
        )
        self.url = reverse("chat:dialog_detail", kwargs={"dialog_id": self.dialog.id})

    def test_dialog_detail_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_dialog_detail_post_method_not_allowed(self):
        self.client.login(username="main_user", password="testpass123")

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    def test_dialog_detail_redirects_if_user_has_no_access(self):
        self.client.login(username="charlie", password="testpass123")

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("chat:dialog_list"),
            fetch_redirect_response=False
        )

    def test_dialog_detail_returns_404_if_dialog_not_found(self):
        self.client.login(username="main_user", password="testpass123")

        response = self.client.get(
            reverse("chat:dialog_detail", kwargs={"dialog_id": 999999})
        )

        self.assertEqual(response.status_code, 404)

    def test_dialog_detail_marks_only_other_users_unread_messages_as_read(self):
        unread_from_other = Message.objects.create(
            dialog=self.dialog,
            sender=self.other_user,
            text="hello",
            is_read=False
        )
        unread_from_self = Message.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text="my message",
            is_read=False
        )
        already_read = Message.objects.create(
            dialog=self.dialog,
            sender=self.other_user,
            text="already read",
            is_read=True
        )

        self.client.login(username="main_user", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        unread_from_other.refresh_from_db()
        unread_from_self.refresh_from_db()
        already_read.refresh_from_db()

        self.assertTrue(unread_from_other.is_read)
        self.assertFalse(unread_from_self.is_read)
        self.assertTrue(already_read.is_read)

    def test_dialog_detail_renders_context_with_other_user_and_messages(self):
        message = Message.objects.create(
            dialog=self.dialog,
            sender=self.other_user,
            text="hello"
        )

        self.client.login(username="main_user", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dialog_detail.html")
        self.assertEqual(response.context["dialog"], self.dialog)
        self.assertEqual(response.context["other_user"], self.other_user)
        self.assertIn(message, response.context["messages"])