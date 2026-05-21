from django.contrib import admin

from .models import CommunityFeedback


@admin.register(CommunityFeedback)
class CommunityFeedbackAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "name", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "body", "name")
    ordering = ("-created_at",)
    exclude = ("approved",)
