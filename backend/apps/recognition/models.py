from django.db import models


class Recognition(models.Model):
    CATEGORIES = [(c, c.replace("_", " ").title()) for c in ("TEAMWORK", "INNOVATION", "LEADERSHIP", "PROBLEM_SOLVING", "CUSTOMER_FOCUS", "LEARNING")]
    BADGES = [("PROBLEM_SOLVER", "Problem Solver"), ("TEAM_PLAYER", "Team Player"), ("INNOVATOR", "Innovator"),
              ("LEADER", "Leader"), ("FAST_LEARNER", "Fast Learner")]
    giver = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="recognitions_given")
    receiver = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="recognitions")
    category = models.CharField(max_length=20, choices=CATEGORIES)
    badge = models.CharField(max_length=20, choices=BADGES)
    message = models.CharField(max_length=400)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recognitions"
        ordering = ["-created_at"]
