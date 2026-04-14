from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from catalog.models import Book
from review_rating.models import Review


class reviewmodelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="`",
            password="testpass123"
        )

        self.book = Book.objects.create(
            title="Война и мир",
            slug="voyna-i-mir",
            isbn="1234567890999",
            price=Decimal("500.00"),
        )
        
    def test_correct_user_and_book(self):
        review = Review.objects.create(
            user=self.user,
            book=self.book,
            rating=5,
            text="Отлично",
        )

        self.assertEqual(review.user, self.user)
        self.assertEqual(review.book, self.book)
        
