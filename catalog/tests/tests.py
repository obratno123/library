from decimal import Decimal
from unittest.mock import patch
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User, AnonymousUser

from catalog.models import Book, Stock, Author, Genre, Publisher

from django.urls import reverse

from catalog.views import book_detail, catalog_home
from review_rating.models import Review

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
        

class bookreaderviewTests(TestCase):
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
        
    def test_book_reader_view_with_one_author(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")
        self.book.authors.add(author)

        response = self.client.get(
            reverse("catalog:book_reader", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["authors"], "Фрэнк Герберт")
    
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
        

class cataloghomeTests(TestCase):
    def test_catalog_home_shows_only_active_books(self):
        active_book = Book.objects.create(
            title="Активная книга",
            slug="active-book",
            isbn="1234567890123",
            price=Decimal("500.00"),
            is_active=True,
        )
        inactive_book = Book.objects.create(
            title="Неактивная книга",
            slug="inactive-book",
            isbn="1234567890124",
            price=Decimal("600.00"),
            is_active=False,
        )

        response = self.client.get(reverse("catalog:catalog_home"))

        self.assertEqual(response.status_code, 200)
        page_books = list(response.context["page_obj"].object_list)

        self.assertIn(active_book, page_books)
        self.assertNotIn(inactive_book, page_books)
        
    def test_catalog_home_filters_by_title_query(self):
        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna",
            isbn="1234567890123",
            price=Decimal("800.00"),
            is_active=True,
        )
        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin",
            isbn="1234567890124",
            price=Decimal("500.00"),
            is_active=True,
        )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"q": "Дюна"}
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(other_book, page_books)

        self.assertEqual(response.context["query"], "Дюна")
        
    def test_catalog_home_filters_by_isbn_query(self):
        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna",
            isbn="1234567890123",
            price=Decimal("800.00"),
            is_active=True,
        )
        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin",
            isbn="9999999999999",
            price=Decimal("500.00"),
            is_active=True,
        )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"q": "1234567890123"}
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(other_book, page_books)

        self.assertEqual(response.context["query"], "1234567890123")
        
    def test_catalog_home_filters_by_description_query(self):
        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-desc",
            isbn="1234567890125",
            price=Decimal("800.00"),
            is_active=True,
            description="Эпическая фантастика о пустынной планете",
        )
        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin-desc",
            isbn="1234567890126",
            price=Decimal("500.00"),
            is_active=True,
            description="Классический роман в стихах",
        )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"q": "пустынной планете"}
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(other_book, page_books)

        self.assertEqual(response.context["query"], "пустынной планете")
        
    def test_catalog_home_filters_by_genre(self):
        genre_fantasy = Genre.objects.create(
            name="Фантастика",
            slug="fantasy",
        )
        genre_classic = Genre.objects.create(
            name="Классика",
            slug="classic",
        )

        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-genre",
            isbn="1234567890127",
            price=Decimal("800.00"),
            is_active=True,
        )
        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin-genre",
            isbn="1234567890128",
            price=Decimal("500.00"),
            is_active=True,
        )

        matching_book.genres.add(genre_fantasy)
        other_book.genres.add(genre_classic)

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"genre": "fantasy"}
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(other_book, page_books)

        self.assertEqual(response.context["selected_genre"], "fantasy")
        
    def test_catalog_home_filters_by_author(self):
        author_match = Author.objects.create(
            first_name="Фрэнк",
            last_name="Герберт",
        )
        author_other = Author.objects.create(
            first_name="Александр",
            last_name="Пушкин",
        )

        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-author",
            isbn="1234567890129",
            price=Decimal("800.00"),
            is_active=True,
        )
        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin-author",
            isbn="1234567890130",
            price=Decimal("500.00"),
            is_active=True,
        )

        matching_book.authors.add(author_match)
        other_book.authors.add(author_other)

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"author": str(author_match.id)}
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(other_book, page_books)

        self.assertEqual(response.context["selected_author"], str(author_match.id))


    def test_catalog_home_filters_by_publisher(self):
        publisher_match = Publisher.objects.create(name="АСТ")
        publisher_other = Publisher.objects.create(name="Эксмо")

        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-publisher",
            isbn="1234567890131",
            price=Decimal("800.00"),
            is_active=True,
            publisher=publisher_match,
        )
        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin-publisher",
            isbn="1234567890132",
            price=Decimal("500.00"),
            is_active=True,
            publisher=publisher_other,
        )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"publisher": str(publisher_match.id)}
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(other_book, page_books)

        self.assertEqual(response.context["selected_publisher"], str(publisher_match.id))
        
    def test_catalog_home_applies_multiple_filters(self):
        genre_match = Genre.objects.create(
            name="Фантастика",
            slug="fantasy",
        )
        genre_other = Genre.objects.create(
            name="Классика",
            slug="classic",
        )

        author_match = Author.objects.create(
            first_name="Фрэнк",
            last_name="Герберт",
        )
        author_other = Author.objects.create(
            first_name="Александр",
            last_name="Пушкин",
        )

        publisher_match = Publisher.objects.create(name="АСТ")
        publisher_other = Publisher.objects.create(name="Эксмо")

        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-combo",
            isbn="1234567890133",
            price=Decimal("800.00"),
            is_active=True,
            description="Эпическая фантастика",
            publisher=publisher_match,
        )
        matching_book.genres.add(genre_match)
        matching_book.authors.add(author_match)

        wrong_genre_book = Book.objects.create(
            title="Дюна 2",
            slug="duna-wrong-genre",
            isbn="1234567890134",
            price=Decimal("800.00"),
            is_active=True,
            description="Эпическая фантастика",
            publisher=publisher_match,
        )
        wrong_genre_book.genres.add(genre_other)
        wrong_genre_book.authors.add(author_match)

        wrong_author_book = Book.objects.create(
            title="Дюна 3",
            slug="duna-wrong-author",
            isbn="1234567890135",
            price=Decimal("800.00"),
            is_active=True,
            description="Эпическая фантастика",
            publisher=publisher_match,
        )
        wrong_author_book.genres.add(genre_match)
        wrong_author_book.authors.add(author_other)

        wrong_publisher_book = Book.objects.create(
            title="Дюна 4",
            slug="duna-wrong-publisher",
            isbn="1234567890136",
            price=Decimal("800.00"),
            is_active=True,
            description="Эпическая фантастика",
            publisher=publisher_other,
        )
        wrong_publisher_book.genres.add(genre_match)
        wrong_publisher_book.authors.add(author_match)

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {
                "q": "Дюна",
                "genre": "fantasy",
                "author": str(author_match.id),
                "publisher": str(publisher_match.id),
            }
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(wrong_genre_book, page_books)
        self.assertNotIn(wrong_author_book, page_books)
        self.assertNotIn(wrong_publisher_book, page_books)

        self.assertEqual(response.context["query"], "Дюна")
        self.assertEqual(response.context["selected_genre"], "fantasy")
        self.assertEqual(response.context["selected_author"], str(author_match.id))
        self.assertEqual(response.context["selected_publisher"], str(publisher_match.id))
        
    def test_catalog_home_paginates_books_by_8_on_first_page(self):
        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"book-{i}",
                isbn=f"12345678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )

        response = self.client.get(reverse("catalog:catalog_home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertFalse(response.context["page_obj"].has_previous())
        
    def test_catalog_home_returns_second_page_with_remaining_books(self):
        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"book-page2-{i}",
                isbn=f"22345678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"page": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())
        
    def test_catalog_home_invalid_page_returns_first_page(self):
        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"book-{i}",
                isbn=f"12345678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )

        response = self.client.get(reverse("catalog:catalog_home"),
            {"page": "asd"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertFalse(response.context["page_obj"].has_previous())
        
    def test_catalog_home_uses_correct_template(self):
        response = self.client.get(reverse("catalog:catalog_home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog_home.html")
        
    def test_catalog_home_contains_filter_lists_in_context(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")
        genre = Genre.objects.create(name="Фантастика", slug="fantasy")
        publisher = Publisher.objects.create(name="АСТ")

        response = self.client.get(reverse("catalog:catalog_home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(author, response.context["authors"])
        self.assertIn(genre, response.context["genres"])
        self.assertIn(publisher, response.context["publishers"])
        
    def test_catalog_home_too_large_page_returns_last_page(self):
        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"book-last-{i}",
                isbn=f"33345678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"page": 999}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        
    def test_catalog_home_distinct_removes_duplicates(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")
        genre1 = Genre.objects.create(name="Фантастика", slug="fantasy")
        genre2 = Genre.objects.create(name="Приключения", slug="adventure")

        book = Book.objects.create(
            title="Дюна",
            slug="duna-distinct",
            isbn="1234567890991",
            price=Decimal("800.00"),
            is_active=True,
        )
        book.authors.add(author)
        book.genres.add(genre1, genre2)

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"author": str(author.id)}
        )

        self.assertEqual(response.status_code, 200)

        page_books = list(response.context["page_obj"].object_list)
        self.assertEqual(page_books.count(book), 1)
        
    def test_catalog_home_strips_query_whitespace(self):
        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-strip",
            isbn="1234567890555",
            price=Decimal("800.00"),
            is_active=True,
        )
        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin-strip",
            isbn="1234567890556",
            price=Decimal("500.00"),
            is_active=True,
        )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"q": "  Дюна  "}
        )

        self.assertEqual(response.status_code, 200)
        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(other_book, page_books)
        self.assertEqual(response.context["query"], "Дюна")
        
    def test_catalog_home_does_not_show_inactive_book(self):
        active_book = Book.objects.create(
            title="Дюна",
            slug="duna-active-search",
            isbn="1234567890666",
            price=Decimal("800.00"),
            is_active=True,
        )
        inactive_book = Book.objects.create(
            title="Дюна",
            slug="duna-inactive-search",
            isbn="1234567890667",
            price=Decimal("800.00"),
            is_active=False,
        )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"q": "Дюна"}
        )

        self.assertEqual(response.status_code, 200)
        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(active_book, page_books)
        self.assertNotIn(inactive_book, page_books)
        
    def test_catalog_home_returns_empty_result_for_unknown_query(self):
        Book.objects.create(
            title="Дюна",
            slug="duna-empty-search",
            isbn="1234567890777",
            price=Decimal("800.00"),
            is_active=True,
        )

        response = self.client.get(
            reverse("catalog:catalog_home"),
            {"q": "несуществующий запрос"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"].object_list), [])
        self.assertEqual(response.context["query"], "несуществующий запрос")
        
    def test_catalog_home_sorts_books_by_price_ascending(self):
        factory = RequestFactory()

        publisher = Publisher.objects.create(name="Test Publisher")
        genre = Genre.objects.create(name="Fantasy", slug="fantasy")
        author = Author.objects.create(first_name="John", last_name="Smith")

        cheap_book = Book.objects.create(
            title="Cheap Book",
            slug="cheap-book",
            description="Cheap",
            isbn="isbn-cheap",
            price=Decimal("10.00"),
            publisher=publisher,
            is_active=True,
        )
        cheap_book.authors.add(author)
        cheap_book.genres.add(genre)

        expensive_book = Book.objects.create(
            title="Expensive Book",
            slug="expensive-book",
            description="Expensive",
            isbn="isbn-expensive",
            price=Decimal("50.00"),
            publisher=publisher,
            is_active=True,
        )
        expensive_book.authors.add(author)
        expensive_book.genres.add(genre)

        middle_book = Book.objects.create(
            title="Middle Book",
            slug="middle-book",
            description="Middle",
            isbn="isbn-middle",
            price=Decimal("30.00"),
            publisher=publisher,
            is_active=True,
        )
        middle_book.authors.add(author)
        middle_book.genres.add(genre)

        request = factory.get("/catalog/", {"sort": "price_asc"})

        with patch("catalog.views.render") as mock_render:
            catalog_home(request)

        _, template_name, context = mock_render.call_args[0]
        books = list(context["page_obj"].object_list)

        self.assertEqual(template_name, "catalog_home.html")
        self.assertEqual(books, [cheap_book, middle_book, expensive_book])
        self.assertEqual(context["sort"], "price_asc")
        
    def test_catalog_home_sorts_books_by_price_descending(self):
        factory = RequestFactory()

        publisher = Publisher.objects.create(name="Test Publisher")
        genre = Genre.objects.create(name="Fantasy", slug="fantasy")
        author = Author.objects.create(first_name="John", last_name="Smith")

        cheap_book = Book.objects.create(
            title="Cheap Book",
            slug="cheap-book-desc",
            description="Cheap",
            isbn="isbn-cheap-desc",
            price=Decimal("10.00"),
            publisher=publisher,
            is_active=True,
        )
        cheap_book.authors.add(author)
        cheap_book.genres.add(genre)

        expensive_book = Book.objects.create(
            title="Expensive Book",
            slug="expensive-book-desc",
            description="Expensive",
            isbn="isbn-expensive-desc",
            price=Decimal("50.00"),
            publisher=publisher,
            is_active=True,
        )
        expensive_book.authors.add(author)
        expensive_book.genres.add(genre)

        middle_book = Book.objects.create(
            title="Middle Book",
            slug="middle-book-desc",
            description="Middle",
            isbn="isbn-middle-desc",
            price=Decimal("30.00"),
            publisher=publisher,
            is_active=True,
        )
        middle_book.authors.add(author)
        middle_book.genres.add(genre)

        request = factory.get("/catalog/", {"sort": "price_desc"})

        with patch("catalog.views.render") as mock_render:
            catalog_home(request)

        _, template_name, context = mock_render.call_args[0]
        books = list(context["page_obj"].object_list)

        self.assertEqual(template_name, "catalog_home.html")
        self.assertEqual(books, [expensive_book, middle_book, cheap_book])
        self.assertEqual(context["sort"], "price_desc")
        

class bookdetailTests(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(
            name="Фантастика",
            slug="fantasy",
        )

        self.book = Book.objects.create(
            title="Дюна",
            slug="duna-detail",
            isbn="1234567890991",
            price=Decimal("800.00"),
            is_active=True,
        )
        self.book.genres.add(self.genre)
        
    def test_book_detail_status_code_200_active_book(self):
        response = self.client.get(
            reverse("catalog:book_detail", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["book"], self.book)
        self.assertTemplateUsed(response, "book_detail.html")
    
    def test_book_detail_status_code_404_for_inactive_book(self):
        inactive_book = Book.objects.create(
            title="Скрытая книга",
            slug="hidden-book-detail",
            isbn="1234567890992",
            price=Decimal("500.00"),
            is_active=False,
        )

        response = self.client.get(
            reverse("catalog:book_detail", args=[inactive_book.slug])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_book_detail_status_code_404_for_nonexistent_slug(self):
        response = self.client.get(
            reverse("catalog:book_detail", args=["no-such-book"])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_book_detail_available_quantity_is_zero_stock(self):
        response = self.client.get(
            reverse("catalog:book_detail", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["stock"])
        self.assertEqual(response.context["available_quantity"], 0)
        
    def test_book_detail_available_quantity_from_stock(self):
        stock = Stock.objects.create(
            book=self.book,
            quantity=10,
            reserved_quantity=3,
        )

        response = self.client.get(
            reverse("catalog:book_detail", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stock"], stock)
        self.assertEqual(response.context["available_quantity"], 7)
        
    def test_book_detail_related_books_inactive_books(self):
        related_active = Book.objects.create(
            title="Дюна: Мессия",
            slug="dune-messiah",
            isbn="1234567890993",
            price=Decimal("700.00"),
            is_active=True,
        )
        related_active.genres.add(self.genre)

        related_inactive = Book.objects.create(
            title="Скрытая Дюна",
            slug="hidden-dune",
            isbn="1234567890994",
            price=Decimal("700.00"),
            is_active=False,
        )
        related_inactive.genres.add(self.genre)

        other_genre = Genre.objects.create(name="Классика", slug="classic")
        unrelated_book = Book.objects.create(
            title="Онегин",
            slug="onegin-detail",
            isbn="1234567890995",
            price=Decimal("500.00"),
            is_active=True,
        )
        unrelated_book.genres.add(other_genre)

        response = self.client.get(
            reverse("catalog:book_detail", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)

        related_books = list(response.context["related_books"])
        self.assertIn(related_active, related_books)
        self.assertNotIn(self.book, related_books)
        self.assertNotIn(related_inactive, related_books)
        self.assertNotIn(unrelated_book, related_books)
        
        
    def test_book_detail_related_books_is_limited_to_four(self):
        for i in range(5):
            book = Book.objects.create(
                title=f"Похожая книга {i}",
                slug=f"related-book-{i}",
                isbn=f"12345678919{i:02d}",
                price=Decimal("600.00"),
                is_active=True,
            )
            book.genres.add(self.genre)

        response = self.client.get(
            reverse("catalog:book_detail", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["related_books"]), 4)
        
    def test_book_detail_returns_empty_related_books_no_genres(self):
        book = Book.objects.create(
            title="Без жанров",
            slug="no-genres-book",
            isbn="1234567890888",
            price=Decimal("500.00"),
            is_active=True,
        )

        response = self.client.get(
            reverse("catalog:book_detail", args=[book.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["related_books"]), [])
        
    def test_book_detail_related_books_are_distinct(self):
        genre1 = Genre.objects.create(name="Фантастика 2", slug="fantasy-2")
        genre2 = Genre.objects.create(name="Приключения 2", slug="adventure-2")

        self.book.genres.add(genre1, genre2)

        related_book = Book.objects.create(
            title="Похожая книга",
            slug="related-distinct",
            isbn="1234567890889",
            price=Decimal("600.00"),
            is_active=True,
        )
        related_book.genres.add(genre1, genre2)

        response = self.client.get(
            reverse("catalog:book_detail", args=[self.book.slug])
        )

        self.assertEqual(response.status_code, 200)

        related_books = list(response.context["related_books"])
        self.assertEqual(related_books.count(related_book), 1)
        
    def test_book_detail_sets_user_review_for_authenticated_user(self):
        factory = RequestFactory()

        user = User.objects.create_user(
            username="reader",
            password="testpass123"
        )

        publisher = Publisher.objects.create(name="Test Publisher")
        genre = Genre.objects.create(name="Fantasy", slug="fantasy-detail-auth")
        author = Author.objects.create(
            first_name="John",
            last_name="Smith"
        )

        book = Book.objects.create(
            title="Book Detail Auth",
            slug="book-detail-auth",
            description="Test description",
            isbn="isbn-detail-auth",
            price=Decimal("100.00"),
            publisher=publisher,
            is_active=True,
        )
        book.authors.add(author)
        book.genres.add(genre)

        Stock.objects.create(
            book=book,
            quantity=10,
            reserved_quantity=3
        )

        review = Review.objects.create(
            user=user,
            book=book,
            rating=5,
            text="Great book"
        )

        request = factory.get("/catalog/book-detail-auth/")
        request.user = user

        with patch("catalog.views.render") as mock_render:
            book_detail(request, slug="book-detail-auth")

        mock_render.assert_called_once()
        _, template_name, context = mock_render.call_args[0]

        self.assertEqual(template_name, "book_detail.html")
        self.assertEqual(context["book"], book)
        self.assertEqual(context["user_review"], review)
        
    def test_book_detail_sets_user_review_none_for_anonymous_user(self):
        factory = RequestFactory()

        user = User.objects.create_user(
            username="reader2",
            password="testpass123"
        )

        publisher = Publisher.objects.create(name="Test Publisher")
        genre = Genre.objects.create(name="Fantasy", slug="fantasy-detail-anon")
        author = Author.objects.create(
            first_name="Jane",
            last_name="Smith"
        )

        book = Book.objects.create(
            title="Book Detail Anon",
            slug="book-detail-anon",
            description="Test description",
            isbn="isbn-detail-anon",
            price=Decimal("120.00"),
            publisher=publisher,
            is_active=True,
        )
        book.authors.add(author)
        book.genres.add(genre)

        Stock.objects.create(
            book=book,
            quantity=5,
            reserved_quantity=1
        )

        Review.objects.create(
            user=user,
            book=book,
            rating=4,
            text="Nice book"
        )

        request = factory.get("/catalog/book-detail-anon/")
        request.user = AnonymousUser()

        with patch("catalog.views.render") as mock_render:
            book_detail(request, slug="book-detail-anon")

        mock_render.assert_called_once()
        _, template_name, context = mock_render.call_args[0]

        self.assertEqual(template_name, "book_detail.html")
        self.assertEqual(context["book"], book)
        self.assertIsNone(context["user_review"])
        

class booksbygenreTests(TestCase):
    def test_books_by_genre_status_code_404_for_nonexistent_genre(self):
        response = self.client.get(
            reverse("catalog:books_by_genre", args=["no-such-genre"])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_books_by_genre_returns_only_active_books_for_selected_genre(self):
        genre = Genre.objects.create(name="Фантастика", slug="fantasy")
        other_genre = Genre.objects.create(name="Классика", slug="classic")

        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-genre-view",
            isbn="1234567890501",
            price=Decimal("800.00"),
            is_active=True,
        )
        matching_book.genres.add(genre)

        inactive_book = Book.objects.create(
            title="Скрытая Дюна",
            slug="hidden-duna-genre-view",
            isbn="1234567890502",
            price=Decimal("800.00"),
            is_active=False,
        )
        inactive_book.genres.add(genre)

        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin-genre-view",
            isbn="1234567890503",
            price=Decimal("500.00"),
            is_active=True,
        )
        other_book.genres.add(other_genre)

        response = self.client.get(
            reverse("catalog:books_by_genre", args=[genre.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["genre"], genre)
        self.assertTemplateUsed(response, "catalog/books_by_genre.html")

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(inactive_book, page_books)
        self.assertNotIn(other_book, page_books)
        
    def test_books_by_genre_paginates_books_by_8(self):
        genre = Genre.objects.create(name="Фантастика", slug="fantasy")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"genre-book-{i}",
                isbn=f"55545678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.genres.add(genre)

        response = self.client.get(
            reverse("catalog:books_by_genre", args=[genre.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
        
    def test_books_by_genre_returns_second_page_other_books(self):
        genre = Genre.objects.create(name="Фантастика", slug="fantasy")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"genre-book-page2-{i}",
                isbn=f"55645678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.genres.add(genre)

        response = self.client.get(
            reverse("catalog:books_by_genre", args=[genre.slug]),
            {"page": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())
        
    def test_books_by_genre_returns_big_page_second_books(self):
        genre = Genre.objects.create(name="Фантастика", slug="fantasy")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"genre-book-page2-{i}",
                isbn=f"55645678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.genres.add(genre)

        response = self.client.get(
            reverse("catalog:books_by_genre", args=[genre.slug]),
            {"page": 9999}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())
        
    def test_books_by_genre_returns_abc_page_second_books(self):
        genre = Genre.objects.create(name="Фантастика", slug="fantasy")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"genre-book-page2-{i}",
                isbn=f"55645678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.genres.add(genre)

        response = self.client.get(
            reverse("catalog:books_by_genre", args=[genre.slug]),
            {"page": "abc"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertFalse(response.context["page_obj"].has_previous())
    
    
class booksbyauthorTests(TestCase):
    def test_books_by_author_status_code_404_for_nonexistent_genre(self):
        response = self.client.get(
            reverse("catalog:books_by_author", args=[9999])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_books_by_author_returns_only_active_books_for_selected_author(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")
        other_author = Author.objects.create(first_name="Александр", last_name="Пушкин")

        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-author-view",
            isbn="1234567890401",
            price=Decimal("800.00"),
            is_active=True,
        )
        matching_book.authors.add(author)

        inactive_book = Book.objects.create(
            title="Скрытая Дюна",
            slug="hidden-duna-author-view",
            isbn="1234567890402",
            price=Decimal("800.00"),
            is_active=False,
        )
        inactive_book.authors.add(author)

        other_book = Book.objects.create(
            title="Онегин",
            slug="onegin-author-view",
            isbn="1234567890403",
            price=Decimal("500.00"),
            is_active=True,
        )
        other_book.authors.add(other_author)

        response = self.client.get(
            reverse("catalog:books_by_author", args=[author.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["author"], author)
        self.assertTemplateUsed(response, "catalog/books_by_author.html")

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(inactive_book, page_books)
        self.assertNotIn(other_book, page_books)
        
    def test_books_by_author_paginates_books_by_8(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"author-book-{i}",
                isbn=f"65545678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.authors.add(author)

        response = self.client.get(
            reverse("catalog:books_by_author", args=[author.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
            
    def test_books_by_author_returns_second_page_other_books(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"author-book-page2-{i}",
                isbn=f"65645678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.authors.add(author)

        response = self.client.get(
            reverse("catalog:books_by_author", args=[author.id]),
            {"page": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())
            
    def test_books_by_author_returns_big_page_second_books(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"author-book-page2-{i}",
                isbn=f"65745678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.authors.add(author)

        response = self.client.get(
            reverse("catalog:books_by_author", args=[author.id]),
            {"page": 9999}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())
            
    def test_books_by_author_returns_abc_page_second_books(self):
        author = Author.objects.create(first_name="Фрэнк", last_name="Герберт")

        for i in range(9):
            book = Book.objects.create(
                title=f"Книга {i}",
                slug=f"author-book-page2-{i}",
                isbn=f"65845678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
            )
            book.authors.add(author)

        response = self.client.get(
            reverse("catalog:books_by_author", args=[author.id]),
            {"page": "abc"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertFalse(response.context["page_obj"].has_previous())
    
    
class booksbypublisherTests(TestCase):
    def test_books_by_publisher_status_code_404_for_nonexistent_genre(self):
        response = self.client.get(
            reverse("catalog:books_by_publisher", args=[9999])
        )

        self.assertEqual(response.status_code, 404)
        
    def test_books_by_publisher_returns_only_active_books_for_selected_publisher(self):
        publisher = Publisher.objects.create(name="АСТ")
        other_publisher = Publisher.objects.create(name="Эксмо")

        matching_book = Book.objects.create(
            title="Дюна",
            slug="duna-publisher-view",
            isbn="1234567890301",
            price=Decimal("800.00"),
            is_active=True,
            publisher=publisher,
        )

        inactive_book = Book.objects.create(
            title="Скрытая Дюна",
            slug="hidden-duna-publisher-view",
            isbn="1234567890302",
            price=Decimal("800.00"),
            is_active=False,
            publisher=publisher,
        )
        other_book = Book.objects.create(
        title="Онегин",
        slug="onegin-publisher-view",
        isbn="1234567890303",
        price=Decimal("500.00"),
        is_active=True,
        publisher=other_publisher,
        )

        response = self.client.get(
            reverse("catalog:books_by_publisher", args=[publisher.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["publisher"], publisher)
        self.assertTemplateUsed(response, "catalog/books_by_publisher.html")

        page_books = list(response.context["page_obj"].object_list)
        self.assertIn(matching_book, page_books)
        self.assertNotIn(inactive_book, page_books)
        self.assertNotIn(other_book, page_books)
        
    def test_books_by_publisher_paginates_books_by_8(self):
        publisher = Publisher.objects.create(name="АСТ")

        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"publisher-book-{i}",
                isbn=f"75545678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
                publisher=publisher,
            )

        response = self.client.get(
            reverse("catalog:books_by_publisher", args=[publisher.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
            
    def test_books_by_publisher_returns_second_page_other_books(self):
        publisher = Publisher.objects.create(name="АСТ")

        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"publisher-book-page2-{i}",
                isbn=f"75645678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
                publisher=publisher,
            )

        response = self.client.get(
            reverse("catalog:books_by_publisher", args=[publisher.id]),
            {"page": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())
            
    def test_books_by_publisher_returns_big_page_second_books(self):
        publisher = Publisher.objects.create(name="АСТ")

        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"publisher-book-page2-{i}",
                isbn=f"75745678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
                publisher=publisher,
            )

        response = self.client.get(
            reverse("catalog:books_by_publisher", args=[publisher.id]),
            {"page": 9999}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 1)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())
            
    def test_books_by_publisher_returns_abc_page_second_books(self):
        publisher = Publisher.objects.create(name="АСТ")

        for i in range(9):
            Book.objects.create(
                title=f"Книга {i}",
                slug=f"publisher-book-page2-{i}",
                isbn=f"75845678901{i:02d}",
                price=Decimal("500.00"),
                is_active=True,
                publisher=publisher,
            )

        response = self.client.get(
            reverse("catalog:books_by_publisher", args=[publisher.id]),
            {"page": "abc"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"].object_list), 8)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertFalse(response.context["page_obj"].has_previous())