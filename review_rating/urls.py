from django.urls import path
from .views import add_or_edit_review, user_reviews

app_name = "review_rating"

urlpatterns = [
    path("book/<slug:slug>/review/", add_or_edit_review, name="add_or_edit_review"),
    path("my-reviews/", user_reviews, name="user_reviews"),
]