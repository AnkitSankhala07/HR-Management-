from django.db import models


class Onboarding(models.Model):
    employee = models.OneToOneField("employees.Employee", on_delete=models.CASCADE, related_name="onboarding")
    application = models.OneToOneField("recruitment.Application", null=True, blank=True, on_delete=models.SET_NULL, related_name="onboarding")
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding"

    @property
    def progress(self):
        tasks = list(self.tasks.all())
        return round(100 * sum(t.status == "COMPLETED" for t in tasks) / len(tasks)) if tasks else 0


class OnboardingTask(models.Model):
    STATUSES = [("PENDING", "Pending"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed")]
    onboarding = models.ForeignKey(Onboarding, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=STATUSES, default="PENDING")
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "onboarding_tasks"
        ordering = ["id"]
