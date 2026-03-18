from django.db import models
from django.contrib.auth.models import User


class Cart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name="Пользователь"
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
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина #{self.id} - {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Корзина"
    )
    book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="Книга"
    )
    quantity = models.IntegerField(
        verbose_name="Количество"
    )
    price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена на момент добавления"
    )

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"

    def __str__(self):
        return f"{self.book} x {self.quantity}"


class Order(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Пользователь"
    )
    status = models.CharField(
        max_length=50,
        verbose_name="Статус заказа"
    )
    delivery_method = models.CharField(
        max_length=50,
        verbose_name="Способ доставки"
    )
    payment_method = models.CharField(
        max_length=50,
        verbose_name="Способ оплаты"
    )
    payment_status = models.CharField(
        max_length=50,
        verbose_name="Статус оплаты"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Общая стоимость"
    )
    delivery_address = models.TextField(
        verbose_name="Адрес доставки"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    qr_code = models.ImageField(
        upload_to="orders/qr_codes/",
        blank=True,
        null=True,
        verbose_name="QR-код"
    )
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата оплаты"
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"Заказ #{self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ"
    )
    book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.CASCADE,
        related_name="order_items",
        verbose_name="Книга"
    )
    quantity = models.IntegerField(
        verbose_name="Количество"
    )
    price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена на момент заказа"
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.book} x {self.quantity}"