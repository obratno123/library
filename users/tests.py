from django.test import TestCase
from django.contrib.auth.models import User

from users.models import Role, Profile

import json
from django.urls import reverse
from unittest.mock import patch
from django.db import IntegrityError


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
        
    