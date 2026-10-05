from django.conf import settings
from django.db import models


class Notification(models.Model):
    TYPES = [(t, t.replace("_", " ").title()) for t in (
        "LEAVE", "PAYROLL", "DOCUMENT", "ATTENDANCE", "GOAL", "ANNOUNCEMENT", "BIRTHDAY",
        "ANNIVERSARY", "INTERVIEW", "ONBOARDING", "RECOGNITION", "SYSTEM")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=160)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPES, default="SYSTEM")
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "is_read"])]
