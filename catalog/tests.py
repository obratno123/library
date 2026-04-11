from decimal import Decimal
from django.test import TestCase

from catalog.models import Book, Stock, Author, Genre, Publisher

from django.urls import reverse

class stockmodelsTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Мастер и Маргарита",
            slug="master-i-margarita",
            isbn="1234567890123",
            price=Decimal("499.00"),)
        
    def test_available_books(self):
        stock = Stock.objects.create(
            book=self.book,
            quantity=10,
            reserved_quantity=3
        )
        
        self.assertEqual(stock.available(), 7)
    
    def test_available_books_zero(self):
        stock = Stock.objects.create(
            book=self.book,
            quantity=5,
            reserved_quantity=5
        )

        self.assertEqual(stock.available(), 0)
        
    def test_stock_str_contains_book_title_and_available_quantity(self):
        book = Book.objects.create(
            title="1984",
            slug="1984",
            isbn="1234567890125",
            price=Decimal("400.00"),
        )
        stock = Stock.objects.create(
            book=book,
            quantity=12,
            reserved_quantity=2,
        )

        self.assertEqual(str(stock), "1984 (10 доступно)")
    
class authormodelTests(TestCase):
    
    def test_author_last_name_and_first_name(self):
        author = Author.objects.create(
            first_name="Михаил",
            last_name="Булгаков"
        )

        self.assertEqual(str(author), "Булгаков Михаил")


class genremodelTests(TestCase):
    def test_genre_str_name(self):
        genre = Genre.objects.create(
            name="Роман",
            slug="roman",
        )

        self.assertEqual(str(genre), "Роман")
        
        
class publishermodelTests(TestCase):
    def test_publisher_name(self):
        publisher = Publisher.objects.create(
            name = "АСТ"
        )
        
        self.assertEqual(str(publisher), "АСТ")
        
class bookmodelTests(TestCase):
    def test_book_str_returns_title(self):
        book = Book.objects.create(
            title="Преступление и наказание",
            slug="prestuplenie-i-nakazanie",
            isbn="1234567890124",
            price=Decimal("350.00"),
        )

        self.assertEqual(str(book), "Преступление и наказание")
        

class BookReaderViewTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Дюна",
            slug="duna",
            isbn="1234567890126",
            price=Decimal("800.00"),
            is_active=True,
        )
    
    def test_book_reader_view_returns_200_with_correct_context(self):
        author1 = Author.objects.create(first_name="Фрэнк", last_name="Герберт")
        author2 = Author.objects.create(first_name="Иван", last_name="Иванов")
        self.book.authors.add(author1, author2)

        response = self.client.get(
            reverse("catalog:book_reader", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["book"], self.book)
        self.assertEqual(
            response.context["authors"],
            "Фрэнк Герберт, Иван Иванов"
        )
        self.assertFalse(response.context["has_file"])
        
    def test_book_reader_view_status_code_404_for_inactive_book(self):
        inactive_book = Book.objects.create(
            title="Скрытая книга",
            slug="hidden-book",
            isbn="1234567890999",
            price=Decimal("500.00"),
            is_active=False,
        )

        response = self.client.get(
            reverse("catalog:book_reader", args=[inactive_book.slug])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_book_reader_view_status_code_404_for_nonexistent_slug(self):
        response = self.client.get(
            reverse("catalog:book_reader", args=["no-such-book"])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_book_reader_view_not_author_no_authors(self):
        response = self.client.get(
            reverse("catalog:book_reader", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["authors"], "Автор не указан")
    
    def test_book_reader_view_has_file_true_when_ebook_file_exists(self):
        self.book.ebook_file = "books/test.pdf"
        self.book.save()

        response = self.client.get(
            reverse("catalog:book_reader", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["has_file"])
        
    def test_book_reader_view_uses_correct_template(self):
        response = self.client.get(
            reverse("catalog:book_reader", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "book_reader.html")
        
    def test_book_reader_view_has_file_false_when_ebook_file_is_empty(self):
        
        response = self.client.get(
            reverse("catalog:book_reader", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["has_file"])