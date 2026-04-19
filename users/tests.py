from django.core.exceptions import ValidationError
import os
import shutil
import tempfile
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from config import settings
from users.models import Role, Profile

import json
from django.urls import reverse
from unittest.mock import MagicMock, patch
from django.db import IntegrityError
from users.models import PasswordResetCode, EmailVerificationCode
from django.utils import timezone
from datetime import timedelta
from users.views import generate_reset_code, generate_verification_code, send_password_changed_email, send_reset_code_email, send_verification_email
from django.contrib.auth.hashers import make_password



class rolemodelTests(TestCase):
    def test_role_str_returns_name(self):
        role = Role.objects.create(name="Администратор")

        self.assertEqual(str(role), "Администратор")


class profilemodelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ivan",
            password="testpass123"
        )

    def test_profile_str_returns_full_name(self):
        profile = Profile.objects.create(
            user=self.user,
            full_name="Иван Иванов"
        )

        self.assertEqual(str(profile), "Иван Иванов")


class PasswordResetCodeModelTest(TestCase):
    def test_password_reset_code_str_returns_correct_string(self):
        user = User.objects.create_user(
            username="reset_user",
            password="testpass123"
        )

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash="hashed_code"
        )

        self.assertEqual(str(reset_code), f"Reset code for {user}")

    def test_password_reset_code_is_expired_returns_false_if_code_is_fresh(self):
        user = User.objects.create_user(
            username="reset_user_fresh",
            password="testpass123"
        )

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash="hashed_code"
        )

        with patch("users.models.timezone.now", return_value=reset_code.created_at + timedelta(minutes=9)):
            self.assertFalse(reset_code.is_expired())

    def test_password_reset_code_is_expired_returns_true_if_more_than_10_minutes_passed(self):
        user = User.objects.create_user(
            username="reset_user_expired",
            password="testpass123"
        )

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash="hashed_code"
        )

        with patch("users.models.timezone.now", return_value=reset_code.created_at + timedelta(minutes=11)):
            self.assertTrue(reset_code.is_expired())

    def test_password_reset_code_is_expired_returns_false_at_exactly_10_minutes(self):
        user = User.objects.create_user(
            username="reset_user_exact",
            password="testpass123"
        )

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash="hashed_code"
        )

        with patch("users.models.timezone.now", return_value=reset_code.created_at + timedelta(minutes=10)):
            self.assertFalse(reset_code.is_expired())

    def test_password_reset_code_default_is_used_is_false(self):
        user = User.objects.create_user(
            username="reset_user_default",
            password="testpass123"
        )

        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash="hashed_code"
        )

        self.assertFalse(reset_code.is_used)


class EmailVerificationCodeModelTest(TestCase):
    def test_email_verification_code_str_returns_correct_string(self):
        user = User.objects.create_user(
            username="email_user",
            password="testpass123"
        )

        verification_code = EmailVerificationCode.objects.create(
            user=user,
            email="test@example.com",
            code_hash="hashed_code"
        )

        self.assertEqual(str(verification_code), f"Email verification for {user}")

    def test_email_verification_code_is_expired_returns_false_if_code_is_fresh(self):
        user = User.objects.create_user(
            username="email_user_fresh",
            password="testpass123"
        )

        verification_code = EmailVerificationCode.objects.create(
            user=user,
            email="fresh@example.com",
            code_hash="hashed_code"
        )

        with patch("users.models.timezone.now", return_value=verification_code.created_at + timedelta(minutes=9)):
            self.assertFalse(verification_code.is_expired())

    def test_email_verification_code_is_expired_returns_true_if_more_than_10_minutes_passed(self):
        user = User.objects.create_user(
            username="email_user_expired",
            password="testpass123"
        )

        verification_code = EmailVerificationCode.objects.create(
            user=user,
            email="expired@example.com",
            code_hash="hashed_code"
        )

        with patch("users.models.timezone.now", return_value=verification_code.created_at + timedelta(minutes=11)):
            self.assertTrue(verification_code.is_expired())

    def test_email_verification_code_is_expired_returns_false_at_exactly_10_minutes(self):
        user = User.objects.create_user(
            username="email_user_exact",
            password="testpass123"
        )

        verification_code = EmailVerificationCode.objects.create(
            user=user,
            email="exact@example.com",
            code_hash="hashed_code"
        )

        with patch("users.models.timezone.now", return_value=verification_code.created_at + timedelta(minutes=10)):
            self.assertFalse(verification_code.is_expired())

    def test_email_verification_code_default_is_used_is_false(self):
        user = User.objects.create_user(
            username="email_user_default",
            password="testpass123"
        )

        verification_code = EmailVerificationCode.objects.create(
            user=user,
            email="default@example.com",
            code_hash="hashed_code"
        )

        self.assertFalse(verification_code.is_used)

        
class registerTests(TestCase):
    def setUp(self):
        return super().setUp()
    
    def test_register_success(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "StrongPassword123!",
                "email": "newuser@example.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertTrue(Profile.objects.filter(user__username="newuser").exists())

        data = response.json()
        self.assertEqual(data["message"], "Пользователь зарегистрирован")
        self.assertEqual(data["username"], "newuser")
        
    def test_register_application_json_status_code_400(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "StrongPassword123!",
                "email": "newuser@example.com"
            }),
            content_type="application/x-www-form-urlencoded"
        )

        self.assertEqual(response.status_code, 400)
        
    def test_register_invalid_json_status_code_400(self):
        response = self.client.post(
            reverse("users:register"),
            data='{"username": "newuser", "password": }',
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Невалидный JSON")
        
    def test_register_not_username_status_code_400(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "",
                "password": "StrongPassword123!",
                "email": "newuser@example.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "username обязателен")
        self.assertFalse(User.objects.filter(username="").exists())
        self.assertFalse(Profile.objects.filter(user__username="").exists())
        
    def test_register_not_password_status_code_400(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "",
                "email": "newuser@example.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "password обязателен")
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        
    def test_register_not_password_json_status_code_400(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "email": "newuser@example.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "password обязателен")
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        
    def test_register_exist_user_status_code_400(self):
        User.objects.create_user(
            username="ivan",
            password="testpass123"
        )

        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "ivan",
                "password": "testpass123",
                "email": "newuser@example.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Пользователь уже существует")
        self.assertEqual(User.objects.filter(username="ivan").count(), 1)
        
    def test_register_invalid_email_status_code_400(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "StrongPassword123!",
                "email": "not-an-email"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Неверный email")
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        
    def test_register_invalid_email_status_code_400_2(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "StrongPassword123!",
                "email": "user@"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Неверный email")
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        
    def test_register_weak_password_status_code_400(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "123",
                "email": "newuser@example.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("error", data)
        self.assertIsInstance(data["error"], list)

        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        
    def test_register_weak_password_status_code_400_2(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "newuser_123",
                "email": "newuser@example.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("error", data)
        self.assertIsInstance(data["error"], list)

        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        
    def test_register_existing_email_status_code_400(self):
        User.objects.create_user(
            username="ivan",
            password="testpass123",
            email="user@gmail.com"
        )

        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser",
                "password": "StrongPassword123!",
                "email": "user@gmail.com"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Email уже используется")
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        self.assertEqual(User.objects.filter(email="user@gmail.com").count(), 1)
        
    def test_register_status_code_400_integrity_error(self):
        with patch("users.views.User.objects.create_user", side_effect=IntegrityError):
            response = self.client.post(
                reverse("users:register"),
                data=json.dumps({
                    "username": "newuser",
                    "password": "StrongPassword123!",
                    "email": "newuser@example.com"
                }),
                content_type="application/json"
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Пользователь или email уже существует")
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
        
    def test_register_status_code_500_exception(self):
        with patch("users.views.logger.exception")as mock_logger:
            with patch("users.views.User.objects.create_user", side_effect=Exception("asdasfd")):
                response = self.client.post(
                    reverse("users:register"),
                    data=json.dumps({
                        "username": "newuser",
                        "password": "StrongPassword123!",
                        "email": "newuser@example.com"
                    }),
                    content_type="application/json"
                )

            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json()["error"], "Ошибка при регистрации")
            mock_logger.assert_called_once()
            self.assertFalse(User.objects.filter(username="newuser").exists())
            self.assertFalse(Profile.objects.filter(user__username="newuser").exists())
            
    def test_register_success_without_email(self):
        response = self.client.post(
            reverse("users:register"),
            data=json.dumps({
                "username": "newuser_no_email",
                "password": "StrongPassword123!"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="newuser_no_email").exists())
        self.assertTrue(Profile.objects.filter(user__username="newuser_no_email").exists())

        user = User.objects.get(username="newuser_no_email")
        self.assertEqual(user.email, "")

    
class loginTests(TestCase):
    def test_login_success(self):
        User.objects.create_user(
            username="alex",
            password="testpass12345A!"
        )

        response = self.client.post(
            reverse("users:login"),
            data=json.dumps({
                "username": "alex",
                "password": "testpass12345A!"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["message"], "Вход выполнен")
        self.assertEqual(data["username"], "alex")

        self.assertEqual(str(self.client.session["_auth_user_id"]), str(data["user_id"]))
        
    def test_login_content_type_status_code_400(self):
        response = self.client.post(
            reverse("users:login"),
            data="username=alex&password=testpass12345A!",
            content_type="application/x-www-form-urlencoded"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Ожидается application/json")
        
    def test_login_json_status_code_400(self):
        response = self.client.post(
            reverse("users:login"),
            data='{"username": "alex", "password": }',
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Невалидный JSON")
        
    def test_login_not_username_status_code_400(self):
        response = self.client.post(
            reverse("users:login"),
            data=json.dumps({
                "password": "testpass12345A!"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "username обязателен")
        
    def test_login_not_password_status_code_400(self):
        response = self.client.post(
            reverse("users:login"),
            data=json.dumps({
                "username": "alex",
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "password обязателен")
        
    
    def test_login_wrong_password_status_code_401(self):
        User.objects.create_user(
            username="alex",
            password="testpass12345A!"
        )

        response = self.client.post(
            reverse("users:login"),
            data=json.dumps({
                "username": "alex",
                "password": "wrongpass"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Неверный логин или пароль")
        
    def test_login_status_code_401_when_authenticate_return_none(self):
        with patch("users.views.authenticate", return_value=None):
            response = self.client.post(
                reverse("users:login"),
                data=json.dumps({
                    "username": "alex",
                    "password": "wrongpass"
                }),
                content_type="application/json"
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Неверный логин или пароль")
        
        
    def test_login_status_code_500_exception(self):
        User.objects.create_user(
            username="alex",
            password="testpass12345A!"
        )
        with patch("users.views.logger.exception")as mock_logger:
            with patch("users.views.login", side_effect=Exception("asdf")):
                response = self.client.post(
                    reverse("users:login"),
                    data=json.dumps({
                        "username": "alex",
                        "password": "testpass12345A!"
                    }),
                    content_type="application/json"
                )
            mock_logger.assert_called_once()
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json()["error"], "Ошибка при входе")
            

class logoutTests(TestCase):
    def test_logout_unauthorized_returns_401(self):
        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Не авторизован")
        
    def test_logout_success_returns_200(self):
        user = User.objects.create_user(
            username="alex",
            password="testpass12345A!"
        )

        self.client.force_login(user)

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Выход выполнен")
        self.assertNotIn("_auth_user_id", self.client.session)


class userprofileTests(TestCase):
    def test_profile_unauthorized_sattus_code_401(self):
        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Не авторизован")


    def test_profile_not_found_status_code_404(self):
        user = User.objects.create_user(
            username="alex",
            password="testpass12345A!",
            email="alex@example.com"
        )

        self.client.force_login(user)

        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Профиль не найден")


    def test_profile_success_status_code_200(self):
        user = User.objects.create_user(
            username="alex",
            password="testpass12345A!",
            email="alex@example.com"
        )

        Profile.objects.create(
            user=user,
            full_name="Алексей Иванов",
            city="Москва",
            delivery_address="ул. Пушкина, д. 1",
            postal_code="123456"
        )

        self.client.force_login(user)

        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["username"], "alex")
        self.assertEqual(data["email"], "alex@example.com")
        self.assertEqual(data["full_name"], "Алексей Иванов")
        self.assertEqual(data["city"], "Москва")
        self.assertEqual(data["delivery_address"], "ул. Пушкина, д. 1")
        self.assertEqual(data["postal_code"], "123456")
        

class PasswordResetTest(TestCase):
    @patch("users.views.secrets.randbelow")
    def test_generate_reset_code_returns_zero_padded_6_digit_string(self, mock_randbelow):
        mock_randbelow.return_value = 123

        code = generate_reset_code()

        self.assertEqual(code, "000123")
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        mock_randbelow.assert_called_once_with(1000000)

    @patch("users.views.EmailMultiAlternatives")
    @patch("users.views.render_to_string")
    def test_send_reset_code_email_renders_templates_and_sends_email(
        self,
        mock_render_to_string,
        mock_email_class
    ):
        user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="testpass123"
        )

        mock_render_to_string.side_effect = [
            "text email content",
            "<p>html email content</p>",
        ]

        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        send_reset_code_email(user, "123456")

        expected_context = {
            "user": user,
            "code": "123456",
            "site_name": "Букинист",
            "minutes": 10,
        }

        self.assertEqual(mock_render_to_string.call_count, 2)
        mock_render_to_string.assert_any_call(
            "emails/password_reset_code_email.txt",
            expected_context
        )
        mock_render_to_string.assert_any_call(
            "emails/password_reset_code_email.html",
            expected_context
        )

        mock_email_class.assert_called_once_with(
            subject="Код восстановления пароля — Букинист",
            body="text email content",
            to=["reader@example.com"],
        )

        mock_email_instance.attach_alternative.assert_called_once_with(
            "<p>html email content</p>",
            "text/html"
        )
        mock_email_instance.send.assert_called_once()
        
    @patch("users.views.secrets.randbelow")
    def test_generate_reset_code_returns_999999_for_max_value(self, mock_randbelow):
        mock_randbelow.return_value = 999999

        code = generate_reset_code()

        self.assertEqual(code, "999999")
        
        
    @patch("users.views.EmailMultiAlternatives")
    @patch("users.views.render_to_string")
    def test_send_password_changed_email_renders_templates_and_sends_email(
        self,
        mock_render_to_string,
        mock_email_class
    ):
        user = User.objects.create_user(
            username="reader_changed",
            email="reader_changed@example.com",
            password="testpass123"
        )

        mock_render_to_string.side_effect = [
            "password changed text content",
            "<p>password changed html content</p>",
        ]

        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        send_password_changed_email(user)

        expected_context = {
            "user": user,
            "site_name": "Букинист",
        }

        self.assertEqual(mock_render_to_string.call_count, 2)
        mock_render_to_string.assert_any_call(
            "emails/password_changed.txt",
            expected_context
        )
        mock_render_to_string.assert_any_call(
            "emails/password_changed.html",
            expected_context
        )

        mock_email_class.assert_called_once_with(
            subject="Пароль был изменён — Букинист",
            body="password changed text content",
            to=["reader_changed@example.com"],
        )

        mock_email_instance.attach_alternative.assert_called_once_with(
            "<p>password changed html content</p>",
            "text/html"
        )
        mock_email_instance.send.assert_called_once()
        
        
class PasswordResetResendViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="testpass123"
        )
        self.url = reverse("users:password_reset_resend")

    def test_redirects_to_request_if_email_not_in_session(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_request"),
            fetch_redirect_response=False
        )

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_resends_code_for_active_user_with_usable_password(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        mock_generate_reset_code.return_value = "123456"

        old_code_1 = PasswordResetCode.objects.create(
            user=self.user,
            code_hash="old_hash_1",
            is_used=False
        )
        old_code_2 = PasswordResetCode.objects.create(
            user=self.user,
            code_hash="old_hash_2",
            is_used=False
        )
        used_code = PasswordResetCode.objects.create(
            user=self.user,
            code_hash="used_hash",
            is_used=True
        )

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        old_code_1.refresh_from_db()
        old_code_2.refresh_from_db()
        used_code.refresh_from_db()

        self.assertTrue(old_code_1.is_used)
        self.assertTrue(old_code_2.is_used)
        self.assertTrue(used_code.is_used)

        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 4)

        new_code = PasswordResetCode.objects.filter(user=self.user).latest("id")
        self.assertEqual(new_code.user, self.user)
        self.assertFalse(new_code.is_used)
        self.assertNotEqual(new_code.code_hash, "123456")

        mock_generate_reset_code.assert_called_once_with()
        mock_send_reset_code_email.assert_called_once_with(self.user, "123456")

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_does_nothing_if_user_not_found(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        session = self.client.session
        session["password_reset_email"] = "unknown@example.com"
        session.save()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        self.assertEqual(PasswordResetCode.objects.count(), 0)
        mock_generate_reset_code.assert_not_called()
        mock_send_reset_code_email.assert_not_called()

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_does_nothing_if_user_is_inactive(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        self.assertEqual(PasswordResetCode.objects.count(), 0)
        mock_generate_reset_code.assert_not_called()
        mock_send_reset_code_email.assert_not_called()

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_does_nothing_if_user_has_no_usable_password(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        self.user.set_unusable_password()
        self.user.save()

        PasswordResetCode.objects.create(
            user=self.user,
            code_hash="old_hash",
            is_used=False
        )

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        old_code = PasswordResetCode.objects.get(user=self.user)
        self.assertFalse(old_code.is_used)

        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 1)
        mock_generate_reset_code.assert_not_called()
        mock_send_reset_code_email.assert_not_called()

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_finds_user_by_email_case_insensitively(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        mock_generate_reset_code.return_value = "654321"

        session = self.client.session
        session["password_reset_email"] = "READER@EXAMPLE.COM"
        session.save()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 1)
        mock_generate_reset_code.assert_called_once_with()
        mock_send_reset_code_email.assert_called_once_with(self.user, "654321")
        
        
class PasswordResetRequestViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="testpass123"
        )
        self.url = reverse("users:password_reset_request")

    def test_get_renders_password_reset_request_template(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_request.html")

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_post_creates_new_reset_code_and_sends_email_for_active_user(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        mock_generate_reset_code.return_value = "123456"

        old_code_1 = PasswordResetCode.objects.create(
            user=self.user,
            code_hash="old_hash_1",
            is_used=False
        )
        old_code_2 = PasswordResetCode.objects.create(
            user=self.user,
            code_hash="old_hash_2",
            is_used=False
        )
        used_code = PasswordResetCode.objects.create(
            user=self.user,
            code_hash="used_hash",
            is_used=True
        )

        response = self.client.post(self.url, {
            "email": "reader@example.com"
        })

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        session = self.client.session
        self.assertEqual(session["password_reset_email"], "reader@example.com")

        old_code_1.refresh_from_db()
        old_code_2.refresh_from_db()
        used_code.refresh_from_db()

        self.assertTrue(old_code_1.is_used)
        self.assertTrue(old_code_2.is_used)
        self.assertTrue(used_code.is_used)

        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 4)

        new_code = PasswordResetCode.objects.filter(user=self.user).latest("id")
        self.assertEqual(new_code.user, self.user)
        self.assertFalse(new_code.is_used)
        self.assertNotEqual(new_code.code_hash, "123456")

        mock_generate_reset_code.assert_called_once_with()
        mock_send_reset_code_email.assert_called_once_with(self.user, "123456")

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_post_does_not_create_code_if_user_not_found(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        response = self.client.post(self.url, {
            "email": "unknown@example.com"
        })

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        session = self.client.session
        self.assertEqual(session["password_reset_email"], "unknown@example.com")

        self.assertEqual(PasswordResetCode.objects.count(), 0)
        mock_generate_reset_code.assert_not_called()
        mock_send_reset_code_email.assert_not_called()

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_post_does_not_create_code_if_user_is_inactive(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(self.url, {
            "email": "reader@example.com"
        })

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        session = self.client.session
        self.assertEqual(session["password_reset_email"], "reader@example.com")

        self.assertEqual(PasswordResetCode.objects.count(), 0)
        mock_generate_reset_code.assert_not_called()
        mock_send_reset_code_email.assert_not_called()

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_post_does_not_create_code_if_user_has_unusable_password(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        self.user.set_unusable_password()
        self.user.save()

        old_code = PasswordResetCode.objects.create(
            user=self.user,
            code_hash="old_hash",
            is_used=False
        )

        response = self.client.post(self.url, {
            "email": "reader@example.com"
        })

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        session = self.client.session
        self.assertEqual(session["password_reset_email"], "reader@example.com")

        old_code.refresh_from_db()
        self.assertFalse(old_code.is_used)

        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 1)
        mock_generate_reset_code.assert_not_called()
        mock_send_reset_code_email.assert_not_called()

    @patch("users.views.send_reset_code_email")
    @patch("users.views.generate_reset_code")
    def test_post_normalizes_email_with_strip_and_lower(
        self,
        mock_generate_reset_code,
        mock_send_reset_code_email
    ):
        mock_generate_reset_code.return_value = "654321"

        response = self.client.post(self.url, {
            "email": "  READER@EXAMPLE.COM  "
        })

        self.assertRedirects(
            response,
            reverse("users:password_reset_code"),
            fetch_redirect_response=False
        )

        session = self.client.session
        self.assertEqual(session["password_reset_email"], "reader@example.com")

        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 1)
        mock_generate_reset_code.assert_called_once_with()
        mock_send_reset_code_email.assert_called_once_with(self.user, "654321")
        
        
class PasswordResetCodeViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="testpass123"
        )
        self.url = reverse("users:password_reset_code")

    def test_redirects_to_request_if_email_not_in_session(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_request"),
            fetch_redirect_response=False
        )

    def test_get_renders_template_with_error_none(self):
        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_code.html")
        self.assertIsNone(response.context["error"])

    def test_post_returns_error_if_user_not_found(self):
        session = self.client.session
        session["password_reset_email"] = "unknown@example.com"
        session.save()

        response = self.client.post(self.url, {
            "code": "123456"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_code.html")
        self.assertEqual(response.context["error"], "Неверный или просроченный код.")

    def test_post_returns_error_if_user_has_unusable_password(self):
        self.user.set_unusable_password()
        self.user.save()

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.post(self.url, {
            "code": "123456"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_code.html")
        self.assertEqual(response.context["error"], "Неверный или просроченный код.")

    def test_post_returns_error_if_reset_code_not_found(self):
        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.post(self.url, {
            "code": "123456"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_code.html")
        self.assertEqual(response.context["error"], "Неверный или просроченный код.")

    @patch("users.models.PasswordResetCode.is_expired", return_value=True)
    def test_post_returns_error_if_code_is_expired(self, mock_is_expired):
        PasswordResetCode.objects.create(
            user=self.user,
            code_hash=make_password("123456"),
            is_used=False
        )

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.post(self.url, {
            "code": "123456"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_code.html")
        self.assertEqual(response.context["error"], "Код истёк. Запросите новый.")
        mock_is_expired.assert_called_once()

    @patch("users.models.PasswordResetCode.is_expired", return_value=False)
    def test_post_returns_error_if_code_is_incorrect(self, mock_is_expired):
        reset_code = PasswordResetCode.objects.create(
            user=self.user,
            code_hash=make_password("123456"),
            is_used=False
        )

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.post(self.url, {
            "code": "654321"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_code.html")
        self.assertEqual(response.context["error"], "Неверный или просроченный код.")

        reset_code.refresh_from_db()
        self.assertFalse(reset_code.is_used)
        mock_is_expired.assert_called_once()

    @patch("users.models.PasswordResetCode.is_expired", return_value=False)
    def test_post_marks_code_used_sets_session_and_redirects_if_code_is_correct(self, mock_is_expired):
        reset_code = PasswordResetCode.objects.create(
            user=self.user,
            code_hash=make_password("123456"),
            is_used=False
        )

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.post(self.url, {
            "code": "123456"
        })

        self.assertRedirects(
            response,
            reverse("users:password_reset_new"),
            fetch_redirect_response=False
        )

        reset_code.refresh_from_db()
        self.assertTrue(reset_code.is_used)

        session = self.client.session
        self.assertEqual(session["password_reset_verified_user_id"], self.user.id)
        mock_is_expired.assert_called_once()

    def test_post_uses_latest_unused_code(self):
        old_code = PasswordResetCode.objects.create(
            user=self.user,
            code_hash=make_password("111111"),
            is_used=False
        )
        new_code = PasswordResetCode.objects.create(
            user=self.user,
            code_hash=make_password("222222"),
            is_used=False
        )

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session.save()

        response = self.client.post(self.url, {
            "code": "222222"
        })

        self.assertRedirects(
            response,
            reverse("users:password_reset_new"),
            fetch_redirect_response=False
        )

        old_code.refresh_from_db()
        new_code.refresh_from_db()

        self.assertFalse(old_code.is_used)
        self.assertTrue(new_code.is_used)
        
        
class PasswordResetNewViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="oldpass123"
        )
        self.url = reverse("users:password_reset_new")

    def test_redirects_to_request_if_verified_user_id_not_in_session(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_request"),
            fetch_redirect_response=False
        )

    def test_redirects_to_request_if_user_not_found(self):
        session = self.client.session
        session["password_reset_verified_user_id"] = 999999
        session.save()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_request"),
            fetch_redirect_response=False
        )

    def test_redirects_to_request_if_user_is_inactive(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        session = self.client.session
        session["password_reset_verified_user_id"] = self.user.id
        session.save()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("users:password_reset_request"),
            fetch_redirect_response=False
        )

    def test_get_renders_template_with_error_none(self):
        session = self.client.session
        session["password_reset_verified_user_id"] = self.user.id
        session.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_new.html")
        self.assertIsNone(response.context["error"])

    def test_post_returns_error_if_passwords_do_not_match(self):
        session = self.client.session
        session["password_reset_verified_user_id"] = self.user.id
        session.save()

        response = self.client.post(self.url, {
            "password": "newpass123",
            "password_confirm": "differentpass123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_new.html")
        self.assertEqual(response.context["error"], "Пароли не совпадают.")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))

    @patch("users.views.send_password_changed_email")
    @patch("users.views.validate_password")
    def test_post_returns_validation_error_message(
        self,
        mock_validate_password,
        mock_send_password_changed_email
    ):
        mock_validate_password.side_effect = ValidationError([
            "Пароль слишком короткий.",
            "Пароль слишком простой."
        ])

        session = self.client.session
        session["password_reset_verified_user_id"] = self.user.id
        session.save()

        response = self.client.post(self.url, {
            "password": "123",
            "password_confirm": "123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_new.html")
        self.assertEqual(
            response.context["error"],
            "Пароль слишком короткий. Пароль слишком простой."
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))
        mock_send_password_changed_email.assert_not_called()

    @patch("users.views.send_password_changed_email")
    @patch("users.views.validate_password")
    def test_post_sets_new_password_sends_email_clears_session_and_redirects(
        self,
        mock_validate_password,
        mock_send_password_changed_email
    ):
        mock_validate_password.return_value = None

        session = self.client.session
        session["password_reset_email"] = "reader@example.com"
        session["password_reset_verified_user_id"] = self.user.id
        session.save()

        response = self.client.post(self.url, {
            "password": "NewStrongPass123!",
            "password_confirm": "NewStrongPass123!",
        })

        self.assertRedirects(
            response,
            reverse("login_page"),
            fetch_redirect_response=False
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))

        mock_validate_password.assert_called_once()
        mock_send_password_changed_email.assert_called_once_with(self.user)

        session = self.client.session
        self.assertNotIn("password_reset_email", session)
        self.assertNotIn("password_reset_verified_user_id", session)
        
        
class EditProfilePageViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            password="testpass123"
        )
        self.url = reverse("users:edit_profile_page")

    def test_edit_profile_page_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        expected_url = f"{settings.LOGIN_URL}?next={self.url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )

    def test_edit_profile_page_creates_profile_if_not_exists(self):
        self.client.login(username="reader", password="testpass123")

        self.assertFalse(Profile.objects.filter(user=self.user).exists())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "edit_profile.html")

        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)
        profile = Profile.objects.get(user=self.user)

        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.full_name, self.user.username)
        self.assertEqual(response.context["profile"], profile)

    def test_edit_profile_page_uses_existing_profile(self):
        profile = Profile.objects.create(
            user=self.user,
            full_name="Иван Иванов"
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "edit_profile.html")

        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

        profile.refresh_from_db()
        self.assertEqual(profile.full_name, "Иван Иванов")
        self.assertEqual(response.context["profile"], profile)
        
        
class UpdateProfileViewTest(TestCase):
    def setUp(self):
        self.temp_media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()

        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="testpass123"
        )
        self.url = reverse("users:update_profile")
        self.profile_url = reverse("profile_page")

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_media, ignore_errors=True)

    def test_update_profile_redirects_anonymous_user_to_login(self):
        response = self.client.post(self.url, {})

        expected_url = f"{settings.LOGIN_URL}?next={self.url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )

    def test_update_profile_get_method_not_allowed(self):
        self.client.login(username="reader", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_update_profile_creates_profile_if_not_exists_and_updates_fields(self):
        self.client.login(username="reader", password="testpass123")

        self.assertFalse(Profile.objects.filter(user=self.user).exists())

        response = self.client.post(self.url, {
            "full_name": "Иван Иванов",
            "email": "reader@example.com",
            "city": "Москва",
            "delivery_address": "ул. Пушкина, 1",
            "postal_code": "123456",
        }, follow=True)

        self.assertRedirects(response, self.profile_url)
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, "Иван Иванов")
        self.assertEqual(profile.city, "Москва")
        self.assertEqual(profile.delivery_address, "ул. Пушкина, 1")
        self.assertEqual(profile.postal_code, "123456")

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "reader@example.com")

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Профиль обновлён.")

    def test_update_profile_does_not_replace_full_name_if_empty(self):
        Profile.objects.create(
            user=self.user,
            full_name="Старое имя",
            city="Старый город",
            delivery_address="Старый адрес",
            postal_code="000000",
        )

        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "full_name": "   ",
            "email": "reader@example.com",
            "city": "Новый город",
            "delivery_address": "Новый адрес",
            "postal_code": "111111",
        }, follow=True)

        self.assertRedirects(response, self.profile_url)

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, "Старое имя")
        self.assertEqual(profile.city, "Новый город")
        self.assertEqual(profile.delivery_address, "Новый адрес")
        self.assertEqual(profile.postal_code, "111111")

    def test_update_profile_updates_avatar_if_uploaded(self):
        Profile.objects.create(
            user=self.user,
            full_name="Иван Иванов"
        )

        self.client.login(username="reader", password="testpass123")

        avatar = SimpleUploadedFile(
            "avatar.jpg",
            b"fake-image-content",
            content_type="image/jpeg"
        )

        response = self.client.post(
            self.url,
            {
                "full_name": "Иван Иванов",
                "email": "reader@example.com",
                "city": "",
                "delivery_address": "",
                "postal_code": "",
                "avatar": avatar,
            },
            follow=True
        )

        self.assertRedirects(response, self.profile_url)

        profile = Profile.objects.get(user=self.user)
        self.assertTrue(bool(profile.avatar))
        self.assertIn("avatars/", profile.avatar.name)

    def test_update_profile_changes_email_and_resets_verification(self):
        profile = Profile.objects.create(
            user=self.user,
            full_name="Иван Иванов",
            is_email_verified=True,
            email_verified_at=timezone.now(),
        )

        active_code_1 = EmailVerificationCode.objects.create(
            user=self.user,
            email="reader@example.com",
            code_hash="hash1",
            is_used=False
        )
        active_code_2 = EmailVerificationCode.objects.create(
            user=self.user,
            email="reader@example.com",
            code_hash="hash2",
            is_used=False
        )
        used_code = EmailVerificationCode.objects.create(
            user=self.user,
            email="reader@example.com",
            code_hash="hash3",
            is_used=True
        )

        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "full_name": "Новое имя",
            "email": "newreader@example.com",
            "city": "Москва",
            "delivery_address": "ул. Ленина, 10",
            "postal_code": "654321",
        }, follow=True)

        self.assertRedirects(response, self.profile_url)

        self.user.refresh_from_db()
        profile.refresh_from_db()
        active_code_1.refresh_from_db()
        active_code_2.refresh_from_db()
        used_code.refresh_from_db()

        self.assertEqual(self.user.email, "newreader@example.com")
        self.assertFalse(profile.is_email_verified)
        self.assertIsNone(profile.email_verified_at)

        self.assertTrue(active_code_1.is_used)
        self.assertTrue(active_code_2.is_used)
        self.assertTrue(used_code.is_used)

    def test_update_profile_does_not_reset_verification_if_email_not_changed(self):
        verified_at = timezone.now()

        profile = Profile.objects.create(
            user=self.user,
            full_name="Иван Иванов",
            is_email_verified=True,
            email_verified_at=verified_at,
        )

        code = EmailVerificationCode.objects.create(
            user=self.user,
            email="reader@example.com",
            code_hash="hash1",
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "full_name": "Новое имя",
            "email": "reader@example.com",
            "city": "СПб",
            "delivery_address": "Невский 1",
            "postal_code": "190000",
        }, follow=True)

        self.assertRedirects(response, self.profile_url)

        self.user.refresh_from_db()
        profile.refresh_from_db()
        code.refresh_from_db()

        self.assertEqual(self.user.email, "reader@example.com")
        self.assertTrue(profile.is_email_verified)
        self.assertEqual(profile.email_verified_at, verified_at)
        self.assertFalse(code.is_used)
        
        
class EmailVerificationUtilsTest(TestCase):
    @patch("users.views.secrets.randbelow")
    def test_generate_verification_code_returns_zero_padded_6_digit_string(self, mock_randbelow):
        mock_randbelow.return_value = 321

        code = generate_verification_code()

        self.assertEqual(code, "000321")
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        mock_randbelow.assert_called_once_with(1000000)

    @patch("users.views.EmailMultiAlternatives")
    @patch("users.views.render_to_string")
    def test_send_verification_email_renders_templates_and_sends_email(
        self,
        mock_render_to_string,
        mock_email_class
    ):
        user = User.objects.create_user(
            username="verify_user",
            email="verify@example.com",
            password="testpass123"
        )

        mock_render_to_string.side_effect = [
            "verification text content",
            "<p>verification html content</p>",
        ]

        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        send_verification_email(user, "654321")

        expected_context = {
            "user": user,
            "code": "654321",
            "site_name": "Букинист",
            "minutes": 10,
        }

        self.assertEqual(mock_render_to_string.call_count, 2)
        mock_render_to_string.assert_any_call(
            "emails/email_verification.txt",
            expected_context
        )
        mock_render_to_string.assert_any_call(
            "emails/email_verification.html",
            expected_context
        )

        mock_email_class.assert_called_once_with(
            subject="Подтверждение почты — Букинист",
            body="verification text content",
            to=["verify@example.com"],
        )

        mock_email_instance.attach_alternative.assert_called_once_with(
            "<p>verification html content</p>",
            "text/html"
        )
        mock_email_instance.send.assert_called_once()
            

class VerifyEmailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="testpass123"
        )
        self.url = reverse("verify_email")
        self.profile_url = reverse("profile_page")

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        expected_url = f"{settings.LOGIN_URL}?next={self.url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )

    def test_redirects_to_profile_if_email_already_verified(self):
        Profile.objects.create(
            user=self.user,
            full_name="Reader",
            is_email_verified=True
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.profile_url,
            fetch_redirect_response=False,
        )

    @patch("users.views.send_verification_email")
    @patch("users.views.generate_verification_code")
    def test_get_creates_profile_and_sends_code_if_no_active_code(
        self,
        mock_generate_verification_code,
        mock_send_verification_email
    ):
        mock_generate_verification_code.return_value = "123456"

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "verify_email.html")
        self.assertIsNone(response.context["error"])

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, self.user.username)
        self.assertFalse(profile.is_email_verified)

        self.assertEqual(
            EmailVerificationCode.objects.filter(
                user=self.user,
                email=self.user.email
            ).count(),
            1
        )

        code_obj = EmailVerificationCode.objects.get(
            user=self.user,
            email=self.user.email
        )
        self.assertFalse(code_obj.is_used)
        self.assertNotEqual(code_obj.code_hash, "123456")

        mock_generate_verification_code.assert_called_once_with()
        mock_send_verification_email.assert_called_once_with(
            self.user,
            "123456"
        )

    @patch("users.views.send_verification_email")
    @patch("users.views.generate_verification_code")
    @patch("users.models.EmailVerificationCode.is_expired", return_value=False)
    def test_get_does_not_send_new_code_if_active_code_exists_and_not_expired(
        self,
        mock_is_expired,
        mock_generate_verification_code,
        mock_send_verification_email
    ):
        Profile.objects.create(
            user=self.user,
            full_name="Reader"
        )
        old_code = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash=make_password("111111"),
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "verify_email.html")
        self.assertIsNone(response.context["error"])

        old_code.refresh_from_db()
        self.assertFalse(old_code.is_used)
        self.assertEqual(
            EmailVerificationCode.objects.filter(
                user=self.user,
                email=self.user.email
            ).count(),
            1
        )

        mock_is_expired.assert_called_once()
        mock_generate_verification_code.assert_not_called()
        mock_send_verification_email.assert_not_called()

    @patch("users.views.send_verification_email")
    @patch("users.views.generate_verification_code")
    @patch("users.models.EmailVerificationCode.is_expired", return_value=True)
    def test_get_invalidates_old_code_and_sends_new_if_active_code_expired(
        self,
        mock_is_expired,
        mock_generate_verification_code,
        mock_send_verification_email
    ):
        mock_generate_verification_code.return_value = "222222"

        Profile.objects.create(
            user=self.user,
            full_name="Reader"
        )
        old_code = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash="old_hash",
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "verify_email.html")
        self.assertIsNone(response.context["error"])

        old_code.refresh_from_db()
        self.assertTrue(old_code.is_used)

        self.assertEqual(
            EmailVerificationCode.objects.filter(
                user=self.user,
                email=self.user.email
            ).count(),
            2
        )

        new_code = EmailVerificationCode.objects.latest("id")
        self.assertFalse(new_code.is_used)
        self.assertEqual(new_code.user, self.user)
        self.assertEqual(new_code.email, self.user.email)

        mock_is_expired.assert_called_once()
        mock_generate_verification_code.assert_called_once_with()
        mock_send_verification_email.assert_called_once_with(
            self.user,
            "222222"
        )

    def test_post_returns_error_if_code_not_found(self):
        Profile.objects.create(
            user=self.user,
            full_name="Reader"
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.post(self.url, {
            "code": "123456"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "verify_email.html")
        self.assertEqual(response.context["error"], "Код не найден.")

    @patch("users.models.EmailVerificationCode.is_expired", return_value=True)
    def test_post_returns_error_if_code_expired(self, mock_is_expired):
        Profile.objects.create(
            user=self.user,
            full_name="Reader"
        )
        code_obj = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash=make_password("123456"),
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.post(self.url, {
            "code": "123456"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "verify_email.html")
        self.assertEqual(response.context["error"], "Код истёк. Запросите новый.")

        code_obj.refresh_from_db()
        self.assertFalse(code_obj.is_used)
        mock_is_expired.assert_called_once()

    @patch("users.models.EmailVerificationCode.is_expired", return_value=False)
    def test_post_returns_error_if_code_incorrect(self, mock_is_expired):
        Profile.objects.create(
            user=self.user,
            full_name="Reader"
        )
        code_obj = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash=make_password("123456"),
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.post(self.url, {
            "code": "654321"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "verify_email.html")
        self.assertEqual(response.context["error"], "Неверный код.")

        code_obj.refresh_from_db()
        self.assertFalse(code_obj.is_used)
        mock_is_expired.assert_called_once()

    @patch("users.models.EmailVerificationCode.is_expired", return_value=False)
    def test_post_marks_code_used_verifies_email_and_redirects(
        self,
        mock_is_expired
    ):
        profile = Profile.objects.create(
            user=self.user,
            full_name="Reader",
            is_email_verified=False,
            email_verified_at=None
        )
        code_obj = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash=make_password("123456"),
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")

        before_call = timezone.now()

        response = self.client.post(self.url, {
            "code": "123456"
        })

        after_call = timezone.now()

        self.assertRedirects(
            response,
            self.profile_url,
            fetch_redirect_response=False,
        )

        code_obj.refresh_from_db()
        profile.refresh_from_db()

        self.assertTrue(code_obj.is_used)
        self.assertTrue(profile.is_email_verified)
        self.assertIsNotNone(profile.email_verified_at)
        self.assertGreaterEqual(profile.email_verified_at, before_call)
        self.assertLessEqual(profile.email_verified_at, after_call)
        mock_is_expired.assert_called_once()

    @patch("users.models.EmailVerificationCode.is_expired", return_value=False)
    def test_post_uses_latest_unused_code(self, mock_is_expired):
        Profile.objects.create(
            user=self.user,
            full_name="Reader"
        )

        old_code = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash=make_password("111111"),
            is_used=False
        )
        new_code = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash=make_password("222222"),
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.post(self.url, {
            "code": "222222"
        })

        self.assertRedirects(
            response,
            self.profile_url,
            fetch_redirect_response=False,
        )

        old_code.refresh_from_db()
        new_code.refresh_from_db()

        self.assertFalse(old_code.is_used)
        self.assertTrue(new_code.is_used)
        
        
class ResendVerificationEmailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="testpass123"
        )
        self.url = reverse("resend_verification_email")
        self.profile_url = reverse("profile_page")
        self.verify_email_url = reverse("verify_email")

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        expected_url = f"{settings.LOGIN_URL}?next={self.url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )

    def test_redirects_to_profile_if_email_already_verified(self):
        Profile.objects.create(
            user=self.user,
            full_name="Reader",
            is_email_verified=True
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.profile_url,
            fetch_redirect_response=False,
        )

        self.assertEqual(EmailVerificationCode.objects.count(), 0)

    @patch("users.views.send_verification_email")
    @patch("users.views.generate_verification_code")
    def test_creates_profile_invalidates_old_codes_creates_new_code_and_sends_email(
        self,
        mock_generate_verification_code,
        mock_send_verification_email
    ):
        mock_generate_verification_code.return_value = "123456"

        old_code_1 = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash="old_hash_1",
            is_used=False
        )
        old_code_2 = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash="old_hash_2",
            is_used=False
        )
        used_code = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash="used_hash",
            is_used=True
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.verify_email_url,
            fetch_redirect_response=False,
        )

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, self.user.username)
        self.assertFalse(profile.is_email_verified)

        old_code_1.refresh_from_db()
        old_code_2.refresh_from_db()
        used_code.refresh_from_db()

        self.assertTrue(old_code_1.is_used)
        self.assertTrue(old_code_2.is_used)
        self.assertTrue(used_code.is_used)

        self.assertEqual(
            EmailVerificationCode.objects.filter(
                user=self.user,
                email=self.user.email
            ).count(),
            4
        )

        new_code = EmailVerificationCode.objects.filter(
            user=self.user,
            email=self.user.email
        ).latest("id")

        self.assertEqual(new_code.user, self.user)
        self.assertEqual(new_code.email, self.user.email)
        self.assertFalse(new_code.is_used)
        self.assertNotEqual(new_code.code_hash, "123456")

        mock_generate_verification_code.assert_called_once_with()
        mock_send_verification_email.assert_called_once_with(
            self.user,
            "123456"
        )

    @patch("users.views.send_verification_email")
    @patch("users.views.generate_verification_code")
    def test_invalidates_only_current_users_current_email_unused_codes(
        self,
        mock_generate_verification_code,
        mock_send_verification_email
    ):
        mock_generate_verification_code.return_value = "654321"

        other_user = User.objects.create_user(
            username="other_reader",
            email="other@example.com",
            password="testpass123"
        )

        Profile.objects.create(
            user=self.user,
            full_name="Reader"
        )

        current_email_code = EmailVerificationCode.objects.create(
            user=self.user,
            email=self.user.email,
            code_hash="hash_current",
            is_used=False
        )
        other_email_code = EmailVerificationCode.objects.create(
            user=self.user,
            email="old@example.com",
            code_hash="hash_old_email",
            is_used=False
        )
        other_user_code = EmailVerificationCode.objects.create(
            user=other_user,
            email=other_user.email,
            code_hash="hash_other_user",
            is_used=False
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.verify_email_url,
            fetch_redirect_response=False,
        )

        current_email_code.refresh_from_db()
        other_email_code.refresh_from_db()
        other_user_code.refresh_from_db()

        self.assertTrue(current_email_code.is_used)
        self.assertFalse(other_email_code.is_used)
        self.assertFalse(other_user_code.is_used)

        self.assertEqual(
            EmailVerificationCode.objects.filter(
                user=self.user,
                email=self.user.email
            ).count(),
            2
        )

        mock_generate_verification_code.assert_called_once_with()
        mock_send_verification_email.assert_called_once_with(
            self.user,
            "654321"
            )