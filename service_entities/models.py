from django.db import models
from django.contrib.auth.models import User


class Payment(models.Model):
    order = models.ForeignKey(
        "cart_order.Order",
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Заказ"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма"
    )
    method = models.CharField(
        max_length=50,
        verbose_name="Метод оплаты"
    )
    status = models.CharField(
        max_length=50,
        verbose_name="Статус платежа"
    )
    transaction_id = models.CharField(
        max_length=255,
        verbose_name="ID транзакции"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"

    def __str__(self):
        return f"Платёж #{self.id} - заказ #{self.order.id}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        "cart_order.Order",
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name="Заказ"
    )
    old_status = models.CharField(
        max_length=50,
        verbose_name="Старый статус"
    )
    new_status = models.CharField(
        max_length=50,
        verbose_name="Новый статус"
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="changed_order_statuses",
        verbose_name="Кто изменил"
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата изменения"
    )

    class Meta:
        verbose_name = "История статусов заказа"
        verbose_name_plural = "История статусов заказов"

    def __str__(self):
        return f"Заказ #{self.order.id}: {self.old_status} -> {self.new_status}"


class SupportMessage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="support_messages",
        verbose_name="Пользователь"
    )
    order = models.ForeignKey(
        "cart_order.Order",
        on_delete=models.CASCADE,
        related_name="support_messages",
        verbose_name="Заказ"
    )
    sender_role = models.CharField(
        max_length=50,
        verbose_name="Роль отправителя"
    )
    text = models.TextField(
        verbose_name="Текст сообщения"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Сообщение поддержки"
        verbose_name_plural = "Сообщения поддержки"

    def __str__(self):
        return f"Сообщение #{self.id} - {self.user.username}"


class BookFileAccess(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="book_file_accesses",
        verbose_name="Пользователь"
    )
    book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.CASCADE,
        related_name="file_accesses",
        verbose_name="Книга"
    )
    order = models.ForeignKey(
        "cart_order.Order",
        on_delete=models.CASCADE,
        related_name="book_file_accesses",
        verbose_name="Заказ"
    )
    access_granted_at = models.DateTimeField(
        verbose_name="Дата выдачи доступа"
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата окончания доступа"
    )

    class Meta:
        verbose_name = "Доступ к файлу книги"
        verbose_name_plural = "Доступы к файлам книг"

    def __str__(self):
        return f"Доступ #{self.id} - {self.user.username} - {self.book}"