from django.conf import settings
from django.db import models

from apps.common.models import TimeStamped


class Document(TimeStamped):
    class Category(models.TextChoices):
        OFFER = "OFFER_LETTER", "Offer Letter"
        JOINING = "JOINING_LETTER", "Joining Letter"
        EXPERIENCE = "EXPERIENCE_LETTER", "Experience Letter"
        SALARY = "SALARY_SLIP", "Salary Slip"
        CERT = "CERTIFICATE", "Certificate"
        IDENTITY = "IDENTITY", "Identity Document"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        EXPIRED = "EXPIRED", "Expired"
        REJECTED = "REJECTED", "Rejected"

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="documents")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    title = models.CharField(max_length=120)
    file = models.FileField(upload_to="documents/%Y/%m/")
    original_name = models.CharField(max_length=150)
    mime_type = models.CharField(max_length=50)
    size = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "documents"
        ordering = ["-created_at"]
