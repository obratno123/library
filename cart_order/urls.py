from django.urls import path
from . import views

app_name = "cart_order"

urlpatterns = [
    path("", views.cart_view, name="cart_view"),
    path("add/<int:book_id>/", views.add_to_cart, name="add_to_cart"),
    path("item/<int:item_id>/update/", views.update_cart_item, name="update_cart_item"),
    path("item/<int:item_id>/remove/", views.remove_cart_item, name="remove_cart_item"),

    path("checkout/", views.checkout_view, name="checkout"),
    path("checkout/pay/", views.create_order_and_pay, name="create_order_and_pay"),
    path("order/<int:order_id>/success/", views.order_success, name="order_success"),

]