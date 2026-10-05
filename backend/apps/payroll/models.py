from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TimeStamped


class Payroll(TimeStamped):
    class PayStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        ON_HOLD = "ON_HOLD", "On Hold"

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="payrolls")
    pay_month = models.PositiveSmallIntegerField()
    pay_year = models.PositiveSmallIntegerField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=10, choices=PayStatus.choices, default=PayStatus.PENDING)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "payroll"
        ordering = ["-pay_year", "-pay_month"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "pay_month", "pay_year"], name="uniq_payroll_period"),
            models.CheckConstraint(condition=models.Q(pay_month__gte=1, pay_month__lte=12), name="payroll_month_1_12"),
        ]
        indexes = [models.Index(fields=["pay_year", "pay_month"])]

    def recalculate(self):
        """Backend is the only place totals are computed - client values are ignored."""
        self.gross_salary = self.basic_salary + self.hra + self.allowances + self.bonus
        self.net_salary = self.gross_salary - self.deductions
