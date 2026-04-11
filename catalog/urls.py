from django.urls import path
from .views import catalog_home, book_detail, book_reader_view, books_by_genre, books_by_author, books_by_publisher

app_name = 'catalog'

urlpatterns = [
    path('', catalog_home, name='catalog_home'),
    path('book/<slug:slug>/', book_detail, name='book_detail'),
    path("reader/<slug:slug>/", book_reader_view, name="book_reader"),
    path('genre/<slug:slug>/', books_by_genre, name='books_by_genre'),
    path('author/<int:author_id>/', books_by_author, name='books_by_author'),
    path('publisher/<int:publisher_id>/', books_by_publisher, name='books_by_publisher'),
]