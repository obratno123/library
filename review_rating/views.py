from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Book
from .models import Review


@login_required
def add_or_edit_review(request, slug):
    book = get_object_or_404(Book, slug=slug, is_active=True)

    if request.method == "POST":
        rating = request.POST.get("rating")
        text = request.POST.get("text", "").strip()

        if rating is None:
            messages.error(request, "Укажите оценку.")
            return redirect("catalog:book_detail", slug=book.slug)

        try:
            rating = int(rating)
        except ValueError:
            messages.error(request, "Некорректная оценка.")
            return redirect("catalog:book_detail", slug=book.slug)

        if rating < 0 or rating > 5:
            messages.error(request, "Оценка должна быть от 0 до 5.")
            return redirect("catalog:book_detail", slug=book.slug)

        if not text:
            messages.error(request, "Напишите текст отзыва.")
            return redirect("catalog:book_detail", slug=book.slug)

        review, created = Review.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={
                "rating": rating,
                "text": text,
            }
        )

        if not created:
            review.rating = rating
            review.text = text
            review.save()

        messages.success(request, "Отзыв сохранён.")

    return redirect("catalog:book_detail", slug=book.slug)


@login_required
def user_reviews(request):
    reviews = (
        Review.objects.filter(user=request.user)
        .select_related("book")
        .order_by("-created_at")
    )

    return render(request, "user_reviews.html", {
        "reviews": reviews
    })