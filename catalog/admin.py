from django.contrib import admin
from .models import Author, Genre, Publisher, Book, Stock

admin.site.register(Author)
admin.site.register(Genre)
admin.site.register(Publisher)
admin.site.register(Book)
admin.site.register(Stock)