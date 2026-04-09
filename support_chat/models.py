from django.db import models
from django.contrib.auth.models import User


class SupportDialog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="support_dialogs",
        verbose_name="Пользователь"
    )
    support_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="handled_support_dialogs",
        verbose_name="Оператор"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Диалог с поддержкой"
        verbose_name_plural = "Диалоги с поддержкой"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "support_user"],
                name="unique_user_support_dialog"
            )
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.support_user.username}"


class SupportMessage(models.Model):
    dialog = models.ForeignKey(
        SupportDialog,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Диалог"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_support_messages",
        verbose_name="Отправитель"
    )
    text = models.TextField(
        verbose_name="Текст сообщения"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата отправки"
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="Прочитано"
    )

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.text[:30]}"