from django.urls import path
from .views import catalog_home, book_detail, book_reader_view

app_name = 'catalog'

urlpatterns = [
    path('', catalog_home, name='catalog_home'),
    path('book/<slug:slug>/', book_detail, name='book_detail'),
    path("reader/<slug:slug>/", book_reader_view, name="book_reader"),

]