from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from support_chat.models import SupportDialog, SupportMessage
from support_chat.views import is_support, choose_support_user
from users.models import Profile, Role


class SupportDialogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self.support_user = User.objects.create_user(
            username="operator",
            password="testpass123"
        )

    def test_create_support_dialog(self):
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

        self.assertEqual(dialog.user, self.user)
        self.assertEqual(dialog.support_user, self.support_user)
        self.assertIsNotNone(dialog.created_at)
        self.assertIsNotNone(dialog.updated_at)

    def test_support_dialog_str(self):
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

        self.assertEqual(str(dialog), "client -> operator")

    def test_support_dialog_verbose_names(self):
        self.assertEqual(SupportDialog._meta.verbose_name, "Диалог с поддержкой")
        self.assertEqual(
            SupportDialog._meta.verbose_name_plural,
            "Диалоги с поддержкой"
        )

    def test_support_dialog_related_names(self):
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

        self.assertIn(dialog, self.user.support_dialogs.all())
        self.assertIn(dialog, self.support_user.handled_support_dialogs.all())

    def test_support_dialog_unique_constraint(self):
        SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SupportDialog.objects.create(
                    user=self.user,
                    support_user=self.support_user
                )

    def test_support_dialog_deleted_when_user_deleted(self):
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

        self.user.delete()

        self.assertFalse(
            SupportDialog.objects.filter(id=dialog.id).exists()
        )

    def test_support_dialog_deleted_when_support_user_deleted(self):
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

        self.support_user.delete()

        self.assertFalse(
            SupportDialog.objects.filter(id=dialog.id).exists()
        )


class SupportMessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self.support_user = User.objects.create_user(
            username="operator",
            password="testpass123"
        )
        self.dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

    def test_create_support_message(self):
        message = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text="Привет, нужна помощь"
        )

        self.assertEqual(message.dialog, self.dialog)
        self.assertEqual(message.sender, self.user)
        self.assertEqual(message.text, "Привет, нужна помощь")
        self.assertFalse(message.is_read)
        self.assertIsNotNone(message.created_at)

    def test_support_message_str(self):
        text = "a" * 50
        message = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text=text
        )

        self.assertEqual(str(message), f"client: {text[:30]}")

    def test_support_message_verbose_names(self):
        self.assertEqual(SupportMessage._meta.verbose_name, "Сообщение")
        self.assertEqual(
            SupportMessage._meta.verbose_name_plural,
            "Сообщения"
        )

    def test_support_message_default_is_read_false(self):
        message = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text="Новое сообщение"
        )

        self.assertFalse(message.is_read)

    def test_support_message_related_names(self):
        message = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text="Сообщение"
        )

        self.assertIn(message, self.dialog.messages.all())
        self.assertIn(message, self.user.chat_support_messages.all())

    def test_support_message_ordering_by_created_at(self):
        message1 = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text="Первое сообщение"
        )
        message2 = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.support_user,
            text="Второе сообщение"
        )

        later_time = timezone.now()
        earlier_time = later_time - timedelta(hours=1)

        SupportMessage.objects.filter(id=message1.id).update(created_at=later_time)
        SupportMessage.objects.filter(id=message2.id).update(created_at=earlier_time)

        ordered_messages = list(self.dialog.messages.all())

        self.assertEqual(ordered_messages[0].id, message2.id)
        self.assertEqual(ordered_messages[1].id, message1.id)

    def test_support_message_deleted_when_dialog_deleted(self):
        message = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text="Сообщение"
        )

        self.dialog.delete()

        self.assertFalse(
            SupportMessage.objects.filter(id=message.id).exists()
        )

    def test_support_message_deleted_when_sender_deleted(self):
        message = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.user,
            text="Сообщение"
        )

        self.user.delete()

        self.assertFalse(
            SupportMessage.objects.filter(id=message.id).exists()
        )


class IsSupportFunctionTest(TestCase):
    def setUp(self):
        self.support_role = Role.objects.create(name="support")
        self.user_role = Role.objects.create(name="user")

        self.support_user = User.objects.create_user(
            username="support1",
            password="testpass123"
        )
        self.regular_user = User.objects.create_user(
            username="user1",
            password="testpass123"
        )
        self.user_without_profile = User.objects.create_user(
            username="noprof",
            password="testpass123"
        )

        Profile.objects.create(
            user=self.support_user,
            role=self.support_role
        )
        Profile.objects.create(
            user=self.regular_user,
            role=self.user_role
        )

    def test_is_support_returns_true_for_support_user(self):
        self.assertTrue(is_support(self.support_user))

    def test_is_support_returns_false_for_regular_user(self):
        self.assertFalse(is_support(self.regular_user))

    def test_is_support_returns_false_for_user_without_profile(self):
        self.assertFalse(is_support(self.user_without_profile))

    def test_is_support_returns_false_for_user_with_profile_but_without_role(self):
        user = User.objects.create_user(
            username="without_role",
            password="testpass123"
        )
        Profile.objects.create(user=user, role=None)

        self.assertFalse(is_support(user))


class ChooseSupportUserFunctionTest(TestCase):
    def setUp(self):
        self.support_role = Role.objects.create(name="support")
        self.user_role = Role.objects.create(name="user")

        self.support_user_1 = User.objects.create_user(
            username="support1",
            password="testpass123"
        )
        self.support_user_2 = User.objects.create_user(
            username="support2",
            password="testpass123"
        )
        self.regular_user = User.objects.create_user(
            username="user1",
            password="testpass123"
        )
        Profile.objects.create(
            user=self.support_user_1,
            role=self.support_role
        )
        Profile.objects.create(
            user=self.support_user_2,
            role=self.support_role
        )
        Profile.objects.create(
            user=self.regular_user,
            role=self.user_role
        )

    @patch("support_chat.views.random.choice")
    def test_choose_support_user_returns_random_support_user(self, mock_choice):
        mock_choice.return_value = self.support_user_1

        result = choose_support_user()

        self.assertEqual(result, self.support_user_1)
        mock_choice.assert_called_once()
        called_users = mock_choice.call_args[0][0]
        self.assertIn(self.support_user_1, called_users)
        self.assertIn(self.support_user_2, called_users)
        self.assertNotIn(self.regular_user, called_users)

    def test_choose_support_user_raises_error_if_no_support_users(self):
        Profile.objects.filter(
            user__in=[self.support_user_1, self.support_user_2]
        ).delete()

        with self.assertRaises(ValueError) as context:
            choose_support_user()

        self.assertEqual(
            str(context.exception),
            "Нет пользователей с ролью support"
        )
        
        
class ChatDialogViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self.support_user = User.objects.create_user(
            username="operator",
            password="testpass123"
        )
        self.url = reverse("support_chat:chat_dialog")

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_post_method_not_allowed(self):
        self.client.login(username="client", password="testpass123")

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    @patch("support_chat.views.is_support")
    def test_support_user_is_redirected_to_support_dialogs_list(self, mock_is_support):
        mock_is_support.return_value = True
        self.client.login(username="client", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("support_chat:support_dialogs_list")
        )

    @patch("support_chat.views.is_support")
    @patch("support_chat.views.choose_support_user")
    def test_creates_dialog_if_not_exists(self, mock_choose_support_user, mock_is_support):
        mock_is_support.return_value = False
        mock_choose_support_user.return_value = self.support_user
        self.client.login(username="client", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SupportDialog.objects.count(), 1)

        dialog = SupportDialog.objects.first()
        self.assertEqual(dialog.user, self.user)
        self.assertEqual(dialog.support_user, self.support_user)

        self.assertEqual(response.context["dialog"], dialog)
        self.assertEqual(response.context["support_user"], self.support_user)
        self.assertQuerySetEqual(
            response.context["messages"],
            dialog.messages.select_related("sender"),
            transform=lambda x: x
        )

        mock_choose_support_user.assert_called_once()

    @patch("support_chat.views.is_support")
    @patch("support_chat.views.choose_support_user")
    def test_uses_existing_dialog_and_does_not_create_new_one(
        self,
        mock_choose_support_user,
        mock_is_support
    ):
        mock_is_support.return_value = False
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )
        self.client.login(username="client", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SupportDialog.objects.count(), 1)
        self.assertEqual(response.context["dialog"], dialog)
        mock_choose_support_user.assert_not_called()

    @patch("support_chat.views.is_support")
    def test_marks_only_other_users_unread_messages_as_read(self, mock_is_support):
        mock_is_support.return_value = False
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )

        unread_from_support = SupportMessage.objects.create(
            dialog=dialog,
            sender=self.support_user,
            text="Здравствуйте",
            is_read=False
        )
        unread_from_client = SupportMessage.objects.create(
            dialog=dialog,
            sender=self.user,
            text="Мой текст",
            is_read=False
        )
        read_from_support = SupportMessage.objects.create(
            dialog=dialog,
            sender=self.support_user,
            text="Уже прочитано",
            is_read=True
        )

        self.client.login(username="client", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        unread_from_support.refresh_from_db()
        unread_from_client.refresh_from_db()
        read_from_support.refresh_from_db()

        self.assertTrue(unread_from_support.is_read)
        self.assertFalse(unread_from_client.is_read)
        self.assertTrue(read_from_support.is_read)

    @patch("support_chat.views.is_support")
    def test_context_contains_dialog_messages_and_support_user(self, mock_is_support):
        mock_is_support.return_value = False
        dialog = SupportDialog.objects.create(
            user=self.user,
            support_user=self.support_user
        )
        message = SupportMessage.objects.create(
            dialog=dialog,
            sender=self.support_user,
            text="Тестовое сообщение"
        )

        self.client.login(username="client", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dialog"], dialog)
        self.assertEqual(response.context["support_user"], self.support_user)
        self.assertIn(message, response.context["messages"])
        
        
class SupportDialogsListViewTest(TestCase):
    def setUp(self):
        self.support_user = User.objects.create_user(
            username="operator",
            password="testpass123"
        )
        self.other_support_user = User.objects.create_user(
            username="operator2",
            password="testpass123"
        )
        self.client_user_1 = User.objects.create_user(
            username="client1",
            password="testpass123"
        )
        self.client_user_2 = User.objects.create_user(
            username="client2",
            password="testpass123"
        )
        self.url = reverse("support_chat:support_dialogs_list")

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_post_method_not_allowed(self):
        self.client.login(username="operator", password="testpass123")

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    @patch("support_chat.views.is_support")
    def test_non_support_user_is_redirected_to_chat_dialog(self, mock_is_support):
        mock_is_support.return_value = False
        self.client.login(username="client1", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("support_chat:chat_dialog"),
            fetch_redirect_response=False
        )

    @patch("support_chat.views.is_support")
    def test_support_user_gets_only_own_dialogs(self, mock_is_support):
        mock_is_support.return_value = True

        dialog_1 = SupportDialog.objects.create(
            user=self.client_user_1,
            support_user=self.support_user
        )
        dialog_2 = SupportDialog.objects.create(
            user=self.client_user_2,
            support_user=self.support_user
        )
        SupportDialog.objects.create(
            user=User.objects.create_user(
                username="client3",
                password="testpass123"
            ),
            support_user=self.other_support_user
        )

        self.client.login(username="operator", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dialogs_list.html")

        dialogs = list(response.context["dialogs"])
        self.assertIn(dialog_1, dialogs)
        self.assertIn(dialog_2, dialogs)
        self.assertEqual(len(dialogs), 2)

        for dialog in dialogs:
            self.assertEqual(dialog.support_user, self.support_user)

    @patch("support_chat.views.is_support")
    def test_dialogs_are_ordered_by_updated_at_desc(self, mock_is_support):
        mock_is_support.return_value = True

        dialog_old = SupportDialog.objects.create(
            user=self.client_user_1,
            support_user=self.support_user
        )
        dialog_new = SupportDialog.objects.create(
            user=self.client_user_2,
            support_user=self.support_user
        )

        now = timezone.now()
        SupportDialog.objects.filter(id=dialog_old.id).update(
            updated_at=now - timedelta(hours=1)
        )
        SupportDialog.objects.filter(id=dialog_new.id).update(
            updated_at=now
        )

        self.client.login(username="operator", password="testpass123")
        response = self.client.get(self.url)

        dialogs = list(response.context["dialogs"])
        self.assertEqual(dialogs[0].id, dialog_new.id)
        self.assertEqual(dialogs[1].id, dialog_old.id)

    @patch("support_chat.views.is_support")
    def test_context_contains_dialogs(self, mock_is_support):
        mock_is_support.return_value = True

        dialog = SupportDialog.objects.create(
            user=self.client_user_1,
            support_user=self.support_user
        )

        self.client.login(username="operator", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(dialog, response.context["dialogs"])
        
        
class SupportDialogDetailViewTest(TestCase):
    def setUp(self):
        self.support_user = User.objects.create_user(
            username="operator",
            password="testpass123"
        )
        self.other_support_user = User.objects.create_user(
            username="operator2",
            password="testpass123"
        )
        self.client_user = User.objects.create_user(
            username="client1",
            password="testpass123"
        )
        self.dialog = SupportDialog.objects.create(
            user=self.client_user,
            support_user=self.support_user
        )
        self.url = reverse(
            "support_chat:support_dialog_detail",
            kwargs={"dialog_id": self.dialog.id}
        )

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_post_method_not_allowed(self):
        self.client.login(username="operator", password="testpass123")

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)

    @patch("support_chat.views.is_support")
    def test_non_support_user_redirected_to_chat_dialog(self, mock_is_support):
        mock_is_support.return_value = False
        self.client.login(username="client1", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("support_chat:chat_dialog"))

    @patch("support_chat.views.is_support")
    def test_support_user_can_open_own_dialog(self, mock_is_support):
        mock_is_support.return_value = True
        self.client.login(username="operator", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "support_dialog_detail.html")
        self.assertEqual(response.context["dialog"], self.dialog)

    @patch("support_chat.views.is_support")
    def test_support_user_cannot_open_foreign_dialog(self, mock_is_support):
        mock_is_support.return_value = True
        self.client.login(username="operator2", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    @patch("support_chat.views.is_support")
    def test_marks_only_other_users_unread_messages_as_read(self, mock_is_support):
        mock_is_support.return_value = True

        unread_from_client = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.client_user,
            text="Нужна помощь",
            is_read=False
        )
        unread_from_support = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.support_user,
            text="Ответ оператора",
            is_read=False
        )
        read_from_client = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.client_user,
            text="Уже прочитано",
            is_read=True
        )

        self.client.login(username="operator", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        unread_from_client.refresh_from_db()
        unread_from_support.refresh_from_db()
        read_from_client.refresh_from_db()

        self.assertTrue(unread_from_client.is_read)
        self.assertFalse(unread_from_support.is_read)
        self.assertTrue(read_from_client.is_read)

    @patch("support_chat.views.is_support")
    def test_context_contains_dialog_and_messages(self, mock_is_support):
        mock_is_support.return_value = True

        message = SupportMessage.objects.create(
            dialog=self.dialog,
            sender=self.client_user,
            text="Тестовое сообщение"
        )

        self.client.login(username="operator", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dialog"], self.dialog)
        self.assertIn(message, response.context["messages"])