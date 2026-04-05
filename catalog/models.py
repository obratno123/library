from django.db import models

class Author(models.Model):
    first_name = models.CharField(
        max_length=100,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Фамилия"
    )
    biography = models.TextField(
        blank=True,
        verbose_name="Биография"
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата рождения"
    )

    class Meta:
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class Genre(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название жанра"
    )
    slug = models.SlugField(
        unique=True,
        verbose_name="Slug"
    )

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Publisher(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="Название издательства"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )

    class Meta:
        verbose_name = "Издательство"
        verbose_name_plural = "Издательства"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Название"
    )
    slug = models.SlugField(
        unique=True,
        verbose_name="Slug"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    authors = models.ManyToManyField(
    Author,
    related_name="books",
    verbose_name="Авторы"
    )

    genres = models.ManyToManyField(
        Genre,
        related_name="books",
        verbose_name="Жанры"
    )
    publish_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Год издания"
    )
    isbn = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="ISBN"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена"
    )
    cover_image = models.ImageField(
        upload_to="covers/",
        blank=True,
        null=True,
        verbose_name="Обложка"
    )
    preview_file = models.FileField(
        upload_to="previews/",
        blank=True,
        null=True,
        verbose_name="Файл предпросмотра"
    )
    ebook_file = models.FileField(
        upload_to="ebooks/",
        blank=True,
        null=True,
        verbose_name="Файл электронной книги"
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
        verbose_name="Издательство"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна"
    )

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ["title"]

    def __str__(self):
        return self.title
    
class Stock(models.Model):
    book = models.OneToOneField(
        Book,
        on_delete=models.CASCADE,
        related_name="stock",
        verbose_name="Книга"
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество на складе"
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Зарезервировано"
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        verbose_name="Порог низкого остатка"
    )

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склад"
    
    def available(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.book.title} ({self.available()} доступно)"
