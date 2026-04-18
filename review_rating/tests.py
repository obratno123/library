from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from catalog.models import Author, Book, Genre, Publisher
from config import settings
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
        
    def test_review_str_returns_correct_string(self):
        user = User.objects.create_user(
            username="reader",
            password="testpass123"
        )

        publisher = Publisher.objects.create(name="Test Publisher")
        genre = Genre.objects.create(name="Fantasy", slug="fantasy-review-str")
        author = Author.objects.create(
            first_name="John",
            last_name="Smith"
        )

        book = Book.objects.create(
            title="Test Book",
            slug="test-book-review-str",
            description="Test description",
            isbn="isbn-review-str",
            price=Decimal("100.00"),
            publisher=publisher,
            is_active=True,
        )
        book.authors.add(author)
        book.genres.add(genre)

        review = Review.objects.create(
            user=user,
            book=book,
            rating=5,
            text="Great book"
        )

        self.assertEqual(str(review), "Отзыв reader на Test Book")
        
    def test_review_stars_range_returns_range_by_rating(self):
        user = User.objects.create_user(
            username="reader2",
            password="testpass123"
        )

        publisher = Publisher.objects.create(name="Test Publisher")
        genre = Genre.objects.create(name="Fantasy", slug="fantasy-review-stars")
        author = Author.objects.create(
            first_name="Jane",
            last_name="Smith"
        )

        book = Book.objects.create(
            title="Stars Book",
            slug="stars-book-review",
            description="Test description",
            isbn="isbn-review-stars",
            price=Decimal("120.00"),
            publisher=publisher,
            is_active=True,
        )
        book.authors.add(author)
        book.genres.add(genre)

        review = Review.objects.create(
            user=user,
            book=book,
            rating=4,
            text="Nice book"
        )

        self.assertEqual(list(review.stars_range), [0, 1, 2, 3])
        
        
class AddOrEditReviewViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            password="testpass123"
        )
        self.book = Book.objects.create(
            title="Review Book",
            slug="review-book",
            isbn="isbn-review-book",
            price=Decimal("100.00"),
            is_active=True,
        )
        self.url = reverse(
            "review_rating:add_or_edit_review",
            kwargs={"slug": self.book.slug}
        )
        self.detail_url = reverse(
            "catalog:book_detail",
            kwargs={"slug": self.book.slug}
        )

    def test_add_or_edit_review_redirects_anonymous_user_to_login(self):
        response = self.client.post(self.url, {
            "rating": "5",
            "text": "Great book",
        })

        expected_url = f"{settings.LOGIN_URL}?next={self.url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )

    def test_add_or_edit_review_get_redirects_to_book_detail(self):
        self.client.login(username="reader", password="testpass123")

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.detail_url,
            fetch_redirect_response=False,
        )
        self.assertEqual(Review.objects.count(), 0)

    def test_add_or_edit_review_returns_error_if_rating_missing(self):
        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "text": "Great book",
        }, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Review.objects.count(), 0)

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Укажите оценку.")

    def test_add_or_edit_review_returns_error_if_rating_is_not_integer(self):
        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "rating": "abc",
            "text": "Great book",
        }, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Review.objects.count(), 0)

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Некорректная оценка.")

    def test_add_or_edit_review_returns_error_if_rating_out_of_range(self):
        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "rating": "6",
            "text": "Great book",
        }, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Review.objects.count(), 0)

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Оценка должна быть от 0 до 5.")

    def test_add_or_edit_review_returns_error_if_text_is_empty(self):
        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "rating": "5",
            "text": "   ",
        }, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Review.objects.count(), 0)

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Напишите текст отзыва.")

    def test_add_or_edit_review_creates_new_review(self):
        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "rating": "5",
            "text": "Great book",
        }, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.get()
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.book, self.book)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.text, "Great book")

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Отзыв сохранён.")

    def test_add_or_edit_review_updates_existing_review(self):
        Review.objects.create(
            user=self.user,
            book=self.book,
            rating=2,
            text="Old text"
        )

        self.client.login(username="reader", password="testpass123")

        response = self.client.post(self.url, {
            "rating": "4",
            "text": "New text",
        }, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.get()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.text, "New text")

        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Отзыв сохранён.")
        
        
class UserReviewsTest(TestCase):
    def test_user_reviews_redirects_anonymous_user_to_login(self):
        url = reverse("review_rating:user_reviews")

        response = self.client.get(url)

        expected_url = f"{settings.LOGIN_URL}?next={url}"
        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )
        
    def test_user_reviews_shows_only_current_user_reviews(self):
        user = User.objects.create_user(
            username="reader",
            password="testpass123"
        )
        other_user = User.objects.create_user(
            username="other_reader",
            password="testpass123"
        )

        book1 = Book.objects.create(
            title="Book 1",
            slug="user-reviews-book-1",
            isbn="user-reviews-isbn-1",
            price=Decimal("100.00"),
            is_active=True,
        )
        book2 = Book.objects.create(
            title="Book 2",
            slug="user-reviews-book-2",
            isbn="user-reviews-isbn-2",
            price=Decimal("120.00"),
            is_active=True,
        )
        book3 = Book.objects.create(
            title="Book 3",
            slug="user-reviews-book-3",
            isbn="user-reviews-isbn-3",
            price=Decimal("130.00"),
            is_active=True,
        )

        review1 = Review.objects.create(
            user=user,
            book=book1,
            rating=5,
            text="My first review"
        )
        review2 = Review.objects.create(
            user=user,
            book=book2,
            rating=4,
            text="My second review"
        )
        Review.objects.create(
            user=other_user,
            book=book3,
            rating=3,
            text="Other user review"
        )

        self.client.login(username="reader", password="testpass123")
        response = self.client.get(reverse("review_rating:user_reviews"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user_reviews.html")

        reviews = list(response.context["reviews"])
        self.assertEqual(len(reviews), 2)
        self.assertIn(review1, reviews)
        self.assertIn(review2, reviews)

        for review in reviews:
            self.assertEqual(review.user, user)
            
    def test_user_reviews_orders_reviews_by_created_at_desc(self):
        from datetime import timedelta
        from django.utils import timezone

        user = User.objects.create_user(
            username="reader_order",
            password="testpass123"
        )

        book1 = Book.objects.create(
            title="Order Book 1",
            slug="order-book-1",
            isbn="order-isbn-1",
            price=Decimal("100.00"),
            is_active=True,
        )
        book2 = Book.objects.create(
            title="Order Book 2",
            slug="order-book-2",
            isbn="order-isbn-2",
            price=Decimal("150.00"),
            is_active=True,
        )

        old_review = Review.objects.create(
            user=user,
            book=book1,
            rating=4,
            text="Old review"
        )
        new_review = Review.objects.create(
            user=user,
            book=book2,
            rating=5,
            text="New review"
        )

        now = timezone.now()
        Review.objects.filter(id=old_review.id).update(created_at=now - timedelta(days=1))
        Review.objects.filter(id=new_review.id).update(created_at=now)

        self.client.login(username="reader_order", password="testpass123")
        response = self.client.get(reverse("review_rating:user_reviews"))

        self.assertEqual(response.status_code, 200)

        reviews = list(response.context["reviews"])
        self.assertEqual(reviews[0].id, new_review.id)
        self.assertEqual(reviews[1].id, old_review.id)