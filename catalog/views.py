from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Book, Author, Genre, Publisher
from django.db.models import Avg
from review_rating.models import Review
from django.db.models import Count
from cart_order.models import OrderItem
import numpy as np
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


def get_purchase_recommendations(book, limit=4):
    buyer_ids = OrderItem.objects.filter(
        book=book,
        order__payment_status="paid"
    ).values_list("order__user_id", flat=True).distinct()

    recommendations = (
        Book.objects.filter(
            order_items__order__user_id__in=buyer_ids,
            order_items__order__payment_status="paid",
            is_active=True
        )
        .exclude(id=book.id)
        .annotate(common_buyers=Count("order_items__order__user", distinct=True))
        .order_by("-common_buyers", "title")
        .prefetch_related("authors")
        .distinct()[:limit]
    )

    return recommendations

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
    sort = request.GET.get("sort", "").strip()

    if query:
        words = query.split()

        search_filter = (
            Q(title__icontains=query) |
            Q(isbn__icontains=query) |
            Q(description__icontains=query) |
            Q(publisher__name__icontains=query) |
            Q(genres__name__icontains=query) |
            Q(authors__first_name__icontains=query) |
            Q(authors__last_name__icontains=query)
        )

        for word in words:
            search_filter |= Q(title__icontains=word)
            search_filter |= Q(isbn__icontains=word)
            search_filter |= Q(description__icontains=word)
            search_filter |= Q(publisher__name__icontains=word)
            search_filter |= Q(genres__name__icontains=word)
            search_filter |= Q(authors__first_name__icontains=word)
            search_filter |= Q(authors__last_name__icontains=word)

        books = books.filter(search_filter)

    if genre_slug:
        books = books.filter(genres__slug=genre_slug)

    if author_id:
        books = books.filter(authors__id=author_id)

    if publisher_id:
        books = books.filter(publisher_id=publisher_id)

    books = books.distinct()

    if sort == "price_asc":
        books = books.order_by("price", "id")
    elif sort == "price_desc":
        books = books.order_by("-price", "id")

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
        "sort": sort,
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
    
    related_books = get_embedding_recommendations(book)
    
    if not related_books:
        related_books = list(get_purchase_recommendations(book))

    if not related_books:
        related_books = list(
            Book.objects.filter(
                is_active=True,
                genres__in=book.genres.all()
            ).exclude(id=book.id).distinct()[:4]
        )
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

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0

    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_embedding_recommendations(book, limit=4):
    if not book.embedding:
        return []

    candidates = (
        Book.objects
        .filter(is_active=True, embedding__isnull=False)
        .exclude(id=book.id)
        .prefetch_related("authors")
    )

    scored_books = []

    for candidate in candidates:
        score = cosine_similarity(book.embedding, candidate.embedding)
        scored_books.append((score, candidate))

    scored_books.sort(key=lambda x: x[0], reverse=True)

    return [candidate for score, candidate in scored_books[:limit]]