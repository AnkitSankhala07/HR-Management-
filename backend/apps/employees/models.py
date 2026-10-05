from django.conf import settings
from django.db import models

from apps.common.models import TimeStamped


class Department(TimeStamped):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "departments"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Designation(TimeStamped):
    title = models.CharField(max_length=80)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="designations")

    class Meta:
        db_table = "designations"
        ordering = ["title"]
        constraints = [models.UniqueConstraint(fields=["title", "department"], name="uniq_designation_dept")]

    def __str__(self):
        return self.title


class Employee(TimeStamped):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full time"
        PART_TIME = "PART_TIME", "Part time"
        CONTRACT = "CONTRACT", "Contract"
        INTERN = "INTERN", "Intern"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee")
    employee_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="employees")
    designation = models.ForeignKey(Designation, null=True, blank=True, on_delete=models.SET_NULL, related_name="employees")
    manager = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    joining_date = models.DateField()
    employment_type = models.CharField(max_length=12, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)

    class Meta:
        db_table = "employees"
        ordering = ["first_name", "last_name"]
        indexes = [models.Index(fields=["department"]), models.Index(fields=["joining_date"])]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()

    def __str__(self):
        return f"{self.employee_id} {self.full_name}"
