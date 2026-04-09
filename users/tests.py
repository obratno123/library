from django.test import TestCase
from django.contrib.auth.models import User

from users.models import Role, Profile


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