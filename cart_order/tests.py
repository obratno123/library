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