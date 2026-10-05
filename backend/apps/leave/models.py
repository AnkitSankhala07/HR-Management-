from django.conf import settings
from django.db import models

from apps.common.models import TimeStamped


class LeaveType(models.Model):
    name = models.CharField(max_length=40, unique=True)
    code = models.CharField(max_length=12, unique=True)
    annual_allocation = models.PositiveSmallIntegerField(default=0)
    is_paid = models.BooleanField(default=True)
    tracks_balance = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_types"

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        db_table = "leave_balances"
        constraints = [models.UniqueConstraint(fields=["employee", "leave_type", "year"], name="uniq_balance")]

    @property
    def remaining(self):
        return self.allocated - self.used


class LeaveRequest(TimeStamped):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    admin_comment = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_leaves")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_requests"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["employee", "start_date", "end_date"])]
