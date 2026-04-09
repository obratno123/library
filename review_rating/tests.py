from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from catalog.models import Book
from review_rating.models import Review


class reviewmodelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ivan",
            password="testpass123"
        )

        self.book = Book.objects.create(
            title="Война и мир",
            slug="voyna-i-mir",
            isbn="1234567890999",
            price=Decimal("500.00"),
        )

    def test_str__review_id_and_username(self):
        review = Review.objects.create(
            user=self.user,
            book=self.book,
            rating=5,
            text="Очень хорошая книга",
        )
        
        self.assertEqual(str(review), f"Отзыв #{review.id} - ivan")
        
    def test_correct_user_and_book(self):
        review = Review.objects.create(
            user=self.user,
            book=self.book,
            rating=5,
            text="Отлично",
        )

        self.assertEqual(review.user, self.user)
        self.assertEqual(review.book, self.book)
        
    def test_review_is_published_true(self): ### можно удалить
        review = Review.objects.create(
            user=self.user,
            book=self.book,
            rating=4,
            text="Нормально",
        )

        self.assertTrue(review.is_published)
