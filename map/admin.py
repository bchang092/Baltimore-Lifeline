from django.contrib import admin

from .models import CommunityFeedback


@admin.register(CommunityFeedback)
class CommunityFeedbackAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "name", "approved", "created_at")
    list_filter = ("approved", "category", "created_at")
    search_fields = ("title", "body", "name")
    ordering = ("-created_at",)
    actions = ("approve_feedback", "hide_feedback")

    @admin.action(description="Approve selected feedback (publish)")
    def approve_feedback(self, request, queryset):
        count = queryset.update(approved=True)
        self.message_user(request, f"Published {count} feedback post(s).")

    @admin.action(description="Hide selected feedback (mark unapproved)")
    def hide_feedback(self, request, queryset):
        count = queryset.update(approved=False)
        self.message_user(request, f"Hidden {count} feedback post(s).")
