from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("tour", "paid_by", "amount", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("tour__title", "paid_by__email", "description")
