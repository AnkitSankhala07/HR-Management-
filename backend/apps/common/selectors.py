"""Dashboard / report queries. Every number shown in the UI comes from here (MySQL), never hardcoded."""
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.announcements.api import active_for
from apps.attendance.models import Attendance
from apps.employees.models import Employee
from apps.employees.services import visible_employee_ids
from apps.goals.models import Goal
from apps.leave.models import LeaveBalance, LeaveRequest
from apps.notifications.models import Notification
from apps.payroll.models import Payroll
from apps.recognition.models import Recognition
from apps.recruitment.models import Application, Candidate, Interview, Job, Offer
from apps.skills.models import EmployeeSkill
from . import roles as R

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _last_months(n=6):
    d, out = date.today().replace(day=1), []
    for _ in range(n):
        out.append((d.year, d.month))
        d = (d - timedelta(days=1)).replace(day=1)
    return out[::-1]


def employee_dashboard(user):
    emp = user.employee
    today = timezone.localdate()
    att = Attendance.objects.filter(employee=emp, attendance_date=today).first()
    from apps.attendance.services import timeline
    month_qs = Attendance.objects.filter(employee=emp, attendance_date__year=today.year, attendance_date__month=today.month)
    return {
        "attendance": att, "timeline": timeline(att) if att else [],
        "month_present": month_qs.filter(status__in=["PRESENT", "WFH", "HALF_DAY"]).count(),
        "balances": LeaveBalance.objects.filter(employee=emp, year=today.year).select_related("leave_type"),
        "leaves": LeaveRequest.objects.filter(employee=emp).select_related("leave_type")[:5],
        "payroll": Payroll.objects.filter(employee=emp).first(),
        "goals": Goal.objects.filter(owner=emp).exclude(status="COMPLETED")[:4],
        "recognitions": Recognition.objects.filter(receiver=emp).select_related("giver")[:3],
        "announcements": active_for(user)[:3],
        "notifications": Notification.objects.filter(user=user)[:5],
        "events": upcoming_events(),
    }


def upcoming_events(days=30):
    today, end = date.today(), date.today() + timedelta(days=days)
    out = []
    for e in Employee.objects.filter(user__is_active=True).select_related("department"):
        for label, d in (("Birthday", e.date_of_birth), ("Work anniversary", e.joining_date)):
            if not d:
                continue
            try:
                nxt = d.replace(year=today.year)
            except ValueError:
                nxt = d.replace(year=today.year, day=28)
            if nxt < today:
                nxt = nxt.replace(year=today.year + 1)
            if nxt <= end and not (label == "Work anniversary" and nxt.year == e.joining_date.year):
                out.append({"name": e.full_name, "type": label, "date": nxt, "years": nxt.year - d.year})
    return sorted(out, key=lambda x: x["date"])[:8]


def hr_dashboard(user):
    today = timezone.localdate()
    emps = Employee.objects.filter(user__is_active=True)
    total = emps.count()
    present = Attendance.objects.filter(attendance_date=today, status__in=["PRESENT", "WFH", "HALF_DAY"]).count()
    on_leave = Attendance.objects.filter(attendance_date=today, status="LEAVE").count()
    pending = LeaveRequest.objects.filter(status="PENDING")
    months = _last_months(6)
    growth = []
    for y, m in months:
        end = date(y + (m == 12), (m % 12) + 1, 1)
        growth.append(Employee.objects.filter(joining_date__lt=end, user__is_active=True).count())
    att_counts = Counter(dict(Attendance.objects.filter(attendance_date__year=today.year, attendance_date__month=today.month)
                              .values_list("status").annotate(c=Count("id")).order_by()))
    leave_counts = dict(LeaveRequest.objects.filter(status="APPROVED").values_list("leave_type__name").annotate(c=Count("id")).order_by())
    pay = []
    for y, m in months:
        pay.append(float(Payroll.objects.filter(pay_year=y, pay_month=m).aggregate(s=Sum("net_salary"))["s"] or 0))
    return {
        "cards": [("Total Employees", total, "users", f"+{emps.filter(joining_date__gte=today.replace(day=1)).count()} this month"),
                  ("Present Today", present, "user-check", f"{round(100 * present / total) if total else 0}% of workforce"),
                  ("On Leave", on_leave, "plane", "today"), ("Pending Approvals", pending.count(), "hourglass", "leave requests")],
        "pending": pending.select_related("employee", "leave_type")[:6],
        "recent_hires": emps.order_by("-joining_date")[:5],
        "events": upcoming_events(),
        "activities": __import__("apps.audit.models", fromlist=["AuditLog"]).AuditLog.objects.all()[:8],
        "announcements": active_for(user)[:3],
        "charts": {
            "growth": {"labels": [f"{MONTHS[m - 1]} {str(y)[2:]}" for y, m in months], "data": growth},
            "attendance": {"labels": [Attendance.Status(k).label for k in att_counts], "data": list(att_counts.values())},
            "leave": {"labels": list(leave_counts), "data": list(leave_counts.values())},
            "payroll": {"labels": [f"{MONTHS[m - 1]} {str(y)[2:]}" for y, m in months], "data": pay},
        },
    }


def manager_dashboard(user):
    me = user.employee
    team = Employee.objects.filter(manager=me, user__is_active=True)
    ids = list(team.values_list("pk", flat=True))
    today = timezone.localdate()
    goals = Goal.objects.filter(owner_id__in=ids)
    return {
        "team": team, "team_size": len(ids),
        "present": Attendance.objects.filter(employee_id__in=ids, attendance_date=today, status__in=["PRESENT", "WFH", "HALF_DAY"]).count(),
        "on_leave": Attendance.objects.filter(employee_id__in=ids, attendance_date=today, status="LEAVE").select_related("employee"),
        "pending": LeaveRequest.objects.filter(employee_id__in=ids, status="PENDING").select_related("employee", "leave_type"),
        "goals_avg": round(goals.aggregate(a=Avg("progress"))["a"] or 0),
        "goals": goals.select_related("owner").exclude(status="COMPLETED")[:6],
        "skills": EmployeeSkill.objects.filter(employee_id__in=ids).values("skill__name").annotate(n=Count("id")).order_by("-n")[:6],
        "recognitions": Recognition.objects.filter(receiver_id__in=ids).select_related("giver", "receiver")[:4],
    }


def recruiter_dashboard(user):
    apps = Application.objects.all()
    stages = dict(apps.values_list("stage").annotate(c=Count("id")).order_by())
    order = ["APPLIED", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED"]
    per_job = list(Job.objects.annotate(n=Count("applications")).values_list("title", "n").order_by("-n")[:6])
    sources = dict(Candidate.objects.values_list("source").annotate(c=Count("id")).order_by())
    return {
        "cards": [("Open Jobs", Job.objects.filter(status="OPEN").count(), "briefcase"), ("Applications", apps.count(), "inbox"),
                  ("Candidates", Candidate.objects.count(), "users"),
                  ("Interviews", Interview.objects.filter(status="SCHEDULED", scheduled_at__gte=timezone.now()).count(), "message-square"),
                  ("Offers", Offer.objects.filter(status__in=["SENT", "DRAFT"]).count(), "file-signature"), ("Hires", stages.get("HIRED", 0), "party-popper")],
        "charts": {"funnel": {"labels": [s.title() for s in order], "data": [stages.get(s, 0) for s in order]},
                   "per_job": {"labels": [j for j, _ in per_job], "data": [n for _, n in per_job]},
                   "sources": {"labels": list(sources), "data": list(sources.values())}},
        "upcoming": Interview.objects.filter(scheduled_at__gte=timezone.now(), status="SCHEDULED").select_related("application__candidate", "application__job")[:5],
    }
