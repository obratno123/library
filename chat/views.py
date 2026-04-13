from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import Dialog, Message


from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .models import Dialog


@login_required
@require_GET
def dialog_list(request):
    query = request.GET.get("q", "").strip()

    dialogs = (
        Dialog.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        )
        .annotate(messages_count=Count("messages"))
        .filter(messages_count__gt=0)
        .select_related("user1", "user2")
        .order_by("-updated_at")
    )

    dialog_data = []
    for dialog in dialogs:
        other_user = dialog.user2 if dialog.user1 == request.user else dialog.user1
        dialog_data.append({
            "dialog": dialog,
            "other_user": other_user,
        })

    users = User.objects.exclude(id=request.user.id).select_related("profile")

    if query:
        users = users.filter(username__icontains=query)

    context = {
        "dialog_data": dialog_data,
        "users": users[:20],
        "query": query,
    }
    return render(request, "dialog_list.html", context)


@login_required
@require_GET
def start_dialog(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    if other_user == request.user:
        return redirect("chat:dialog_list")

    dialog = Dialog.objects.filter(
        Q(user1=request.user, user2=other_user) |
        Q(user1=other_user, user2=request.user)
    ).first()

    if not dialog:
        dialog = Dialog.objects.create(
            user1=request.user,
            user2=other_user
        )

    return redirect("chat:dialog_detail", dialog_id=dialog.id)


@login_required
@require_GET
def dialog_detail(request, dialog_id):
    dialog = get_object_or_404(
        Dialog.objects.select_related("user1", "user2"),
        id=dialog_id
    )

    if request.user not in [dialog.user1, dialog.user2]:
        return redirect("chat:dialog_list")

    messages = dialog.messages.select_related("sender")

    dialog.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(is_read=True)

    context = {
        "dialog": dialog,
        "messages": messages,
        "other_user": dialog.get_other_user(request.user),
    }
    return render(request, "dialog_detail.html", context)