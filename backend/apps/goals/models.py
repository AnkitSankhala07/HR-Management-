from datetime import date

from django.db import models

from apps.common.models import TimeStamped


class Goal(TimeStamped):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        OVERDUE = "OVERDUE", "Overdue"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    owner = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="goals")
    manager = models.ForeignKey("employees.Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    start_date = models.DateField(default=date.today)
    due_date = models.DateField()
    progress = models.PositiveSmallIntegerField(default=0)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NOT_STARTED, db_index=True)

    class Meta:
        db_table = "goals"
        ordering = ["due_date"]

    def refresh_status(self):
        if self.progress >= 100:
            self.status = self.Status.COMPLETED
        elif self.due_date < date.today():
            self.status = self.Status.OVERDUE
        else:
            self.status = self.Status.IN_PROGRESS if self.progress > 0 else self.Status.NOT_STARTED

    def save(self, *a, **kw):
        self.progress = max(0, min(100, self.progress))
        self.refresh_status()
        super().save(*a, **kw)
