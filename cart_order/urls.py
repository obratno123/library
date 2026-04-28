from django.urls import path
from . import views

app_name = "cart_order"

urlpatterns = [
    path("", views.cart_view, name="cart_view"),
    path("add/<int:book_id>/", views.add_to_cart, name="add_to_cart"),
    path("item/<int:item_id>/update/", views.update_cart_item, name="update_cart_item"),
    path("item/<int:item_id>/remove/", views.remove_cart_item, name="remove_cart_item"),
    path("orders/", views.order_history, name="order_history"),
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("checkout/create-session/", views.create_checkout_session, name="create_checkout_session"),
    path("order/<int:order_id>/success/", views.order_success, name="order_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),

]