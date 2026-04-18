from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import RequestFactory, TestCase, override_settings
from django.contrib.auth.models import User

from cart_order.views import checkout_view
from catalog.models import Book
from cart_order.models import Cart, CartItem, Order, OrderItem
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from cart_order.views import stripe_webhook
import stripe

from django.urls import reverse
from cart_order import views as cart_views

from config import settings

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages import get_messages

from cart_order.views import create_checkout_session
from catalog.models import Book
from service_entities.models import BookFileAccess


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


class cartviewsaddTests(TestCase):
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
        
    def test_add_to_cart_quantity_items(self):
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


class cartviewupdateTests(TestCase):
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
    def test_update_cart_item_increase_quantity_plus_one(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)
        
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )
        response = self.client.post(
            reverse("cart_order:update_cart_item", args=[cart_item.id]),
            data={"action": "increase"}
            )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("cart_order:cart_view"))

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)
        
    def test_update_cart_item_decrease_quantity_minus_one(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)
        
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )
        response = self.client.post(
            reverse("cart_order:update_cart_item", args=[cart_item.id]),
            data={"action": "decrease"}
            )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("cart_order:cart_view"))

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)
        
    def test_update_cart_item_decrease_delete_item_by_quantity_zero(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)
        
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=1,
            price_at_time=self.book.price,
        )
        response = self.client.post(
            reverse("cart_order:update_cart_item", args=[cart_item.id]),
            data={"action": "decrease"}
            )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("cart_order:cart_view"))
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())
        
    def test_update_cart_item_status_code_400_for_invalid_action(self):
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        response = self.client.post(
            reverse("cart_order:update_cart_item", args=[cart_item.id]),
            data={"action": "unknown_action"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Некорректное действие", response.content.decode())

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        
    def test_update_cart_item_status_code_404_for_foreign_item(self):
        owner = User.objects.create_user(
            username="owner",
            password="testpass12345A!"
        )
        intruder = User.objects.create_user(
            username="intruder",
            password="testpass12345A!"
        )

        cart = Cart.objects.create(user=owner)
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        self.client.force_login(intruder)

        response = self.client.post(
            reverse("cart_order:update_cart_item", args=[cart_item.id]),
            data={"action": "increase"}
        )

        self.assertEqual(response.status_code, 404)

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        
    def test_update_cart_item_redirects_unauthorized_user(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        response = self.client.post(
            reverse("cart_order:update_cart_item", args=[cart_item.id]),
            data={"action": "increase"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        
    def test_update_cart_item_status_code_404_for_nonexistent_item(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("cart_order:update_cart_item", args=[99999]),
            data={"action": "increase"}
        )

        self.assertEqual(response.status_code, 404)


    def test_update_cart_item_get_method_status_code_405(self):
        self.client.force_login(self.user)

        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        response = self.client.get(
            reverse("cart_order:update_cart_item", args=[cart_item.id])
        )

        self.assertEqual(response.status_code, 405)

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        
        
class cartviewremoveTests(TestCase):
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

    def test_remove_cart_item_deletes_item(self):
        self.client.force_login(self.user)

        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        response = self.client.post(
            reverse("cart_order:remove_cart_item", args=[cart_item.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("cart_order:cart_view"))
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_remove_cart_item_status_code_404_for_foreign_item(self):
        owner = User.objects.create_user(
            username="owner",
            password="testpass12345A!"
        )
        intruder = User.objects.create_user(
            username="intruder",
            password="testpass12345A!"
        )

        cart = Cart.objects.create(user=owner)
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        self.client.force_login(intruder)

        response = self.client.post(
            reverse("cart_order:remove_cart_item", args=[cart_item.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(id=cart_item.id).exists())

    def test_remove_cart_item_redirects_unauthorized_user(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        response = self.client.post(
            reverse("cart_order:remove_cart_item", args=[cart_item.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)
        self.assertTrue(CartItem.objects.filter(id=cart_item.id).exists())

    def test_remove_cart_item_status_code_404_for_nonexistent_item(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("cart_order:remove_cart_item", args=[99999])
        )

        self.assertEqual(response.status_code, 404)

    def test_remove_cart_item_get_method_status_code_405(self):
        self.client.force_login(self.user)

        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=self.book.price,
        )

        response = self.client.get(
            reverse("cart_order:remove_cart_item", args=[cart_item.id])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(CartItem.objects.filter(id=cart_item.id).exists())
        

class cartviewcartviewTests(TestCase):
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

    def test_cart_view_redirects_unauthorized_user(self):
        response = self.client.get(reverse("cart_order:cart_view"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)
        
    def test_cart_view_post_method_status_code_405(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("cart_order:cart_view"))

        self.assertEqual(response.status_code, 405)

    def test_cart_view_creates_cart_for_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("cart_order:cart_view"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        
    def test_cart_view_returns_correct_totals(self):
        self.client.force_login(self.user)

        cart = Cart.objects.create(user=self.user)

        CartItem.objects.create(
            cart=cart,
            book=self.book,
            quantity=2,
            price_at_time=Decimal("800.00"),
        )

        second_book = Book.objects.create(
            title="Онегин",
            slug="onegin",
            isbn="1234567890999",
            price=Decimal("500.00"),
            is_active=True,
        )

        CartItem.objects.create(
            cart=cart,
            book=second_book,
            quantity=1,
            price_at_time=Decimal("500.00"),
        )

        response = self.client.get(reverse("cart_order:cart_view"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_items"], 3)
        self.assertEqual(response.context["subtotal"], Decimal("2100.00"))
        self.assertEqual(response.context["discount"], Decimal("0.00"))
        self.assertEqual(response.context["delivery_price"], Decimal("0.00"))
        self.assertEqual(response.context["total_price"], Decimal("2100.00"))
        
    def test_cart_view_with_empty_cart_zero_totals(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("cart_order:cart_view"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

        self.assertEqual(response.context["total_items"], 0)
        self.assertEqual(response.context["subtotal"], Decimal("0.00"))
        self.assertEqual(response.context["discount"], Decimal("0.00"))
        self.assertEqual(response.context["delivery_price"], Decimal("0.00"))
        self.assertEqual(response.context["total_price"], Decimal("0.00"))
        self.assertEqual(list(response.context["items"]), [])


@override_settings(STRIPE_PUBLISHABLE_KEY="pk_test_123")
class CheckoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self.url = reverse("cart_order:checkout")
        self.cart_url = reverse("cart_order:cart_view")
        self._book_counter = 0

    def _login(self):
        self.client.login(username="client", password="testpass123")

    def _create_book(self, title, price=Decimal("100.00")):
        self._book_counter += 1
        return Book.objects.create(
            title=title,
            slug=f"book-{self._book_counter}",
            isbn=f"isbn-{self._book_counter}",
            price=price,
        )

    def test_checkout_redirects_if_cart_is_empty(self):
        self._login()
        Cart.objects.create(user=self.user)

        response = self.client.get(self.url, follow=True)

        self.assertRedirects(response, self.cart_url)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Корзина пуста.")

    def test_checkout_creates_cart_if_it_does_not_exist(self):
        self._login()

        self.assertFalse(Cart.objects.filter(user=self.user).exists())

        response = self.client.get(self.url, follow=True)

        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertRedirects(response, self.cart_url)

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Корзина пуста.")

    def test_checkout_renders_checkout_page_with_correct_context(self):
        self._login()

        cart = Cart.objects.create(user=self.user)

        book1 = self._create_book("Book 1")
        book2 = self._create_book("Book 2")

        item1 = CartItem.objects.create(
            cart=cart,
            book=book1,
            quantity=2,
            price_at_time=Decimal("100.00")
        )
        item2 = CartItem.objects.create(
            cart=cart,
            book=book2,
            quantity=1,
            price_at_time=Decimal("50.00")
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "checkout.html")

        self.assertEqual(response.context["cart"], cart)

        items = list(response.context["items"])
        self.assertEqual(items, [item1, item2])

        self.assertEqual(response.context["subtotal"], Decimal("250.00"))
        self.assertEqual(response.context["delivery_price"], Decimal("0.00"))
        self.assertEqual(response.context["total_price"], Decimal("250.00"))
        self.assertEqual(response.context["stripe_publishable_key"], "pk_test_123")

    def test_checkout_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)

        expected_url = f"{settings.LOGIN_URL}?next={self.url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )


@override_settings(SITE_URL="https://example.com")
class CreateCheckoutSessionViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self.cart_url = reverse("cart_order:cart_view")
        self._book_counter = 0

    def _setup_request(self, request, user=None):
        request.user = user if user is not None else self.user
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        return request

    def _create_book(self, title="Test Book", price=Decimal("100.00")):
        self._book_counter += 1
        return Book.objects.create(
            title=title,
            slug=f"book-{self._book_counter}",
            isbn=f"isbn-{self._book_counter}",
            price=price,
        )

    def test_create_checkout_session_redirects_anonymous_user_to_login(self):
        request = self.factory.post("/fake-checkout-session/")
        request = self._setup_request(request, user=AnonymousUser())

        response = create_checkout_session(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response.url)

    def test_create_checkout_session_get_method_not_allowed(self):
        request = self.factory.get("/fake-checkout-session/")
        request = self._setup_request(request)

        response = create_checkout_session(request)

        self.assertEqual(response.status_code, 405)

    def test_create_checkout_session_redirects_if_cart_is_empty(self):
        request = self.factory.post("/fake-checkout-session/")
        request = self._setup_request(request)

        Cart.objects.create(user=self.user)

        response = create_checkout_session(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.cart_url)

        messages_list = list(get_messages(request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Корзина пуста.")

    @patch("cart_order.views.stripe.checkout.Session.create")
    def test_create_checkout_session_creates_order_items_payment_and_redirects_with_defaults(
        self,
        mock_stripe_create,
    ):
        request = self.factory.post("/fake-checkout-session/", data={})
        request = self._setup_request(request)

        cart = Cart.objects.create(user=self.user)

        book1 = self._create_book("Book 1", Decimal("100.00"))
        book2 = self._create_book("Book 2", Decimal("50.00"))

        CartItem.objects.create(
            cart=cart,
            book=book1,
            quantity=2,
            price_at_time=Decimal("100.00"),
        )
        CartItem.objects.create(
            cart=cart,
            book=book2,
            quantity=1,
            price_at_time=Decimal("50.00"),
        )

        session = MagicMock()
        session.id = "cs_test_123"
        session.url = "https://checkout.stripe.com/test-session"
        mock_stripe_create.return_value = session

        response = create_checkout_session(request)

        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.delivery_method, "digital")
        self.assertEqual(order.payment_method, "card")
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.total_price, Decimal("250.00"))
        self.assertEqual(order.delivery_address, "Электронная доставка")

        order_items = list(order.items.order_by("id"))
        self.assertEqual(len(order_items), 2)

        self.assertEqual(order_items[0].book, book1)
        self.assertEqual(order_items[0].quantity, 2)
        self.assertEqual(order_items[0].price_at_time, Decimal("100.00"))

        self.assertEqual(order_items[1].book, book2)
        self.assertEqual(order_items[1].quantity, 1)
        self.assertEqual(order_items[1].price_at_time, Decimal("50.00"))

        self.assertEqual(order.payments.count(), 1)
        payment = order.payments.get()
        self.assertEqual(payment.amount, Decimal("250.00"))
        self.assertEqual(payment.method, "card")
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.transaction_id, "cs_test_123")

        mock_stripe_create.assert_called_once_with(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "rub",
                        "product_data": {
                            "name": "Book 1",
                        },
                        "unit_amount": 10000,
                    },
                    "quantity": 2,
                },
                {
                    "price_data": {
                        "currency": "rub",
                        "product_data": {
                            "name": "Book 2",
                        },
                        "unit_amount": 5000,
                    },
                    "quantity": 1,
                },
            ],
            success_url=f"https://example.com/cart/order/{order.id}/success/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://example.com/cart/checkout/",
            client_reference_id=str(order.id),
            metadata={
                "order_id": str(order.id),
                "user_id": str(self.user.id),
                "payment_method": "card",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://checkout.stripe.com/test-session")

    @patch("cart_order.views.stripe.checkout.Session.create")
    def test_create_checkout_session_uses_posted_delivery_payment_and_address(
        self,
        mock_stripe_create,
    ):
        request = self.factory.post(
            "/fake-checkout-session/",
            data={
                "delivery_method": "courier",
                "payment_method": "cash",
                "delivery_address": "  Москва, ул. Пушкина  ",
            },
        )
        request = self._setup_request(request)

        cart = Cart.objects.create(user=self.user)
        book = self._create_book("Book A", Decimal("10.00"))

        CartItem.objects.create(
            cart=cart,
            book=book,
            quantity=3,
            price_at_time=Decimal("10.00"),
        )

        session = MagicMock()
        session.id = "cs_test_999"
        session.url = "https://checkout.stripe.com/another-session"
        mock_stripe_create.return_value = session

        response = create_checkout_session(request)

        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.delivery_method, "courier")
        self.assertEqual(order.payment_method, "cash")
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.total_price, Decimal("30.00"))
        self.assertEqual(order.delivery_address, "Москва, ул. Пушкина")

        order_items = list(order.items.order_by("id"))
        self.assertEqual(len(order_items), 1)
        self.assertEqual(order_items[0].book, book)
        self.assertEqual(order_items[0].quantity, 3)
        self.assertEqual(order_items[0].price_at_time, Decimal("10.00"))

        self.assertEqual(order.payments.count(), 1)
        payment = order.payments.get()
        self.assertEqual(payment.amount, Decimal("30.00"))
        self.assertEqual(payment.method, "cash")
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.transaction_id, "cs_test_999")

        mock_stripe_create.assert_called_once_with(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "rub",
                        "product_data": {
                            "name": "Book A",
                        },
                        "unit_amount": 1000,
                    },
                    "quantity": 3,
                }
            ],
            success_url=f"https://example.com/cart/order/{order.id}/success/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://example.com/cart/checkout/",
            client_reference_id=str(order.id),
            metadata={
                "order_id": str(order.id),
                "user_id": str(self.user.id),
                "payment_method": "cash",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://checkout.stripe.com/another-session")

    @patch("cart_order.views.stripe.checkout.Session.create")
    def test_create_checkout_session_uses_default_digital_address_if_posted_address_is_blank(
        self,
        mock_stripe_create,
    ):
        request = self.factory.post(
            "/fake-checkout-session/",
            data={
                "delivery_method": "pickup",
                "payment_method": "card",
                "delivery_address": "   ",
            },
        )
        request = self._setup_request(request)

        cart = Cart.objects.create(user=self.user)
        book = self._create_book("Book Z", Decimal("15.00"))

        CartItem.objects.create(
            cart=cart,
            book=book,
            quantity=1,
            price_at_time=Decimal("15.00"),
        )

        session = MagicMock()
        session.id = "cs_blank"
        session.url = "https://checkout.stripe.com/blank"
        mock_stripe_create.return_value = session

        response = create_checkout_session(request)

        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.delivery_method, "pickup")
        self.assertEqual(order.payment_method, "card")
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.total_price, Decimal("15.00"))
        self.assertEqual(order.delivery_address, "Электронная доставка")

        order_items = list(order.items.order_by("id"))
        self.assertEqual(len(order_items), 1)
        self.assertEqual(order_items[0].book, book)
        self.assertEqual(order_items[0].quantity, 1)
        self.assertEqual(order_items[0].price_at_time, Decimal("15.00"))

        self.assertEqual(order.payments.count(), 1)
        payment = order.payments.get()
        self.assertEqual(payment.amount, Decimal("15.00"))
        self.assertEqual(payment.method, "card")
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.transaction_id, "cs_blank")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://checkout.stripe.com/blank")

    @patch("cart_order.views.stripe.checkout.Session.create", side_effect=Exception("stripe failed"))
    def test_create_checkout_session_rolls_back_if_stripe_fails(
        self,
        mock_stripe_create,
    ):
        request = self.factory.post("/fake-checkout-session/", data={})
        request = self._setup_request(request)

        cart = Cart.objects.create(user=self.user)
        book = self._create_book("Book fail", Decimal("20.00"))

        CartItem.objects.create(
            cart=cart,
            book=book,
            quantity=1,
            price_at_time=Decimal("20.00"),
        )

        with self.assertRaises(Exception) as context:
            create_checkout_session(request)

        self.assertEqual(str(context.exception), "stripe failed")
        self.assertEqual(Order.objects.count(), 0)
        mock_stripe_create.assert_called_once()
        
        
class OrderSuccessViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="testpass123"
        )
        self._book_counter = 0

    def _create_book(self, title="Test Book", price=Decimal("100.00")):
        self._book_counter += 1
        return Book.objects.create(
            title=title,
            slug=f"book-{self._book_counter}",
            isbn=f"isbn-{self._book_counter}",
            price=price,
        )

    def _create_order(self, user):
        return Order.objects.create(
            user=user,
            status="paid",
            delivery_method="digital",
            payment_method="card",
            payment_status="paid",
            total_price=Decimal("100.00"),
            delivery_address="Электронная доставка",
        )

    def test_order_success_redirects_anonymous_user_to_login(self):
        order = self._create_order(self.user)
        url = reverse("cart_order:order_success", kwargs={"order_id": order.id})

        response = self.client.get(url)

        expected_url = f"{settings.LOGIN_URL}?next={url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )

    def test_order_success_returns_200_for_order_owner(self):
        self.client.login(username="client", password="testpass123")
        order = self._create_order(self.user)
        url = reverse("cart_order:order_success", kwargs={"order_id": order.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "order_success.html")
        self.assertEqual(response.context["order"], order)

    def test_order_success_returns_404_for_other_user_order(self):
        self.client.login(username="other", password="testpass123")
        order = self._create_order(self.user)
        url = reverse("cart_order:order_success", kwargs={"order_id": order.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_order_success_returns_404_if_order_does_not_exist(self):
        self.client.login(username="client", password="testpass123")
        url = reverse("cart_order:order_success", kwargs={"order_id": 99999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        
    def test_order_success_with_order_items(self):
        self.client.login(username="client", password="testpass123")
        order = self._create_order(self.user)
        book = self._create_book("Book 1", Decimal("100.00"))

        OrderItem.objects.create(
            order=order,
            book=book,
            quantity=1,
            price_at_time=Decimal("100.00"),
        )

        url = reverse("cart_order:order_success", kwargs={"order_id": order.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["order"], order)
        
        
@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
class StripeWebhookViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="client",
            password="testpass123"
        )
        self._book_counter = 0

    def _make_request(self, payload=b"{}", signature="test_signature"):
        return self.factory.generic(
            "POST",
            "/stripe/webhook/",
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature,
        )

    def _create_book(self, title="Test Book", price=Decimal("100.00"), ebook=False):
        self._book_counter += 1
        return Book.objects.create(
            title=title,
            slug=f"book-{self._book_counter}",
            isbn=f"isbn-{self._book_counter}",
            price=price,
            ebook_file="ebooks/test.pdf" if ebook else None,
        )

    def _create_order(
        self,
        user=None,
        status="pending",
        payment_status="pending",
        total_price=Decimal("100.00"),
        delivery_method="digital",
        payment_method="card",
        delivery_address="Электронная доставка",
    ):
        return Order.objects.create(
            user=user or self.user,
            status=status,
            delivery_method=delivery_method,
            payment_method=payment_method,
            payment_status=payment_status,
            total_price=total_price,
            delivery_address=delivery_address,
        )

    def _create_payment(self, order, transaction_id="cs_test_123", status="pending", amount=None, method="card"):
        return cart_views.Payment.objects.create(
            order=order,
            amount=amount if amount is not None else order.total_price,
            method=method,
            status=status,
            transaction_id=transaction_id,
        )

    @patch("cart_order.views.stripe.Webhook.construct_event", side_effect=ValueError("bad payload"))
    def test_stripe_webhook_returns_400_for_invalid_payload(self, mock_construct_event):
        request = self._make_request(payload=b"invalid")

        response = stripe_webhook(request)

        self.assertEqual(response.status_code, 400)
        mock_construct_event.assert_called_once_with(
            request.body,
            "test_signature",
            "whsec_test",
        )

    @patch(
        "cart_order.views.stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError("bad signature", "test_signature"),
    )
    def test_stripe_webhook_returns_400_for_invalid_signature(self, mock_construct_event):
        request = self._make_request()

        response = stripe_webhook(request)

        self.assertEqual(response.status_code, 400)
        mock_construct_event.assert_called_once_with(
            request.body,
            "test_signature",
            "whsec_test",
        )

    @patch("cart_order.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_ignores_unrelated_event_type(self, mock_construct_event):
        order = self._create_order()
        self._create_payment(order, transaction_id="cs_other")

        mock_construct_event.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "cs_other",
                    "metadata": {"order_id": str(order.id)},
                    "client_reference_id": str(order.id),
                }
            },
        }

        request = self._make_request()
        response = stripe_webhook(request)

        order.refresh_from_db()
        payment = order.payments.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.payment_status, "pending")
        self.assertIsNone(order.paid_at)
        self.assertEqual(payment.status, "pending")

    @patch("cart_order.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_returns_200_if_order_id_is_missing(self, mock_construct_event):
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "metadata": {},
                    "client_reference_id": "",
                }
            },
        }

        request = self._make_request()
        response = stripe_webhook(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    @patch("cart_order.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_returns_200_if_order_does_not_exist(self, mock_construct_event):
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "metadata": {"order_id": "999999"},
                    "client_reference_id": "",
                }
            },
        }

        request = self._make_request()
        response = stripe_webhook(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    @patch("cart_order.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_marks_order_paid_updates_payment_grants_ebook_access_and_clears_cart(
        self,
        mock_construct_event,
    ):
        cart = Cart.objects.create(user=self.user)

        ebook_book = self._create_book("Ebook Book", Decimal("100.00"), ebook=True)
        regular_book = self._create_book("Regular Book", Decimal("50.00"), ebook=False)

        CartItem.objects.create(
            cart=cart,
            book=ebook_book,
            quantity=2,
            price_at_time=Decimal("100.00"),
        )
        CartItem.objects.create(
            cart=cart,
            book=regular_book,
            quantity=1,
            price_at_time=Decimal("50.00"),
        )

        order = self._create_order(total_price=Decimal("250.00"))
        OrderItem.objects.create(
            order=order,
            book=ebook_book,
            quantity=2,
            price_at_time=Decimal("100.00"),
        )
        OrderItem.objects.create(
            order=order,
            book=regular_book,
            quantity=1,
            price_at_time=Decimal("50.00"),
        )

        payment = self._create_payment(
            order,
            transaction_id="cs_test_123",
            status="pending",
            amount=Decimal("250.00"),
            method="card",
        )

        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "metadata": {"order_id": str(order.id)},
                    "client_reference_id": "",
                }
            },
        }

        request = self._make_request()

        before_call = timezone.now()

        response = stripe_webhook(request)

        after_call = timezone.now()

        order.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "paid")
        self.assertIsNotNone(order.paid_at)
        self.assertGreaterEqual(order.paid_at, before_call)
        self.assertLessEqual(order.paid_at, after_call)

        self.assertEqual(payment.status, "paid")

        accesses = BookFileAccess.objects.filter(order=order)
        self.assertEqual(accesses.count(), 1)

        access = accesses.get()
        self.assertEqual(access.user, self.user)
        self.assertEqual(access.book, ebook_book)
        self.assertEqual(access.order, order)
        self.assertIsNotNone(access.access_granted_at)
        self.assertIsNone(access.expires_at)

        self.assertFalse(
            BookFileAccess.objects.filter(
                order=order,
                book=regular_book,
            ).exists()
        )

        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)

    @patch("cart_order.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_uses_client_reference_id_if_metadata_has_no_order_id(
        self,
        mock_construct_event,
    ):
        order = self._create_order(total_price=Decimal("30.00"))
        book = self._create_book("Fallback Book", Decimal("30.00"), ebook=False)

        OrderItem.objects.create(
            order=order,
            book=book,
            quantity=1,
            price_at_time=Decimal("30.00"),
        )
        payment = self._create_payment(
            order,
            transaction_id="cs_fallback",
            status="pending",
            amount=Decimal("30.00"),
            method="cash",
        )

        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_fallback",
                    "metadata": {},
                    "client_reference_id": str(order.id),
                }
            },
        }

        request = self._make_request()

        before_call = timezone.now()

        response = stripe_webhook(request)

        after_call = timezone.now()

        order.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "paid")
        self.assertIsNotNone(order.paid_at)
        self.assertGreaterEqual(order.paid_at, before_call)
        self.assertLessEqual(order.paid_at, after_call)
        self.assertEqual(payment.status, "paid")

    @patch("cart_order.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_does_nothing_for_already_paid_order(self, mock_construct_event):
        paid_at = timezone.now()

        cart = Cart.objects.create(user=self.user)
        book = self._create_book("Paid Book", Decimal("20.00"), ebook=True)

        CartItem.objects.create(
            cart=cart,
            book=book,
            quantity=1,
            price_at_time=Decimal("20.00"),
        )

        order = self._create_order(
            status="paid",
            payment_status="paid",
            total_price=Decimal("20.00"),
        )
        order.paid_at = paid_at
        order.save(update_fields=["paid_at"])

        OrderItem.objects.create(
            order=order,
            book=book,
            quantity=1,
            price_at_time=Decimal("20.00"),
        )

        payment = self._create_payment(
            order,
            transaction_id="cs_paid",
            status="pending",
            amount=Decimal("20.00"),
            method="card",
        )

        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_paid",
                    "metadata": {"order_id": str(order.id)},
                    "client_reference_id": "",
                }
            },
        }

        request = self._make_request()
        response = stripe_webhook(request)

        order.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "paid")
        self.assertEqual(order.paid_at, paid_at)
        self.assertEqual(payment.status, "pending")
        self.assertEqual(cart_views.BookFileAccess.objects.count(), 0)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 1)