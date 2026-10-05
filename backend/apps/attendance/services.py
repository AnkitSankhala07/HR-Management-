"""Attendance rules. All timestamps come from the SERVER clock, never the browser."""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.exceptions import ServiceError

from .models import Attendance, AttendanceBreak


def _hours(td) -> Decimal:
    return Decimal(td.total_seconds() / 3600).quantize(Decimal("0.01"))


@transaction.atomic
def check_in(employee, work_from_home: bool = False) -> Attendance:
    now = timezone.now()
    today = timezone.localdate(now)
    rec = Attendance.objects.select_for_update().filter(employee=employee, attendance_date=today).first()
    if rec and rec.check_in:
        raise ServiceError("You have already checked in today.", 409)
    if rec and rec.status == Attendance.Status.LEAVE:
        raise ServiceError("You are on approved leave today.", 409)
    status = Attendance.Status.WFH if work_from_home else Attendance.Status.PRESENT
    try:
        if rec:
            rec.check_in, rec.status = now, status
            rec.save()
        else:
            rec = Attendance.objects.create(employee=employee, attendance_date=today, check_in=now, status=status)
    except IntegrityError:
        raise ServiceError("You have already checked in today.", 409)
    return rec


@transaction.atomic
def check_out(employee) -> Attendance:
    now = timezone.now()
    rec = Attendance.objects.select_for_update().filter(employee=employee, attendance_date=timezone.localdate(now)).first()
    if not rec or not rec.check_in:
        raise ServiceError("You must check in before checking out.", 409)
    if rec.check_out:
        raise ServiceError("You have already checked out today.", 409)
    for b in rec.breaks.filter(end__isnull=True):
        b.end = now
        b.save(update_fields=["end"])
    worked = now - rec.check_in - sum((b.end - b.start for b in rec.breaks.all()), timedelta())
    rec.check_out, rec.total_hours = now, max(_hours(worked), Decimal("0"))
    rec.overtime_hours = max(rec.total_hours - Decimal(settings.WORK_DAY_HOURS), Decimal("0"))
    if rec.status != Attendance.Status.WFH and rec.total_hours < Decimal(settings.WORK_DAY_HOURS) / 2:
        rec.status = Attendance.Status.HALF_DAY
    rec.save()
    return rec


def start_break(employee) -> AttendanceBreak:
    rec = Attendance.objects.filter(employee=employee, attendance_date=timezone.localdate()).first()
    if not rec or not rec.check_in or rec.check_out:
        raise ServiceError("You are not currently checked in.", 409)
    if rec.breaks.filter(end__isnull=True).exists():
        raise ServiceError("A break is already in progress.", 409)
    return AttendanceBreak.objects.create(attendance=rec, start=timezone.now())


def end_break(employee) -> AttendanceBreak:
    rec = Attendance.objects.filter(employee=employee, attendance_date=timezone.localdate()).first()
    b = rec.breaks.filter(end__isnull=True).first() if rec else None
    if not b:
        raise ServiceError("No break in progress.", 409)
    b.end = timezone.now()
    b.save(update_fields=["end"])
    return b


def timeline(rec: Attendance) -> list[dict]:
    if not rec or not rec.check_in:
        return []
    ev = [{"time": timezone.localtime(rec.check_in).strftime("%I:%M %p"), "label": "CHECK IN", "ts": rec.check_in}]
    for b in rec.breaks.all():
        ev.append({"time": timezone.localtime(b.start).strftime("%I:%M %p"), "label": "BREAK", "ts": b.start})
        if b.end:
            ev.append({"time": timezone.localtime(b.end).strftime("%I:%M %p"), "label": "BACK TO WORK", "ts": b.end})
    if rec.check_out:
        ev.append({"time": timezone.localtime(rec.check_out).strftime("%I:%M %p"), "label": "CHECK OUT", "ts": rec.check_out})
    ev.sort(key=lambda e: e["ts"])
    for e in ev:
        e.pop("ts")
    return ev


def summarise(qs) -> dict:
    from django.db.models import Count, Sum
    agg = qs.aggregate(hours=Sum("total_hours"), overtime=Sum("overtime_hours"))
    counts = dict(qs.values_list("status").annotate(c=Count("id")).order_by())
    return {"counts": counts, "total_hours": float(agg["hours"] or 0), "overtime_hours": float(agg["overtime"] or 0)}
