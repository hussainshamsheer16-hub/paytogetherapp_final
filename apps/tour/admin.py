from django.contrib import admin
from .models import Tour
# Register your models here.

@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ("title", "description", "budget", "start_date", "end_date", "status", "created_by", "created_at")
    list_filter = ("status", "start_date", )
    search_fields = ("title", "description",)
    ordering = ("-created_at",)
