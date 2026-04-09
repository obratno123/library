from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from catalog.models import Book
from cart_order.models import Cart, CartItem, Order, OrderItem

from django.urls import reverse



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


class cartviewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex",
            password="testpass12345A!"
        )
        self.book = Book.objects.create(
            title="Дюна",
            slug="duna",
            isbn="1234567890126",
            price=Decimal("800.00"),
            is_active=True,
        )

    def test_add_to_cart_creates_cart_and_item(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("cart_order:add_to_cart", args=[self.book.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("cart_order:cart_view"))

        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertTrue(CartItem.objects.filter(cart__user=self.user, book=self.book).exists())

        cart_item = CartItem.objects.get(cart__user=self.user, book=self.book)
        self.assertEqual(cart_item.quantity, 1)
        self.assertEqual(cart_item.price_at_time, self.book.price)
        
    def test_add_to_cart__quantity_items(self):
        self.client.force_login(self.user)

        self.client.post(reverse("cart_order:add_to_cart", args=[self.book.id]))
        self.client.post(reverse("cart_order:add_to_cart", args=[self.book.id]))

        self.assertEqual(
            CartItem.objects.filter(cart__user=self.user, book=self.book).count(),
            1
        )

        cart_item = CartItem.objects.get(cart__user=self.user, book=self.book)
        self.assertEqual(cart_item.quantity, 2)
        
    def test_add_to_cart_status_code_404_for_none_book(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("cart_order:add_to_cart", args=[99999])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_add_to_cart_returns_404_for_inactive_book(self):
        self.client.force_login(self.user)

        inactive_book = Book.objects.create(
            title="Скрытая книга",
            slug="hidden-book",
            isbn="1234567890998",
            price=Decimal("500.00"),
            is_active=False,
        )

        response = self.client.post(
            reverse("cart_order:add_to_cart", args=[inactive_book.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        self.assertFalse(CartItem.objects.filter(book=inactive_book).exists())
        
    def test_add_to_cart_redirects_unauthorized_user(self):
        response = self.client.post(
            reverse("cart_order:add_to_cart", args=[self.book.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        self.assertFalse(CartItem.objects.filter(cart__user=self.user, book=self.book).exists())
        
    def test_add_to_cart_get_method(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("cart_order:add_to_cart", args=[self.book.id])
        )

        self.assertEqual(response.status_code, 405)
