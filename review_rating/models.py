from django.db import models
from django.contrib.auth.models import User


class Review(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Пользователь"
    )
    book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Книга"
    )
    rating = models.PositiveSmallIntegerField(
        verbose_name="Оценка"
    )
    text = models.TextField(
        verbose_name="Текст отзыва"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                name="unique_user_book_review"
            )
        ]

    def __str__(self):
        return f"Отзыв {self.user.username} на {self.book.title}"

    @property
    def stars_range(self):
        return range(self.rating)