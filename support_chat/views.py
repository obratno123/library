import random

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .models import SupportDialog


def is_support(user):
    return (
        hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "support"
    )


def choose_support_user():
    support_users = list(
        User.objects.filter(profile__role__name="support")
    )

    if not support_users:
        raise ValueError("Нет пользователей с ролью support")

    return random.choice(support_users)


@login_required
@require_GET
def chat_dialog(request):
    if is_support(request.user):
        return redirect("support_chat:support_dialogs_list")

    dialog = SupportDialog.objects.filter(user=request.user).select_related(
        "user",
        "support_user"
    ).first()

    if not dialog:
        support_user = choose_support_user()
        dialog = SupportDialog.objects.create(
            user=request.user,
            support_user=support_user
        )

    messages = dialog.messages.select_related("sender")

    dialog.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(is_read=True)

    context = {
        "dialog": dialog,
        "messages": messages,
        "support_user": dialog.support_user,
    }
    return render(request, "chat_dialog.html", context)


@login_required
@require_GET
def support_dialogs_list(request):
    if not is_support(request.user):
        return redirect("support_chat:chat_dialog")

    dialogs = SupportDialog.objects.filter(
        support_user=request.user
    ).select_related("user", "support_user").order_by("-updated_at")

    return render(request, "dialogs_list.html", {
        "dialogs": dialogs,
    })


@login_required
@require_GET
def support_dialog_detail(request, dialog_id):
    if not is_support(request.user):
        return redirect("support_chat:chat_dialog")

    dialog = get_object_or_404(
        SupportDialog.objects.select_related("user", "support_user"),
        id=dialog_id,
        support_user=request.user
    )

    messages = dialog.messages.select_related("sender")

    dialog.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(is_read=True)

    return render(request, "support_dialog_detail.html", {
        "dialog": dialog,
        "messages": messages,
    })