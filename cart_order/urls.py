from django.urls import path
from . import views

urlpatterns = [
    path("", views.cart_view, name="cart"),
    path("add/<int:book_id>/", views.add_to_cart, name="add_to_cart"),
    path("item/<int:item_id>/update/", views.update_cart_item, name="update_cart_item"),
    path("item/<int:item_id>/remove/", views.remove_cart_item, name="remove_cart_item"),
]