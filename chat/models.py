from django.db import models
from django.contrib.auth.models import User


class Dialog(models.Model):
    user1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dialogs_as_user1",
        verbose_name="Пользователь 1"
    )
    user2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dialogs_as_user2",
        verbose_name="Пользователь 2"
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
        verbose_name = "Диалог"
        verbose_name_plural = "Диалоги"

    def __str__(self):
        return f"{self.user1.username} ↔ {self.user2.username}"

    def get_other_user(self, current_user):
        return self.user2 if self.user1 == current_user else self.user1


class Message(models.Model):
    dialog = models.ForeignKey(
        Dialog,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Диалог"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name="Отправитель"
    )
    text = models.TextField(
        verbose_name="Текст"
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