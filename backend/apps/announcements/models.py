from django.conf import settings
from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    class Audience(models.TextChoices):
        COMPANY = "COMPANY", "Company"
        DEPARTMENT = "DEPARTMENT", "Department"

    class Priority(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        IMPORTANT = "IMPORTANT", "Important"
        URGENT = "URGENT", "Urgent"

    title = models.CharField(max_length=160)
    description = models.TextField()
    audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.COMPANY)
    department = models.ForeignKey("employees.Department", null=True, blank=True, on_delete=models.CASCADE)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "announcements"
        ordering = ["-published_at"]
