from decimal import Decimal
from django.test import TestCase

from catalog.models import Book, Stock, Author, Genre, Publisher

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