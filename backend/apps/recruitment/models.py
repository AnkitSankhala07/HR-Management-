import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStamped


class Job(TimeStamped):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    title = models.CharField(max_length=120)
    department = models.ForeignKey("employees.Department", null=True, on_delete=models.SET_NULL, related_name="jobs")
    designation = models.ForeignKey("employees.Designation", null=True, blank=True, on_delete=models.SET_NULL)
    hiring_manager = models.ForeignKey("employees.Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    description = models.TextField()
    skills_required = models.CharField(max_length=300, blank=True)
    experience_min = models.PositiveSmallIntegerField(default=0)
    location = models.CharField(max_length=80, default="Ahmedabad")
    employment_type = models.CharField(max_length=12, default="FULL_TIME")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "jobs"
        ordering = ["-created_at"]


class Candidate(TimeStamped):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    resume = models.FileField(upload_to="resumes/%Y/%m/", null=True, blank=True)
    skills = models.CharField(max_length=300, blank=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    education = models.CharField(max_length=160, blank=True)
    current_company = models.CharField(max_length=120, blank=True)
    expected_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notice_period_days = models.PositiveSmallIntegerField(default=0)
    source = models.CharField(max_length=40, default="Careers Page")

    class Meta:
        db_table = "candidates"
        ordering = ["-created_at"]


class Application(models.Model):
    class Stage(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        SCREENING = "SCREENING", "Screening"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        INTERVIEW = "INTERVIEW", "Interview"
        OFFER = "OFFER", "Offer"
        HIRED = "HIRED", "Hired"
        REJECTED = "REJECTED", "Rejected"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.APPLIED, db_index=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "applications"
        ordering = ["-applied_at"]
        constraints = [models.UniqueConstraint(fields=["candidate", "job"], name="uniq_candidate_job")]


class Interview(TimeStamped):
    TYPES = [("TECHNICAL", "Technical"), ("HR", "HR"), ("MANAGERIAL", "Managerial"), ("FINAL", "Final")]
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    interview_type = models.CharField(max_length=12, choices=TYPES, default="TECHNICAL")
    scheduled_at = models.DateTimeField()
    interviewers = models.ManyToManyField("employees.Employee", related_name="interviews", blank=True)
    meeting_link = models.URLField(blank=True)
    status = models.CharField(max_length=10, default="SCHEDULED")   # SCHEDULED / COMPLETED / CANCELLED

    class Meta:
        db_table = "interviews"
        ordering = ["scheduled_at"]


class InterviewFeedback(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name="feedback")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    rating = models.PositiveSmallIntegerField()
    recommendation = models.CharField(max_length=10, default="MAYBE")   # YES / MAYBE / NO
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interview_feedback"
        constraints = [models.UniqueConstraint(fields=["interview", "reviewer"], name="uniq_feedback_per_reviewer")]


class Offer(TimeStamped):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Sent"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="offer")
    position = models.CharField(max_length=120)
    department = models.ForeignKey("employees.Department", null=True, on_delete=models.SET_NULL)
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    joining_date = models.DateField()
    offer_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        db_table = "offers"
        ordering = ["-created_at"]
