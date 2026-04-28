from django.shortcuts import render
from django.conf import settings
import stripe
# Create your views here.
from decimal import Decimal
from uuid import uuid4
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from catalog.models import Book
from service_entities.models import Payment, BookFileAccess
from .models import Cart, CartItem, Order, OrderItem
stripe.api_key = settings.STRIPE_SECRET_KEY


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
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, "checkout.html", context)

@login_required
@require_POST
@transaction.atomic
def create_checkout_session(request):

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
        status="pending",
        delivery_method=delivery_method,
        payment_method=payment_method,
        payment_status="pending",
        total_price=total_price,
        delivery_address=delivery_address if delivery_address else "Электронная доставка",
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

    line_items = []
    for item in items:
        line_items.append({
            "price_data": {
                "currency": "rub",
                "product_data": {
                    "name": item.book.title,
                },
                "unit_amount": int(item.price_at_time * 100),
            },
            "quantity": item.quantity,
        })

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=f"{settings.SITE_URL}/cart/order/{order.id}/success/?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.SITE_URL}/cart/checkout/",
        client_reference_id=str(order.id),
        metadata={
            "order_id": str(order.id),
            "user_id": str(request.user.id),
            "payment_method": payment_method,
        },
    )

    Payment.objects.create(
        order=order,
        amount=total_price,
        method=payment_method,
        status="pending",
        transaction_id=session.id,
    )

    return redirect(session.url, code=303)


# @login_required
# @transaction.atomic
# def create_order_and_pay(request):
    # if request.method != "POST":
        # return redirect("cart_order:checkout")

    # cart, created = Cart.objects.get_or_create(user=request.user)

    # items = (
        # cart.items
        # .select_related("book")
        # .order_by("id")
    # )

    # if not items.exists():
        # messages.error(request, "Корзина пуста.")
        # return redirect("cart_order:cart_view")

    # delivery_method = request.POST.get("delivery_method", "digital")
    # payment_method = request.POST.get("payment_method", "card")
    # delivery_address = request.POST.get("delivery_address", "").strip()

    # total_price = sum(item.price_at_time * item.quantity for item in items)

    # order = Order.objects.create(
        # user=request.user,
        # status="paid",
        # delivery_method=delivery_method,
        # payment_method=payment_method,
        # payment_status="paid",
        # total_price=total_price,
        # delivery_address=delivery_address if delivery_address else "Электронная доставка",
        # paid_at=timezone.now(),
    # )

    # order_items = []
    # for item in items:
        # order_items.append(
            # OrderItem(
                # order=order,
                # book=item.book,
                # quantity=item.quantity,
                # price_at_time=item.price_at_time,
            # )
        # )
    # OrderItem.objects.bulk_create(order_items)

    # Payment.objects.create(
        # order=order,
        # amount=total_price,
        # method=payment_method,
        # status="paid",
        # transaction_id=str(uuid4()),
    # )

    # for item in items:
        # if item.book.ebook_file:
            # BookFileAccess.objects.get_or_create(
                # user=request.user,
                # book=item.book,
                # order=order,
                # defaults={
                    # "access_granted_at": timezone.now(),
                    # "expires_at": None,
                # }
            # )

    # items.delete()

    # messages.success(request, "Оплата прошла успешно. Заказ создан.")
    # return redirect("cart_order:order_success", order_id=order.id)
   
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

@csrf_exempt
@transaction.atomic
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        metadata = session["metadata"]
        order_id = metadata["order_id"] if "order_id" in metadata else session["client_reference_id"]

        if not order_id:
            return HttpResponse(status=200)

        try:
            order = Order.objects.prefetch_related("items__book").get(id=order_id)
        except Order.DoesNotExist:
            return HttpResponse(status=200)

        if order.payment_status != "paid":
            order.status = "paid"
            order.payment_status = "paid"
            order.paid_at = timezone.now()

            if order.delivery_method == "digital":
                order.delivery_status = "completed"
            else:
                order.delivery_status = "preparing"

            order.save(update_fields=[
                "status",
                "payment_status",
                "paid_at",
                "delivery_status",
            ])

            Payment.objects.filter(
                order=order,
                transaction_id=session["id"]
            ).update(status="paid")

            for item in order.items.all():
                if item.book.ebook_file:
                    BookFileAccess.objects.get_or_create(
                        user=order.user,
                        book=item.book,
                        order=order,
                        defaults={
                            "access_granted_at": timezone.now(),
                            "expires_at": None,
                        }
                    )

            CartItem.objects.filter(cart__user=order.user).delete()

    return HttpResponse(status=200)
@login_required
def order_history(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items__book")
        .order_by("-created_at")
    )

    return render(request, "order_history.html", {
        "orders": orders
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__book"),
        id=order_id,
        user=request.user
    )

    return render(request, "order_detail.html", {
        "order": order
    })