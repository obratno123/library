from django.urls import path
from .views import (
    chat_dialog,
    support_dialogs_list,
    support_dialog_detail,
)

app_name = "support_chat"

urlpatterns = [
    path("", chat_dialog, name="chat_dialog"),
    path("support/dialogs/", support_dialogs_list, name="support_dialogs_list"),
    path("support/dialog/<int:dialog_id>/", support_dialog_detail, name="support_dialog_detail"),
]