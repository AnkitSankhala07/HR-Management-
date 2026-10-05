"""Recruitment workflow rules."""
from datetime import date

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.notifications.services import notify, notify_roles, send_email_safe

from .models import Application, Candidate, Interview, Job, Offer

ORDER = ["APPLIED", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED"]


@transaction.atomic
def apply_to_job(request, job: Job, data: dict, resume=None) -> Application:
    if job.status != Job.Status.OPEN:
        raise ServiceError("This job is not accepting applications.", 400)
    cand, created = Candidate.objects.get_or_create(email=data["email"].lower(), defaults={k: v for k, v in data.items() if k != "email"})
    if not created:   # never let a public applicant overwrite an existing profile's data - only fill blanks
        for k, v in data.items():
            if k != "email" and v and not getattr(cand, k):
                setattr(cand, k, v)
    if resume:
        cand.resume = resume
    cand.save()
    try:
        with transaction.atomic():
            app = Application.objects.create(candidate=cand, job=job)
    except IntegrityError:
        raise ServiceError("You have already applied for this job.", 409)
    audit.log(request, "CANDIDATE_CREATED", "Candidate", cand.pk, new={"job": job.pk, "email": cand.email}, user=None)
    notify_roles(R.RECRUITMENT_ROLES, "New application", f"{cand.name} applied for {job.title}.", "SYSTEM", "/recruitment/pipeline/")
    send_email_safe(cand.email, f"Application received - {job.title}", f"Hi {cand.name},\n\nThanks for applying for {job.title} at Dayflow. We'll be in touch.")
    return app


@transaction.atomic
def move_stage(request, app_id: int, stage: str, notes: str = "") -> Application:
    app = Application.objects.select_for_update().select_related("candidate", "job").get(pk=app_id)
    old = app.stage
    if stage not in ORDER + ["REJECTED"]:
        raise ServiceError("Invalid stage.", 400)
    if old in ("HIRED", "REJECTED"):
        raise ServiceError(f"Application is already {old.lower()}.", 409)
    if stage == "REJECTED":
        pass
    elif stage in ("OFFER", "HIRED"):
        raise ServiceError(f"Use the offer workflow to reach {stage.title()} (create an offer / hire action).", 400)
    elif ORDER.index(stage) <= ORDER.index(old):
        raise ServiceError("Candidates can only move forward in the pipeline.", 400)
    app.stage = stage
    if notes:
        app.notes = (app.notes + "\n" + notes).strip()
    app.save()
    audit.log(request, "CANDIDATE_STAGE_CHANGED", "Application", app.pk, old={"stage": old}, new={"stage": stage})
    if stage == "REJECTED":
        Offer.objects.filter(application=app, status__in=["DRAFT", "SENT"]).update(status="REJECTED")
    return app


@transaction.atomic
def schedule_interview(request, app: Application, *, interview_type, scheduled_at, interviewers, meeting_link="") -> Interview:
    if app.stage not in ("SHORTLISTED", "INTERVIEW"):
        raise ServiceError("Only shortlisted candidates can be scheduled for interview.", 400)
    if scheduled_at < timezone.now():
        raise ServiceError("Interview must be scheduled in the future.", 400, {"scheduled_at": "Must be in the future."})
    iv = Interview.objects.create(application=app, interview_type=interview_type, scheduled_at=scheduled_at, meeting_link=meeting_link)
    iv.interviewers.set(interviewers)
    if app.stage != "INTERVIEW":
        move_stage(request, app.pk, "INTERVIEW")
    when = timezone.localtime(scheduled_at).strftime("%d %b %Y, %I:%M %p")
    for e in interviewers:
        notify(e.user, "Interview scheduled", f"{app.candidate.name} - {app.job.title} on {when}", "INTERVIEW", "/recruitment/interviews/", email=True)
    send_email_safe(app.candidate.email, f"Interview scheduled - {app.job.title}", f"Your {interview_type.title()} interview is on {when}. {meeting_link}")
    audit.log(request, "INTERVIEW_SCHEDULED", "Interview", iv.pk, new={"application": app.pk, "at": str(scheduled_at)})
    return iv


@transaction.atomic
def create_offer(request, app: Application, *, salary, joining_date, expiry_date, position="", department=None, send=False) -> Offer:
    app = Application.objects.select_for_update().get(pk=app.pk)
    if app.stage not in ("INTERVIEW", "OFFER"):
        raise ServiceError("An offer can only be generated for candidates in the interview stage.", 400)
    if hasattr(app, "offer"):
        raise ServiceError("An offer already exists for this application.", 409)
    if expiry_date < date.today() or joining_date < date.today():
        raise ServiceError("Joining and expiry dates must be in the future.", 400)
    offer = Offer.objects.create(application=app, position=position or app.job.title, department=department or app.job.department,
                                 salary=salary, joining_date=joining_date, offer_date=date.today(), expiry_date=expiry_date)
    old = app.stage
    app.stage = "OFFER"
    app.save(update_fields=["stage", "updated_at"])
    audit.log(request, "OFFER_CREATED", "Offer", offer.pk, new={"application": app.pk})
    audit.log(request, "CANDIDATE_STAGE_CHANGED", "Application", app.pk, old={"stage": old}, new={"stage": "OFFER"})
    if send:
        send_offer(request, offer)
    return offer


def send_offer(request, offer: Offer):
    if offer.status not in ("DRAFT", "SENT"):
        raise ServiceError(f"Offer is already {offer.status.lower()}.", 409)
    offer.status = "SENT"
    offer.save(update_fields=["status", "updated_at"])
    link = f"{settings.SITE_URL}/offer/{offer.token}/"
    send_email_safe(offer.application.candidate.email, f"Your offer from Dayflow - {offer.position}",
                    f"Congratulations {offer.application.candidate.name}!\n\nReview and respond to your offer: {link}\nValid until {offer.expiry_date}.")
    return offer


@transaction.atomic
def respond_offer(token, decision: str):
    offer = Offer.objects.select_for_update().select_related("application__candidate", "application__job").get(token=token)
    if offer.status != "SENT":
        raise ServiceError(f"This offer is {offer.status.lower()} and can no longer be changed.", 409)
    if offer.expiry_date < date.today():
        offer.status = "EXPIRED"
        offer.save(update_fields=["status"])
        raise ServiceError("This offer has expired.", 410)
    if decision not in ("accept", "reject"):
        raise ServiceError("Decision must be 'accept' or 'reject'.", 400)
    offer.status = "ACCEPTED" if decision == "accept" else "REJECTED"
    offer.save(update_fields=["status", "updated_at"])
    app = offer.application
    audit.log(None, f"OFFER_{offer.status}", "Offer", offer.pk, new={"candidate": app.candidate.email})
    notify_roles(R.RECRUITMENT_ROLES, f"Offer {offer.status.lower()}", f"{app.candidate.name} {offer.status.lower()} the {offer.position} offer.", "SYSTEM", "/recruitment/offers/")
    if decision == "reject":
        app.stage = "REJECTED"
        app.save(update_fields=["stage", "updated_at"])
    elif settings.AUTO_HIRE_ON_ACCEPT:
        from apps.onboarding.services import onboard_candidate
        onboard_candidate(None, app)
    return offer
