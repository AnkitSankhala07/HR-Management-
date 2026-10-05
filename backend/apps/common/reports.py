"""Reports with filters, JSON view, CSV and PDF export (authorised roles only)."""
import csv
from io import BytesIO, StringIO

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from apps.attendance.models import Attendance
from apps.common.exceptions import ServiceError
from apps.common.responses import ok
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest
from apps.payroll.models import Payroll
from apps.recruitment.models import Application
from apps.skills.models import EmployeeSkill
from apps.employees.services import visible_employee_ids

from . import roles as R


def _rows(kind, request):
    q, u = request.query_params, request.user
    ids = visible_employee_ids(u)
    scope = (lambda qs, f="employee_id__in": qs if ids is None else qs.filter(**{f: ids}))
    if kind == "attendance":
        qs = scope(Attendance.objects.select_related("employee", "employee__department"))
        if q.get("date_from"): qs = qs.filter(attendance_date__gte=q["date_from"])
        if q.get("date_to"): qs = qs.filter(attendance_date__lte=q["date_to"])
        if q.get("department"): qs = qs.filter(employee__department=q["department"])
        if q.get("status"): qs = qs.filter(status=q["status"])
        return ["Employee ID", "Name", "Department", "Date", "Check in", "Check out", "Hours", "Overtime", "Status"], [
            [a.employee.employee_id, a.employee.full_name, a.employee.department or "", a.attendance_date, a.check_in or "", a.check_out or "",
             a.total_hours, a.overtime_hours, a.get_status_display()] for a in qs[:5000]]
    if kind == "leave":
        qs = scope(LeaveRequest.objects.select_related("employee", "leave_type", "employee__department"))
        if q.get("status"): qs = qs.filter(status=q["status"])
        if q.get("department"): qs = qs.filter(employee__department=q["department"])
        return ["Employee ID", "Name", "Type", "From", "To", "Days", "Status", "Comment"], [
            [l.employee.employee_id, l.employee.full_name, l.leave_type.name, l.start_date, l.end_date, l.total_days, l.status, l.admin_comment] for l in qs[:5000]]
    if kind == "payroll":
        if u.role not in R.PAYROLL_ROLES:
            raise PermissionDenied("Payroll reports are restricted to payroll administrators.")
        qs = Payroll.objects.select_related("employee", "employee__department")
        for k, f in (("month", "pay_month"), ("year", "pay_year"), ("payment_status", "payment_status"), ("department", "employee__department")):
            if q.get(k): qs = qs.filter(**{f: q[k]})
        return ["Employee ID", "Name", "Department", "Month", "Year", "Gross", "Deductions", "Net", "Status"], [
            [p.employee.employee_id, p.employee.full_name, p.employee.department or "", p.pay_month, p.pay_year, p.gross_salary, p.deductions, p.net_salary, p.payment_status] for p in qs[:5000]]
    if kind in ("employee", "department"):
        if u.role not in R.HR_ROLES:
            raise PermissionDenied()
        qs = Employee.objects.select_related("user", "department", "designation", "manager")
        if q.get("department"): qs = qs.filter(department=q["department"])
        return ["Employee ID", "Name", "Email", "Department", "Designation", "Manager", "Joined", "Active"], [
            [e.employee_id, e.full_name, e.user.email, e.department or "", e.designation or "", e.manager or "", e.joining_date, e.user.is_active] for e in qs]
    if kind == "recruitment":
        if u.role not in R.RECRUITMENT_ROLES:
            raise PermissionDenied()
        qs = Application.objects.select_related("candidate", "job")
        if q.get("job"): qs = qs.filter(job=q["job"])
        if q.get("stage"): qs = qs.filter(stage=q["stage"])
        return ["Candidate", "Email", "Job", "Stage", "Experience", "Applied"], [
            [a.candidate.name, a.candidate.email, a.job.title, a.stage, a.candidate.experience_years, a.applied_at.date()] for a in qs[:5000]]
    if kind == "skill":
        if u.role not in R.HR_ROLES + (R.MANAGER,):
            raise PermissionDenied()
        qs = scope(EmployeeSkill.objects.select_related("employee", "skill", "employee__department"), "employee_id__in")
        return ["Employee", "Department", "Skill", "Level", "Years", "Certification"], [
            [s.employee.full_name, s.employee.department or "", s.skill.name, s.get_level_display(), s.years_experience, s.certification] for s in qs]
    raise ServiceError("Unknown report.", 404)


from drf_spectacular.types import OpenApiTypes as _T
from drf_spectacular.utils import extend_schema as _es


@_es(request=_T.OBJECT, responses=_T.OBJECT)
class ReportView(APIView):
    """GET /api/reports/<kind>/?format=json|csv|pdf&<filters>"""

    def get(self, request, kind):
        if request.user.role == R.EMPLOYEE and kind not in ("attendance", "leave"):
            raise PermissionDenied()
        header, rows = _rows(kind, request)
        fmt = request.query_params.get("export", "json")
        rows = [[str(c) for c in r] for r in rows]
        if fmt == "csv":
            buf = StringIO()
            w = csv.writer(buf)
            w.writerow(header)
            for r in rows:
                w.writerow([("'" + c if c[:1] in "=+-@" and c else c) for c in r])   # CSV-injection guard
            resp = HttpResponse(buf.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{kind}-report.csv"'
            return resp
        if fmt == "pdf":
            out = BytesIO()
            doc = SimpleDocTemplate(out, pagesize=landscape(A4), title=f"{kind} report")
            t = Table([header] + rows[:400], repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5A724A")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#EBEBEB"))]))
            doc.build([Paragraph(f"Dayflow HRMS - {kind.title()} Report", getSampleStyleSheet()["Title"]), Spacer(1, 6), t])
            resp = HttpResponse(out.getvalue(), content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="{kind}-report.pdf"'
            return resp
        return ok({"columns": header, "rows": rows[:500], "total": len(rows)})
