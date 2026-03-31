from django.shortcuts import render

def home_page(request):
    return render(request, "index.html")

def login_page(request):
    return render(request, "login.html")

def register_page(request):
    return render(request, "register.html")

def profile_page(request):
    return render(request, "profile.html")