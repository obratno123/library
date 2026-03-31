from django.contrib import admin
from .models import Payment, OrderStatusHistory, SupportMessage, BookFileAccess

admin.site.register(Payment)
admin.site.register(OrderStatusHistory)
admin.site.register(SupportMessage)
admin.site.register(BookFileAccess)
