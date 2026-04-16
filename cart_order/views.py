from django.shortcuts import render

# Create your views here.
from decimal import Decimal
from uuid import uuid4
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseBadRequest

from catalog.models import Book
from service_entities.models import Payment, BookFileAccess
from .models import Cart, CartItem, Order, OrderItem



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
  
@login_required
def checkout_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)

    items = (
        cart.items
        .select_related("book")
        .prefetch_related("book__authors")
        .order_by("id")
    )

    if not items.exists():
        messages.error(request, "Корзина пуста.")
        return redirect("cart_order:cart_view")

    subtotal = sum(item.price_at_time * item.quantity for item in items)
    delivery_price = Decimal("0.00")
    total_price = subtotal + delivery_price

    context = {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "delivery_price": delivery_price,
        "total_price": total_price,
    }
    return render(request, "checkout.html", context)


@login_required
@transaction.atomic
def create_order_and_pay(request):
    if request.method != "POST":
        return redirect("cart_order:checkout")

    cart, created = Cart.objects.get_or_create(user=request.user)

    items = (
        cart.items
        .select_related("book")
        .order_by("id")
    )

    if not items.exists():
        messages.error(request, "Корзина пуста.")
        return redirect("cart_order:cart_view")

    delivery_method = request.POST.get("delivery_method", "digital")
    payment_method = request.POST.get("payment_method", "card")
    delivery_address = request.POST.get("delivery_address", "").strip()

    total_price = sum(item.price_at_time * item.quantity for item in items)

    order = Order.objects.create(
        user=request.user,
        status="paid",
        delivery_method=delivery_method,
        payment_method=payment_method,
        payment_status="paid",
        total_price=total_price,
        delivery_address=delivery_address if delivery_address else "Электронная доставка",
        paid_at=timezone.now(),
    )

    order_items = []
    for item in items:
        order_items.append(
            OrderItem(
                order=order,
                book=item.book,
                quantity=item.quantity,
                price_at_time=item.price_at_time,
            )
        )
    OrderItem.objects.bulk_create(order_items)

    Payment.objects.create(
        order=order,
        amount=total_price,
        method=payment_method,
        status="paid",
        transaction_id=str(uuid4()),
    )

    for item in items:
        if item.book.ebook_file:
            BookFileAccess.objects.get_or_create(
                user=request.user,
                book=item.book,
                order=order,
                defaults={
                    "access_granted_at": timezone.now(),
                    "expires_at": None,
                }
            )

    items.delete()

    messages.success(request, "Оплата прошла успешно. Заказ создан.")
    return redirect("cart_order:order_success", order_id=order.id)
   
@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__book"),
        id=order_id,
        user=request.user
    )
    return render(request, "order_success.html", {
        "order": order
    })