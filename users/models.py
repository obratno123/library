from django.db import models
from django.contrib.auth.models import User


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