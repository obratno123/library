import csv
from pathlib import Path
from decimal import Decimal

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Author, Genre, Publisher, Book, Stock


class Command(BaseCommand):
    help = "Импорт книг из CSV + папок с EPUB и обложками"

    def add_arguments(self, parser):
        parser.add_argument("--csv", type=str, required=True, help="Путь к CSV-файлу")
        parser.add_argument("--epub-dir", type=str, required=True, help="Папка с EPUB-файлами")
        parser.add_argument("--cover-dir", type=str, required=True, help="Папка с обложками")
        parser.add_argument("--default-quantity", type=int, default=10, help="Остаток на складе по умолчанию")
        parser.add_argument("--default-threshold", type=int, default=5, help="Порог низкого остатка по умолчанию")
        parser.add_argument("--update-existing", action="store_true", help="Обновлять существующие книги по slug")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        epub_dir = Path(options["epub_dir"])
        cover_dir = Path(options["cover_dir"])
        default_quantity = options["default_quantity"]
        default_threshold = options["default_threshold"]
        update_existing = options["update_existing"]

        if not csv_path.exists():
            raise CommandError(f"CSV не найден: {csv_path}")
        if not epub_dir.exists():
            raise CommandError(f"Папка EPUB не найдена: {epub_dir}")
        if not cover_dir.exists():
            raise CommandError(f"Папка обложек не найдена: {cover_dir}")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            required_columns = {
                "number", "title", "slug", "first_name", "last_name",
                "genre", "genre_slug", "publisher", "publish_year",
                "price", "isbn", "description"
            }
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"В CSV не хватает колонок: {', '.join(sorted(missing))}")

            for row in reader:
                try:
                    with transaction.atomic():
                        number = row["number"].strip()
                        title = row["title"].strip()
                        slug = row["slug"].strip()
                        first_name = row["first_name"].strip()
                        last_name = row["last_name"].strip()
                        genre_name = row["genre"].strip()
                        genre_slug = row["genre_slug"].strip()
                        publisher_name = row["publisher"].strip()
                        publish_year = int(row["publish_year"]) if row["publish_year"].strip() else None
                        price = Decimal(row["price"].strip())
                        isbn = row["isbn"].strip()
                        description = row["description"].strip()

                        epub_path = self.find_epub(epub_dir, number, slug)
                        if epub_path is None:
                            self.stdout.write(self.style.WARNING(
                                f"[#{number}] EPUB не найден для slug='{slug}', пропуск."
                            ))
                            skipped_count += 1
                            continue

                        cover_path = self.find_cover(cover_dir, number)

                        author, _ = Author.objects.get_or_create(
                            first_name=first_name,
                            last_name=last_name
                        )

                        genre, _ = Genre.objects.get_or_create(
                            slug=genre_slug,
                            defaults={"name": genre_name}
                        )
                        if genre.name != genre_name:
                            genre.name = genre_name
                            genre.save(update_fields=["name"])

                        publisher, _ = Publisher.objects.get_or_create(
                            name=publisher_name
                        )

                        book = Book.objects.filter(slug=slug).first()
                        if book and not update_existing:
                            self.stdout.write(self.style.WARNING(
                                f"[#{number}] Книга '{slug}' уже существует, пропуск."
                            ))
                            skipped_count += 1
                            continue

                        if book is None:
                            book = Book.objects.create(
                                title=title,
                                slug=slug,
                                description=description,
                                publish_year=publish_year,
                                isbn=isbn,
                                price=price,
                                publisher=publisher,
                                is_active=True,
                            )
                            created_count += 1
                            action_word = "Создана"
                        else:
                            book.title = title
                            book.description = description
                            book.publish_year = publish_year
                            book.price = price
                            book.publisher = publisher
                            if not book.isbn:
                                book.isbn = isbn
                            book.is_active = True
                            book.save()
                            updated_count += 1
                            action_word = "Обновлена"

                        book.authors.set([author])
                        book.genres.set([genre])

                        if not book.ebook_file:
                            with epub_path.open("rb") as epub_file:
                                book.ebook_file.save(epub_path.name, File(epub_file), save=True)

                        if cover_path and not book.cover_image:
                            with cover_path.open("rb") as cover_file:
                                book.cover_image.save(cover_path.name, File(cover_file), save=True)

                        stock, stock_created = Stock.objects.get_or_create(
                            book=book,
                            defaults={
                                "quantity": default_quantity,
                                "reserved_quantity": 0,
                                "low_stock_threshold": default_threshold,
                            }
                        )
                        if not stock_created:
                            # Ничего не ломаем: только если остаток пустой
                            if stock.quantity == 0:
                                stock.quantity = default_quantity
                                stock.low_stock_threshold = default_threshold
                                stock.save(update_fields=["quantity", "low_stock_threshold"])

                        self.stdout.write(self.style.SUCCESS(
                            f"[#{number}] {action_word}: {book.title}"
                        ))

                except Exception as e:
                    skipped_count += 1
                    self.stdout.write(self.style.ERROR(
                        f"[{row.get('number', '?')}] Ошибка: {e}"
                    ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Готово. Создано: {created_count}, обновлено: {updated_count}, пропущено: {skipped_count}"
        ))

    @staticmethod
    def find_epub(epub_dir: Path, number: str, slug: str):
        exact = epub_dir / f"{number}_{slug}.epub"
        if exact.exists():
            return exact

        candidates = list(epub_dir.glob(f"{number}_*.epub"))
        return candidates[0] if candidates else None

    @staticmethod
    def find_cover(cover_dir: Path, number: str):
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = cover_dir / f"{number}{ext}"
            if candidate.exists():
                return candidate
        return None
