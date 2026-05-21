from django.db import models


class CommunityFeedback(models.Model):
    CATEGORY_SUGGESTION = "suggestion"
    CATEGORY_CORRECTION = "correction"
    CATEGORY_BUG = "bug"
    CATEGORY_EXPERIENCE = "experience"

    CATEGORY_CHOICES = [
        (CATEGORY_SUGGESTION, "Suggestion"),
        (CATEGORY_CORRECTION, "Resource correction"),
        (CATEGORY_BUG, "Bug report"),
        (CATEGORY_EXPERIENCE, "Service experience"),
    ]

    name = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=24, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=160)
    body = models.TextField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
