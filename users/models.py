from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Role(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Название роли"
    )

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь"
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Полное имя"
    )
    delivery_address = models.TextField(
        blank=True, # поле можно оставить пустым
        verbose_name="Адрес доставки"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Город"
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Почтовый индекс"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        verbose_name="Роль"
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return self.full_name
    
class PasswordResetCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"Reset code for {self.user}"