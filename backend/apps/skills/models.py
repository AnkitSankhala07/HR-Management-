from django.db import models


class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)
    category = models.CharField(max_length=40, blank=True)

    class Meta:
        db_table = "skills"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmployeeSkill(models.Model):
    class Level(models.IntegerChoices):
        BEGINNER = 1, "Beginner"
        INTERMEDIATE = 2, "Intermediate"
        ADVANCED = 3, "Advanced"
        EXPERT = 4, "Expert"

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, related_name="skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="holders")
    level = models.PositiveSmallIntegerField(choices=Level.choices, default=Level.BEGINNER)
    years_experience = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    certification = models.CharField(max_length=120, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employee_skills"
        constraints = [models.UniqueConstraint(fields=["employee", "skill"], name="uniq_employee_skill")]
