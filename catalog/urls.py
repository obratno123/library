from django.urls import path
from .views import catalog_home, book_detail

app_name = 'catalog'

urlpatterns = [
    path('', catalog_home, name='catalog_home'),
    path('book/<slug:slug>/', book_detail, name='book_detail'),
]