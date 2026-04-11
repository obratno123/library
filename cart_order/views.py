from django.shortcuts import render

# Create your views here.
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseBadRequest

from catalog.models import Book
from .models import Cart, CartItem


@login_required
@require_GET
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)

    items = (
        cart.items
        .select_related("book")
        .prefetch_related("book__authors")
        .order_by("id")
    )

    total_items = sum(item.quantity for item in items)
    subtotal = sum(item.price_at_time * item.quantity for item in items)

    discount = Decimal("0.00")
    delivery_price = Decimal("0.00")
    total_price = subtotal - discount + delivery_price

    context = {
        "cart": cart,
        "items": items,
        "total_items": total_items,
        "subtotal": subtotal,
        "discount": discount,
        "delivery_price": delivery_price,
        "total_price": total_price,
    }
    return render(request, "cart.html", context)


@login_required
@require_POST
def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id, is_active=True)
    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        book=book,
        defaults={
            "quantity": 1,
            "price_at_time": book.price,
        }
    )

    if not item_created:
        cart_item.quantity += 1
        cart_item.save(update_fields=["quantity"])

    return redirect("cart_order:cart_view")


@login_required
@require_POST
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(
        CartItem.objects.select_related("cart"),
        id=item_id,
        cart__user=request.user
    )

    action = request.POST.get("action")

    if action == "increase":
        cart_item.quantity += 1
        cart_item.save(update_fields=["quantity"])

    elif action == "decrease":
        cart_item.quantity -= 1
        if cart_item.quantity <= 0:
            cart_item.delete()
        else:
            cart_item.save(update_fields=["quantity"])
            
    else:
        return HttpResponseBadRequest("Некорректное действие")

    return redirect("cart_order:cart_view")


@login_required
@require_POST
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )
    cart_item.delete()
    return redirect("cart_order:cart_view")