from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Book, Author, Genre, Publisher
from django.db.models import Avg
from review_rating.models import Review

def book_reader_view(request, slug):
    book = get_object_or_404(
        Book.objects.prefetch_related("authors"),
        slug=slug,
        is_active=True,
    )

    authors = ", ".join(
        f"{author.first_name} {author.last_name}"
        for author in book.authors.all()
    ) or "Автор не указан"

    context = {
        "book": book,
        "authors": authors,
        "has_file": bool(book.ebook_file),
    }
    return render(request, "book_reader.html", context)


def catalog_home(request):
    books = Book.objects.filter(is_active=True).prefetch_related(
        "authors",
        "genres"
    ).select_related(
        "publisher"
    )

    query = request.GET.get("q", "").strip()
    genre_slug = request.GET.get("genre", "").strip()
    author_id = request.GET.get("author", "").strip()
    publisher_id = request.GET.get("publisher", "").strip()

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(isbn__icontains=query) |
            Q(description__icontains=query)
        )

    if genre_slug:
        books = books.filter(genres__slug=genre_slug)

    if author_id:
        books = books.filter(authors__id=author_id)

    if publisher_id:
        books = books.filter(publisher_id=publisher_id)

    books = books.distinct()

    paginator = Paginator(books, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "authors": Author.objects.all(),
        "genres": Genre.objects.all(),
        "publishers": Publisher.objects.all(),
        "query": query,
        "selected_genre": genre_slug,
        "selected_author": author_id,
        "selected_publisher": publisher_id,
    }
    return render(request, "catalog_home.html", context)


def book_detail(request, slug):
    book = get_object_or_404(
        Book.objects.filter(is_active=True).prefetch_related(
            "authors",
            "genres",
            "reviews__user"
        ).select_related(
            "publisher"
        ),
        slug=slug
    )

    stock = getattr(book, "stock", None)
    available_quantity = stock.available() if stock else 0

    related_books = Book.objects.filter(
        is_active=True,
        genres__in=book.genres.all()
    ).exclude(id=book.id).distinct()[:4]

    reviews = book.reviews.select_related("user").order_by("-created_at")[:5]
    average_rating = reviews.aggregate(avg=Avg("rating"))["avg"]
    reviews_count = reviews.count()

    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(user=request.user, book=book).first()

    context = {
        "book": book,
        "stock": stock,
        "available_quantity": available_quantity,
        "related_books": related_books,
        "reviews": reviews,
        "reviews_count": reviews_count,
        "average_rating": average_rating,
        "user_review": user_review,
    }
    return render(request, "book_detail.html", context)


def books_by_genre(request, slug):
    genre = get_object_or_404(Genre, slug=slug)

    books = Book.objects.filter(
        is_active=True,
        genres=genre
    ).prefetch_related(
        "authors",
        "genres"
    ).select_related(
        "publisher"
    ).distinct()

    paginator = Paginator(books, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "genre": genre,
        "page_obj": page_obj,
    }
    return render(request, "catalog/books_by_genre.html", context)


def books_by_author(request, author_id):
    author = get_object_or_404(Author, id=author_id)

    books = Book.objects.filter(
        is_active=True,
        authors=author
    ).prefetch_related(
        "authors",
        "genres"
    ).select_related(
        "publisher"
    ).distinct()

    paginator = Paginator(books, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "author": author,
        "page_obj": page_obj,
    }
    return render(request, "catalog/books_by_author.html", context)


def books_by_publisher(request, publisher_id):
    publisher = get_object_or_404(Publisher, id=publisher_id)

    books = Book.objects.filter(
        is_active=True,
        publisher=publisher
    ).prefetch_related(
        "authors",
        "genres"
    ).select_related(
        "publisher"
    ).distinct()

    paginator = Paginator(books, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "publisher": publisher,
        "page_obj": page_obj,
    }
    return render(request, "catalog/books_by_publisher.html", context)