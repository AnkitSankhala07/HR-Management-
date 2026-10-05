"""Leave workflow: validation, overlap detection, balances, approval (transactional)."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.notifications.services import notify, notify_roles

from .models import LeaveBalance, LeaveRequest, LeaveType

DEFAULT_TYPES = [("Paid Leave", "PAID", 12, True, True), ("Sick Leave", "SICK", 7, True, True),
                 ("Casual Leave", "CASUAL", 5, True, True), ("Unpaid Leave", "UNPAID", 0, False, False),
                 ("Emergency Leave", "EMERGENCY", 3, True, True)]


def ensure_leave_types():
    if LeaveType.objects.count() < len(DEFAULT_TYPES):
        for name, code, alloc, paid, track in DEFAULT_TYPES:
            LeaveType.objects.get_or_create(code=code, defaults=dict(name=name, annual_allocation=alloc, is_paid=paid, tracks_balance=track))


def ensure_balances(employee, year: int | None = None):
    ensure_leave_types()
    year = year or date.today().year
    for lt in LeaveType.objects.filter(tracks_balance=True):
        LeaveBalance.objects.get_or_create(employee=employee, leave_type=lt, year=year, defaults={"allocated": lt.annual_allocation})


def working_days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1) if (start + timedelta(days=i)).weekday() < 5]


@transaction.atomic
def apply_leave(request, employee, leave_type, start_date, end_date, reason) -> LeaveRequest:
    if end_date < start_date:
        raise ServiceError("End date cannot be before start date.", 400, {"end_date": "End date cannot be before start date."})
    if start_date < date.today() - timedelta(days=30):
        raise ServiceError("Start date is too far in the past.", 400, {"start_date": "Too far in the past."})
    days = working_days(start_date, end_date)
    if not days:
        raise ServiceError("Selected range contains no working days.", 400)
    if LeaveRequest.objects.filter(employee=employee, status__in=["PENDING", "APPROVED"],
                                   start_date__lte=end_date, end_date__gte=start_date).exists():
        raise ServiceError("This overlaps with an existing leave request.", 409)
    total = Decimal(len(days))
    if leave_type.tracks_balance:
        ensure_balances(employee, start_date.year)
        bal = LeaveBalance.objects.get(employee=employee, leave_type=leave_type, year=start_date.year)
        if bal.remaining < total:
            raise ServiceError(f"Insufficient {leave_type.name} balance ({bal.remaining} days left).", 400)
    lr = LeaveRequest.objects.create(employee=employee, leave_type=leave_type, start_date=start_date,
                                     end_date=end_date, total_days=total, reason=reason)
    audit.log(request, "LEAVE_CREATED", "LeaveRequest", lr.pk, new={"type": leave_type.code, "days": str(total)})
    msg = f"{employee.full_name} requested {total} day(s) of {leave_type.name} ({start_date} to {end_date})."
    if employee.manager and employee.manager.user.is_active:
        notify(employee.manager.user, "New leave request", msg, "LEAVE", "/leave/", email=True)
    notify_roles(R.HR_ROLES, "New leave request", msg, "LEAVE", "/leave/", exclude=employee.manager.user if employee.manager else None)
    notify(employee.user, "Leave submitted", f"Your {leave_type.name} request is pending approval.", "LEAVE", "/leave/", email=True)
    return lr


def can_review(user, lr: LeaveRequest) -> bool:
    if lr.employee.user_id == user.pk:
        return False   # nobody approves their own leave
    if user.role in R.HR_ROLES:
        return True
    return user.role == R.MANAGER and lr.employee.manager_id == getattr(user.employee, "pk", None)


@transaction.atomic
def review_leave(request, lr_id: int, approve: bool, comment: str = "") -> LeaveRequest:
    lr = LeaveRequest.objects.select_for_update().select_related("employee__user", "leave_type").get(pk=lr_id)
    if not can_review(request.user, lr):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("You are not allowed to review this request.")
    if lr.status != LeaveRequest.Status.PENDING:
        raise ServiceError(f"Request already {lr.status.lower()}.", 409)
    if not approve and not comment.strip():
        raise ServiceError("A comment is required when rejecting.", 400, {"comment": "Required when rejecting."})
    if approve:
        if lr.leave_type.tracks_balance:
            ensure_balances(lr.employee, lr.start_date.year)
            bal = LeaveBalance.objects.select_for_update().get(employee=lr.employee, leave_type=lr.leave_type, year=lr.start_date.year)
            if bal.remaining < lr.total_days:
                raise ServiceError("Employee no longer has enough balance.", 400)
            bal.used += lr.total_days
            bal.save(update_fields=["used"])
        from apps.attendance.models import Attendance
        for d in working_days(lr.start_date, lr.end_date):
            rec, created = Attendance.objects.get_or_create(employee=lr.employee, attendance_date=d,
                                                            defaults={"status": Attendance.Status.LEAVE, "remarks": lr.leave_type.name})
            if not created and not rec.check_in:
                rec.status, rec.remarks = Attendance.Status.LEAVE, lr.leave_type.name
                rec.save(update_fields=["status", "remarks"])
    lr.status = LeaveRequest.Status.APPROVED if approve else LeaveRequest.Status.REJECTED
    lr.admin_comment, lr.reviewed_by, lr.reviewed_at = comment, request.user, timezone.now()
    lr.save()
    word = "approved" if approve else "rejected"
    audit.log(request, "LEAVE_APPROVED" if approve else "LEAVE_REJECTED", "LeaveRequest", lr.pk, new={"comment": comment})
    notify(lr.employee.user, f"Leave {word}", f"Your {lr.leave_type.name} ({lr.start_date} to {lr.end_date}) was {word}. {comment}".strip(),
           "LEAVE", "/leave/", email=True)
    return lr


@transaction.atomic
def cancel_leave(request, lr_id: int):
    lr = LeaveRequest.objects.select_for_update().get(pk=lr_id)
    if lr.employee.user_id != request.user.pk:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied()
    if lr.status != LeaveRequest.Status.PENDING:
        raise ServiceError("Only pending requests can be cancelled.", 409)
    lr.status = LeaveRequest.Status.CANCELLED
    lr.save(update_fields=["status", "updated_at"])
    return lr
