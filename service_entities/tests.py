from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from catalog.models import Book
from cart_order.models import Order
from service_entities.models import Payment, OrderStatusHistory, SupportMessage, BookFileAccess


class ServiceEntitiesModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex",
            password="testpass12345A!"
        )

        self.book = Book.objects.create(
            title="Дюна",
            slug="duna-service",
            isbn="1234567890999",
            price=Decimal("800.00"),
            is_active=True,
        )

        self.order = Order.objects.create(
            user=self.user,
            status="new",
            delivery_method="courier",
            payment_method="card",
            payment_status="pending",
            total_price=Decimal("800.00"),
            delivery_address="Москва, ул. Пушкина, д. 1",
        )

    def test_payment_str_returns_payment_id_and_order_id(self):
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("800.00"),
            method="card",
            status="paid",
            transaction_id="txn_123456",
        )

        self.assertEqual(str(payment), f"Платёж #{payment.id} - заказ #{self.order.id}")

    def test_payment_created_at_is_set(self):
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("800.00"),
            method="card",
            status="paid",
            transaction_id="txn_123456",
        )

        self.assertIsNotNone(payment.created_at)

    def test_order_status_history_str_returns_status_transition(self):
        history = OrderStatusHistory.objects.create(
            order=self.order,
            old_status="new",
            new_status="processing",
            changed_by=self.user,
        )

        self.assertEqual(
            str(history),
            f"Заказ #{self.order.id}: new -> processing"
        )

    def test_order_status_history_changed_at_is_set(self):
        history = OrderStatusHistory.objects.create(
            order=self.order,
            old_status="new",
            new_status="processing",
            changed_by=self.user,
        )

        self.assertIsNotNone(history.changed_at)

    def test_support_message_str_returns_message_id_and_username(self):
        message = SupportMessage.objects.create(
            user=self.user,
            order=self.order,
            sender_role="user",
            text="Где мой заказ?",
        )

        self.assertEqual(str(message), f"Сообщение #{message.id} - alex")

    def test_support_message_created_at_is_set(self):
        message = SupportMessage.objects.create(
            user=self.user,
            order=self.order,
            sender_role="user",
            text="Нужна помощь",
        )

        self.assertIsNotNone(message.created_at)

    def test_book_file_access_str_returns_access_id_username_and_book(self):
        access = BookFileAccess.objects.create(
            user=self.user,
            book=self.book,
            order=self.order,
            access_granted_at=timezone.now(),
        )

        self.assertEqual(
            str(access),
            f"Доступ #{access.id} - alex - {self.book}"
        )

    def test_book_file_access_can_be_created_without_expires_at(self):
        access = BookFileAccess.objects.create(
            user=self.user,
            book=self.book,
            order=self.order,
            access_granted_at=timezone.now(),
        )

        self.assertIsNone(access.expires_at)

    def test_book_file_access_has_correct_relations(self):
        access = BookFileAccess.objects.create(
            user=self.user,
            book=self.book,
            order=self.order,
            access_granted_at=timezone.now(),
        )

        self.assertEqual(access.user, self.user)
        self.assertEqual(access.book, self.book)
        self.assertEqual(access.order, self.order)
        
    def test_payment_has_correct_order_relation(self):
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("800.00"),
            method="card",
            status="paid",
            transaction_id="txn_123456",
        )

        self.assertEqual(payment.order, self.order)
        
    def test_order_status_history_has_correct_relations(self):
        history = OrderStatusHistory.objects.create(
            order=self.order,
            old_status="new",
            new_status="processing",
            changed_by=self.user,
        )

        self.assertEqual(history.order, self.order)
        self.assertEqual(history.changed_by, self.user)
        
    def test_support_message_has_correct_relations(self):
        message = SupportMessage.objects.create(
            user=self.user,
            order=self.order,
            sender_role="user",
            text="Где мой заказ?",
        )

        self.assertEqual(message.user, self.user)
        self.assertEqual(message.order, self.order)