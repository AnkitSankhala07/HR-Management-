from django.db import models

from apps.common.models import TimeStamped


class Attendance(TimeStamped):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        HALF_DAY = "HALF_DAY", "Half Day"
        LEAVE = "LEAVE", "Leave"
        HOLIDAY = "HOLIDAY", "Holiday"
        WFH = "WFH", "Work From Home"

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="attendance")
    attendance_date = models.DateField(db_index=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    remarks = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "attendance"
        ordering = ["-attendance_date"]
        constraints = [models.UniqueConstraint(fields=["employee", "attendance_date"], name="uniq_employee_date")]
        indexes = [models.Index(fields=["attendance_date", "status"])]


class AttendanceBreak(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="breaks")
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attendance_breaks"
        ordering = ["start"]
