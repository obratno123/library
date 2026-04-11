import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from catalog.models import Author, Genre, Publisher, Book, Stock


class ImportBooksCommandTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        self.csv_path = self.base_path / "books.csv"
        self.epub_dir = self.base_path / "epubs"
        self.cover_dir = self.base_path / "covers"

        self.epub_dir.mkdir(parents=True, exist_ok=True)
        self.cover_dir.mkdir(parents=True, exist_ok=True)

        self.override = override_settings(MEDIA_ROOT=self.temp_dir.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.temp_dir.cleanup)

    def write_csv(self, rows, fieldnames=None):
        if fieldnames is None:
            fieldnames = [
                "number",
                "title",
                "slug",
                "first_name",
                "last_name",
                "genre",
                "genre_slug",
                "publisher",
                "publish_year",
                "price",
                "isbn",
                "description",
            ]

        with self.csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def create_epub(self, number, slug, content=b"fake epub content"):
        path = self.epub_dir / f"{number}_{slug}.epub"
        path.write_bytes(content)
        return path

    def create_cover(self, number, ext=".jpg", content=b"fake image content"):
        path = self.cover_dir / f"{number}{ext}"
        path.write_bytes(content)
        return path

    def run_command(self, **extra_options):
        out = StringIO()

        options = {
            "csv": str(self.csv_path),
            "epub_dir": str(self.epub_dir),
            "cover_dir": str(self.cover_dir),
        }
        options.update(extra_options)

        call_command("import_books_csv", stdout=out, **options)
        return out.getvalue()

    def test_import_creates_book_and_related_objects(self):
        self.write_csv([
            {
                "number": "1",
                "title": "Clean Code",
                "slug": "clean-code",
                "first_name": "Robert",
                "last_name": "Martin",
                "genre": "Programming",
                "genre_slug": "programming",
                "publisher": "Prentice Hall",
                "publish_year": "2008",
                "price": "19.99",
                "isbn": "9780132350884",
                "description": "A book about clean code",
            }
        ])
        self.create_epub("1", "clean-code")
        self.create_cover("1", ".jpg")

        output = self.run_command()

        self.assertIn("Создана: Clean Code", output)
        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Author.objects.count(), 1)
        self.assertEqual(Genre.objects.count(), 1)
        self.assertEqual(Publisher.objects.count(), 1)
        self.assertEqual(Stock.objects.count(), 1)

        book = Book.objects.get(slug="clean-code")
        self.assertEqual(book.title, "Clean Code")
        self.assertEqual(book.price, Decimal("19.99"))
        self.assertEqual(book.isbn, "9780132350884")
        self.assertTrue(book.is_active)

        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.genres.count(), 1)
        self.assertEqual(book.publisher.name, "Prentice Hall")

        stock = Stock.objects.get(book=book)
        self.assertEqual(stock.quantity, 10)
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(stock.low_stock_threshold, 5)

        self.assertTrue(bool(book.ebook_file))
        self.assertTrue(bool(book.cover_image))

    def test_skip_when_epub_not_found(self):
        self.write_csv([
            {
                "number": "2",
                "title": "Refactoring",
                "slug": "refactoring",
                "first_name": "Martin",
                "last_name": "Fowler",
                "genre": "Programming",
                "genre_slug": "programming",
                "publisher": "Addison-Wesley",
                "publish_year": "1999",
                "price": "25.00",
                "isbn": "9780201485677",
                "description": "Refactoring book",
            }
        ])
        # EPUB не создаем
        self.create_cover("2", ".jpg")

        output = self.run_command()

        self.assertIn("EPUB не найден", output)
        self.assertEqual(Book.objects.count(), 0)
        self.assertEqual(Stock.objects.count(), 0)

    def test_skip_existing_book_without_update_existing(self):
        publisher = Publisher.objects.create(name="Old Publisher")
        book = Book.objects.create(
            title="Old title",
            slug="domain-driven-design",
            description="Old desc",
            publish_year=2003,
            isbn="1111111111111",
            price=Decimal("10.00"),
            publisher=publisher,
            is_active=True,
        )

        self.write_csv([
            {
                "number": "3",
                "title": "Domain-Driven Design",
                "slug": "domain-driven-design",
                "first_name": "Eric",
                "last_name": "Evans",
                "genre": "Architecture",
                "genre_slug": "architecture",
                "publisher": "Pearson",
                "publish_year": "2004",
                "price": "30.00",
                "isbn": "9780321125217",
                "description": "New description",
            }
        ])
        self.create_epub("3", "domain-driven-design")
        self.create_cover("3", ".jpg")

        output = self.run_command()

        self.assertIn("уже существует, пропуск", output)

        book.refresh_from_db()
        self.assertEqual(book.title, "Old title")
        self.assertEqual(book.price, Decimal("10.00"))
        self.assertEqual(book.publisher.name, "Old Publisher")

    def test_update_existing_book_with_flag(self):
        old_publisher = Publisher.objects.create(name="Old Publisher")
        book = Book.objects.create(
            title="Old title",
            slug="the-pragmatic-programmer",
            description="Old desc",
            publish_year=1999,
            isbn="",
            price=Decimal("15.00"),
            publisher=old_publisher,
            is_active=False,
        )

        self.write_csv([
            {
                "number": "4",
                "title": "The Pragmatic Programmer",
                "slug": "the-pragmatic-programmer",
                "first_name": "Andrew",
                "last_name": "Hunt",
                "genre": "Programming",
                "genre_slug": "programming",
                "publisher": "Addison-Wesley",
                "publish_year": "1999",
                "price": "42.50",
                "isbn": "9780201616224",
                "description": "Classic book",
            }
        ])
        self.create_epub("4", "the-pragmatic-programmer")
        self.create_cover("4", ".jpg")

        output = self.run_command(update_existing=True)

        self.assertIn("Обновлена: The Pragmatic Programmer", output)

        book.refresh_from_db()
        self.assertEqual(book.title, "The Pragmatic Programmer")
        self.assertEqual(book.description, "Classic book")
        self.assertEqual(book.price, Decimal("42.50"))
        self.assertEqual(book.publisher.name, "Addison-Wesley")
        self.assertEqual(book.isbn, "9780201616224")
        self.assertTrue(book.is_active)
        self.assertEqual(book.authors.count(), 1)
        self.assertEqual(book.genres.count(), 1)

    def test_raises_error_when_required_columns_are_missing(self):
        self.write_csv(
            rows=[
                {
                    "number": "5",
                    "title": "Test book",
                }
            ],
            fieldnames=["number", "title"],
        )

        with self.assertRaises(CommandError) as exc:
            self.run_command()

        self.assertIn("В CSV не хватает колонок", str(exc.exception))

    def test_find_epub_by_fallback_pattern(self):
        self.write_csv([
            {
                "number": "6",
                "title": "Patterns of Enterprise Application Architecture",
                "slug": "patterns-eaa",
                "first_name": "Martin",
                "last_name": "Fowler",
                "genre": "Architecture",
                "genre_slug": "architecture",
                "publisher": "Addison-Wesley",
                "publish_year": "2002",
                "price": "35.00",
                "isbn": "9780321127426",
                "description": "Enterprise patterns",
            }
        ])

        # slug в имени файла другой, но number совпадает
        (self.epub_dir / "6_something-else.epub").write_bytes(b"fake epub")
        self.create_cover("6", ".jpg")

        output = self.run_command()

        self.assertIn("Создана: Patterns of Enterprise Application Architecture", output)
        self.assertTrue(Book.objects.filter(slug="patterns-eaa").exists())
        
    def test_existing_stock_is_updated_only_when_quantity_is_zero(self):
        publisher = Publisher.objects.create(name="Test Publisher")
        book = Book.objects.create(
            title="Old",
            slug="old-book",
            description="Old",
            publish_year=2000,
            isbn="123",
            price=Decimal("10.00"),
            publisher=publisher,
            is_active=True,
        )
        Stock.objects.create(
            book=book,
            quantity=0,
            reserved_quantity=0,
            low_stock_threshold=1,
        )

        self.write_csv([
            {
                "number": "7",
                "title": "Old",
                "slug": "old-book",
                "first_name": "John",
                "last_name": "Doe",
                "genre": "Test",
                "genre_slug": "test",
                "publisher": "Test Publisher",
                "publish_year": "2001",
                "price": "11.00",
                "isbn": "123",
                "description": "Desc",
            }
        ])
        self.create_epub("7", "old-book")

        self.run_command(update_existing=True, default_quantity=15, default_threshold=7)

        stock = Stock.objects.get(book=book)
        self.assertEqual(stock.quantity, 15)
        self.assertEqual(stock.low_stock_threshold, 7)
    
    def test_raises_error_when_csv_file_does_not_exist(self):
        with self.assertRaises(CommandError) as exc:
            self.run_command()

        self.assertIn("CSV не найден", str(exc.exception))
        
    def test_raises_error_when_epub_dir_does_not_exist(self):
        self.epub_dir.rmdir()

        self.write_csv([
            {
                "number": "1",
                "title": "Book",
                "slug": "book",
                "first_name": "John",
                "last_name": "Doe",
                "genre": "Test",
                "genre_slug": "test",
                "publisher": "Pub",
                "publish_year": "2020",
                "price": "10.00",
                "isbn": "123",
                "description": "Desc",
            }
        ])

        with self.assertRaises(CommandError) as exc:
            self.run_command()

        self.assertIn("Папка EPUB не найдена", str(exc.exception))
    
    def test_raises_error_when_cover_dir_does_not_exist(self):
        self.cover_dir.rmdir()

        self.write_csv([
            {
                "number": "1",
                "title": "Book",
                "slug": "book",
                "first_name": "John",
                "last_name": "Doe",
                "genre": "Test",
                "genre_slug": "test",
                "publisher": "Pub",
                "publish_year": "2020",
                "price": "10.00",
                "isbn": "123",
                "description": "Desc",
            }
        ])

        with self.assertRaises(CommandError) as exc:
            self.run_command()

        self.assertIn("Папка обложек не найдена", str(exc.exception))
        
    def test_updates_genre_name_when_slug_exists_with_different_name(self):
        Genre.objects.create(slug="programming", name="Old Genre Name")

        self.write_csv([
            {
                "number": "1",
                "title": "Clean Code",
                "slug": "clean-code",
                "first_name": "Robert",
                "last_name": "Martin",
                "genre": "Programming",
                "genre_slug": "programming",
                "publisher": "Prentice Hall",
                "publish_year": "2008",
                "price": "19.99",
                "isbn": "9780132350884",
                "description": "A book about clean code",
            }
        ])
        self.create_epub("1", "clean-code")
        self.create_cover("1", ".jpg")

        self.run_command()

        genre = Genre.objects.get(slug="programming")
        self.assertEqual(genre.name, "Programming")
        
    def test_skips_row_and_logs_error_when_row_processing_fails(self):
        self.write_csv([
            {
                "number": "8",
                "title": "Broken Book",
                "slug": "broken-book",
                "first_name": "John",
                "last_name": "Doe",
                "genre": "Test",
                "genre_slug": "test",
                "publisher": "Pub",
                "publish_year": "2020",
                "price": "not-a-decimal",
                "isbn": "123",
                "description": "Desc",
            }
        ])

        self.create_epub("8", "broken-book")
        self.create_cover("8", ".jpg")

        output = self.run_command()

        self.assertIn("[8] Ошибка:", output)
        self.assertEqual(Book.objects.count(), 0)