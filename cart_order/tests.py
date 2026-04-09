from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from catalog.models import Book
from cart_order.models import Cart, CartItem, Order, OrderItem


class cartmodelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex",
            password="testpass123"
        )

    def test_str_cart_id_and_username(self):
        cart = Cart.objects.create(user=self.user)

        self.assertEqual(str(cart), f"Корзина #{cart.id} - alex")


class cartitemmodelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex",
            password="testpass123"
        )
        self.cart = Cart.objects.create(user=self.user)
        self.book = Book.objects.create(
            title="Дюна",
            slug="duna",
            isbn="1234567890126",
            price=Decimal("800.00"),
        )

    def test_cart_item_str_book_and_quantity(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            book=self.book,
            quantity=2,
            price_at_time=Decimal("800.00"),
        )

        self.assertEqual(str(cart_item), "Дюна x 2")


class ordermodelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex",
            password="testpass123"
        )

    def test_str_order_id_and_username(self):
        order = Order.objects.create(
            user=self.user,
            status="new",
            delivery_method="courier",
            payment_method="card",
            payment_status="pending",
            total_price=Decimal("1200.00"),
            delivery_address="Москва, ул. Пушкина, д. 1",
        )

        self.assertEqual(str(order), f"Заказ #{order.id} - alex")


class OrderItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex",
            password="testpass123"
        )
        self.book = Book.objects.create(
            title="Онегин",
            slug="onegin",
            isbn="1234567890127",
            price=Decimal("650.00"),
        )
        self.order = Order.objects.create(
            user=self.user,
            status="new",
            delivery_method="pickup",
            payment_method="cash",
            payment_status="pending",
            total_price=Decimal("650.00"),
            delivery_address="Минск, ул. Ленина, д. 10",
        )

    def test_order_item_str_book_and_quantity(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            book=self.book,
            quantity=3,
            price_at_time=Decimal("650.00"),
        )

        self.assertEqual(str(order_item), "Онегин x 3")
