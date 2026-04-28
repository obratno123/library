import numpy as np

from django.core.management.base import BaseCommand

from catalog.models import Book
from sentence_transformers import SentenceTransformer


class Command(BaseCommand):
    help = "Generate embeddings for books"

    def handle(self, *args, **options):
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        books = Book.objects.filter(is_active=True).prefetch_related("authors", "genres")

        for book in books:
            authors = ", ".join(str(author) for author in book.authors.all())
            genres = ", ".join(genre.name for genre in book.genres.all())

            text = f"""
            Название: {book.title}
            Авторы: {authors}
            Жанры: {genres}
            Описание: {book.description}
            """

            embedding = model.encode(text, normalize_embeddings=True)

            book.embedding = embedding.astype(float).tolist()
            book.save(update_fields=["embedding"])

            self.stdout.write(self.style.SUCCESS(f"Embedding saved: {book.title}"))