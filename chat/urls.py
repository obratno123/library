from django.urls import path
from .views import dialog_list, start_dialog, dialog_detail

app_name = "chat"

urlpatterns = [
    path("", dialog_list, name="dialog_list"),
    path("start/<int:user_id>/", start_dialog, name="start_dialog"),
    path("dialog/<int:dialog_id>/", dialog_detail, name="dialog_detail"),
]