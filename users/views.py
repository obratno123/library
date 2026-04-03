from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Profile
import json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)

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
                full_name=username
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
    })