from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Profile
import json

@require_http_methods(["POST"])
def register(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Невалидный JSON"}, status=400)

    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")

    if not username or not password:
        return JsonResponse({"error": "username и password обязательны"}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Пользователь уже существует"}, status=400)

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    Profile.objects.create(
        user=user,
        full_name=username
    )

    login(request, user)

    return JsonResponse({
        "message": "Пользователь зарегистрирован",
        "user_id": user.id,
        "username": user.username
    }, status=201)
    

@require_http_methods(["POST"])
def user_login(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Невалидный JSON"}, status=400)

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return JsonResponse({"error": "username и password обязательны"}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse({"error": "Неверный логин или пароль"}, status=401)

    login(request, user)

    return JsonResponse({
        "message": "Вход выполнен",
        "user_id": user.id,
        "username": user.username
    })

@require_http_methods(["POST"])
def user_logout(request):
    logout(request)
    return JsonResponse({"message": "Выход выполнен"})