from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db import IntegrityError
import logging
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
import secrets
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Profile, PasswordResetCode, EmailVerificationCode


User = get_user_model()
logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    content_type = request.content_type or ""
    if "application/json" not in content_type:
        return JsonResponse({"error": "Ожидается application/json"}, status=400)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Невалидный JSON"}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()

    if not username:
        return JsonResponse({"error": "username обязателен"}, status=400)

    if not password:
        return JsonResponse({"error": "password обязателен"}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Пользователь уже существует"}, status=400)
    
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({"error": "Неверный email"}, status=400)
    try:
        temp_user = User(username=username, email=email)
        validate_password(password, user=temp_user)
    except ValidationError as e:
        return JsonResponse({"error": e.messages}, status=400)
    
    if email and User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email уже используется"}, status=400)
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email
            )
            Profile.objects.create(
                user=user,
                full_name=username,
                is_email_verified=False
            )
    except IntegrityError:
        return JsonResponse({"error": "Пользователь или email уже существует"}, status=400)
    except Exception as e:
        logger.exception(f"ошибка при регистрации {e}")
        return JsonResponse({"error": "Ошибка при регистрации"}, status=500)
        
    login(request, user)

    return JsonResponse({
        "message": "Пользователь зарегистрирован",
        "user_id": user.id,
        "username": user.username
    }, status=201)
    
@csrf_exempt
@require_http_methods(["POST"])
def user_login(request):
    content_type = request.content_type or ""
    if "application/json" not in content_type:
        return JsonResponse({"error": "Ожидается application/json"}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Невалидный JSON"}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username:
        return JsonResponse({"error": "username обязателен"}, status=400)

    if not password:
        return JsonResponse({"error": "password обязателен"}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse({"error": "Неверный логин или пароль"}, status=401)

    try:
        login(request, user)
    except Exception as e:
        logger.exception(f"ошибка при входе {e}")
        return JsonResponse({"error": "Ошибка при входе"}, status=500)

    return JsonResponse({
        "message": "Вход выполнен",
        "user_id": user.id,
        "username": user.username
    })
@csrf_exempt
@require_http_methods(["POST"])
def user_logout(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Не авторизован"}, status=401)
    logout(request)
    return JsonResponse({"message": "Выход выполнен"}, status=200)


@require_http_methods(["GET"])
def user_profile(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Не авторизован"}, status=401)

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({"error": "Профиль не найден"}, status=404)

    return JsonResponse({
        "user_id": request.user.id,
        "username": request.user.username,
        "email": request.user.email,
        "full_name": profile.full_name,
        "city": profile.city,
        "delivery_address": profile.delivery_address,
        "postal_code": profile.postal_code,
        "avatar_url": profile.avatar.url if profile.avatar else None,
        "is_email_verified": profile.is_email_verified,
        "email_verified_at": profile.email_verified_at.isoformat() if profile.email_verified_at else None,
    })
    
    
def generate_reset_code():
    return f"{secrets.randbelow(1000000):06d}"


def send_reset_code_email(user, code):
    context = {
        "user": user,
        "code": code,
        "site_name": "Букинист",
        "minutes": 10,
    }

    text_content = render_to_string("emails/password_reset_code_email.txt", context)
    html_content = render_to_string("emails/password_reset_code_email.html", context)

    msg = EmailMultiAlternatives(
        subject="Код восстановления пароля — Букинист",
        body=text_content,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    
def send_password_changed_email(user):
    context = {
        "user": user,
        "site_name": "Букинист",
    }

    text_content = render_to_string("emails/password_changed.txt", context)
    html_content = render_to_string("emails/password_changed.html", context)

    msg = EmailMultiAlternatives(
        subject="Пароль был изменён — Букинист",
        body=text_content,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    
def password_reset_resend_view(request):
    email = request.session.get("password_reset_email")
    if not email:
        return redirect("users:password_reset_request")

    user = User.objects.filter(email__iexact=email, is_active=True).first()

    if user and user.has_usable_password():
        PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)

        code = generate_reset_code()
        PasswordResetCode.objects.create(
            user=user,
            code_hash=make_password(code),
        )

        send_reset_code_email(user, code)

    return redirect("users:password_reset_code")


def password_reset_request_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        request.session["password_reset_email"] = email

        user = User.objects.filter(email__iexact=email, is_active=True).first()

        # Одинаковое поведение независимо от того, найден пользователь или нет
        if user and user.has_usable_password():
            PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)

            code = generate_reset_code()

            PasswordResetCode.objects.create(
                user=user,
                code_hash=make_password(code),
            )

            send_reset_code_email(user, code)

        return redirect("users:password_reset_code")

    return render(request, "password_reset_request.html")


def password_reset_code_view(request):
    error = None

    email = request.session.get("password_reset_email")
    if not email:
        return redirect("users:password_reset_request")

    if request.method == "POST":
        entered_code = (request.POST.get("code") or "").strip()

        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if not user or not user.has_usable_password():
            error = "Неверный или просроченный код."
        else:
            reset_obj = (
                PasswordResetCode.objects
                .filter(user=user, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if not reset_obj:
                error = "Неверный или просроченный код."
            elif reset_obj.is_expired():
                error = "Код истёк. Запросите новый."
            elif not check_password(entered_code, reset_obj.code_hash):
                error = "Неверный или просроченный код."
            else:
                reset_obj.is_used = True
                reset_obj.save(update_fields=["is_used"])

                request.session["password_reset_verified_user_id"] = user.id
                return redirect("users:password_reset_new")

    return render(request, "password_reset_code.html", {"error": error})


def password_reset_new_view(request):
    error = None

    user_id = request.session.get("password_reset_verified_user_id")
    if not user_id:
        return redirect("users:password_reset_request")

    user = User.objects.filter(id=user_id, is_active=True).first()
    if not user:
        return redirect("users:password_reset_request")

    if request.method == "POST":
        password = request.POST.get("password") or ""
        password_confirm = request.POST.get("password_confirm") or ""

        if password != password_confirm:
            error = "Пароли не совпадают."
        else:
            try:
                validate_password(password, user=user)
                user.set_password(password)
                user.save()
                
                send_password_changed_email(user)

                request.session.pop("password_reset_email", None)
                request.session.pop("password_reset_verified_user_id", None)

                return redirect("login_page")
            except ValidationError as exc:
                error = " ".join(exc.messages)

    return render(request, "password_reset_new.html", {"error": error})


@login_required
def edit_profile_page(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.username}
    )
    return render(request, "edit_profile.html", {
        "profile": profile
    })


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.username}
    )

    full_name = (request.POST.get("full_name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    city = (request.POST.get("city") or "").strip()
    delivery_address = (request.POST.get("delivery_address") or "").strip()
    postal_code = (request.POST.get("postal_code") or "").strip()
    avatar = request.FILES.get("avatar")

    if full_name:
        profile.full_name = full_name

    profile.city = city
    profile.delivery_address = delivery_address
    profile.postal_code = postal_code

    if avatar:
        profile.avatar = avatar

    old_email = request.user.email

    if email and email != old_email:
        request.user.email = email
        request.user.save(update_fields=["email"])

        profile.is_email_verified = False
        profile.email_verified_at = None

        EmailVerificationCode.objects.filter(
            user=request.user,
            is_used=False
        ).update(is_used=True)

    profile.save()

    messages.success(request, "Профиль обновлён.")
    return redirect("profile_page")

def generate_verification_code():
    return f"{secrets.randbelow(1000000):06d}"

def send_verification_email(user, code):
    context = {
        "user": user,
        "code": code,
        "site_name": "Букинист",
        "minutes": 10,
    }

    text_content = render_to_string("emails/email_verification.txt", context)
    html_content = render_to_string("emails/email_verification.html", context)

    msg = EmailMultiAlternatives(
        subject="Подтверждение почты — Букинист",
        body=text_content,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    
@login_required
def verify_email_view(request):
    error = None

    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.username}
    )

    if profile.is_email_verified:
        return redirect("profile_page")

    if request.method == "GET":
        active_code = (
            EmailVerificationCode.objects
            .filter(
                user=request.user,
                email=request.user.email,
                is_used=False
            )
            .order_by("-created_at")
            .first()
        )

        if not active_code or active_code.is_expired():
            EmailVerificationCode.objects.filter(
                user=request.user,
                email=request.user.email,
                is_used=False
            ).update(is_used=True)

            code = generate_verification_code()

            EmailVerificationCode.objects.create(
                user=request.user,
                email=request.user.email,
                code_hash=make_password(code),
            )

            send_verification_email(request.user, code)

    if request.method == "POST":
        entered_code = (request.POST.get("code") or "").strip()

        verify_obj = (
            EmailVerificationCode.objects
            .filter(
                user=request.user,
                email=request.user.email,
                is_used=False
            )
            .order_by("-created_at")
            .first()
        )

        if not verify_obj:
            error = "Код не найден."
        elif verify_obj.is_expired():
            error = "Код истёк. Запросите новый."
        elif not check_password(entered_code, verify_obj.code_hash):
            error = "Неверный код."
        else:
            verify_obj.is_used = True
            verify_obj.save(update_fields=["is_used"])

            profile.is_email_verified = True
            profile.email_verified_at = timezone.now()
            profile.save(update_fields=["is_email_verified", "email_verified_at"])

            return redirect("profile_page")

    return render(request, "verify_email.html", {"error": error})

@login_required
def resend_verification_email_view(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.username}
    )

    if profile.is_email_verified:
        return redirect("profile_page")

    EmailVerificationCode.objects.filter(
        user=request.user,
        email=request.user.email,
        is_used=False
    ).update(is_used=True)

    code = generate_verification_code()

    EmailVerificationCode.objects.create(
        user=request.user,
        email=request.user.email,
        code_hash=make_password(code),
    )

    send_verification_email(request.user, code)
    return redirect("verify_email")