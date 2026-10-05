"""Candidate -> Employee conversion (single atomic transaction)."""
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction

from apps.accounts.services import issue_token
from apps.accounts.models import PasswordResetToken
from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.employees.services import create_employee, next_employee_id
from apps.notifications.services import notify, notify_roles, send_email_safe

from .models import Onboarding, OnboardingTask

CHECKLIST = ["Identity verification", "Offer letter signed", "Joining documents", "Bank details",
             "Emergency contact", "IT equipment", "Email account", "HR orientation", "Manager introduction"]


@transaction.atomic
def onboard_candidate(request, application):
    from apps.recruitment.models import Application, Offer
    app = Application.objects.select_for_update().select_related("candidate", "job", "offer").get(pk=application.pk)
    if app.stage == Application.Stage.HIRED:
        raise ServiceError("Candidate is already hired.", 409)
    offer = getattr(app, "offer", None)
    if not offer or offer.status != Offer.Status.ACCEPTED:
        raise ServiceError("The candidate must accept the offer before being hired.", 400)
    c, job = app.candidate, app.job
    first, _, last = c.name.strip().partition(" ")
    temp_password = secrets.token_urlsafe(9) + "aA1!"
    emp = create_employee(
        request=request, employee_id=next_employee_id(), email=c.email, first_name=first, last_name=last or "-",
        phone=c.phone, password=temp_password, role=R.EMPLOYEE, email_verified=True, joining_date=offer.joining_date,
        department=offer.department or job.department, designation=job.designation, manager=job.hiring_manager)
    ob = Onboarding.objects.create(employee=emp, application=app)
    OnboardingTask.objects.bulk_create([OnboardingTask(onboarding=ob, title=t, due_date=offer.joining_date + timedelta(days=7)) for t in CHECKLIST])
    app.stage = Application.Stage.HIRED
    app.save(update_fields=["stage", "updated_at"])
    audit.log(request, "CANDIDATE_STAGE_CHANGED", "Application", app.pk, old={"stage": "OFFER"}, new={"stage": "HIRED", "employee": emp.employee_id})
    notify(emp.user, "Welcome to Dayflow!", "Your onboarding checklist is ready. Complete your profile and documents.", "ONBOARDING", "/onboarding/")
    notify_roles(R.HR_ROLES, "New hire onboarding", f"{emp.full_name} ({emp.employee_id}) was hired and onboarding has started.", "ONBOARDING", "/onboarding/")
    raw = issue_token(emp.user, PasswordResetToken, 72)
    transaction.on_commit(lambda: send_email_safe(
        c.email, "Welcome to Dayflow - set your password",
        f"Hi {first},\n\nYour employee ID is {emp.employee_id}. Set your password: {settings.SITE_URL}/reset-password/{raw}/"))
    return emp, temp_password
