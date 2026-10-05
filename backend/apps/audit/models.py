from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    user_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=40, db_index=True)
    entity = models.CharField(max_length=40, db_index=True)
    entity_id = models.CharField(max_length=40, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-timestamp", "-id"]
