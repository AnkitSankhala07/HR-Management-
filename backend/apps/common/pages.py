"""Server-rendered pages. Data is loaded from MySQL via selectors or via the REST API (fetch)."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import redirect, render

from apps.employees.models import Employee
from apps.recruitment.models import Job

from . import roles as R, selectors
from .permissions import page_role_required


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)


def landing(request):
    if request.user.is_authenticated:
        return redirect("/dashboard/")
    return render(request, "landing.html")


def auth_page(template):
    def view(request, **kw):
        if request.user.is_authenticated and template != "auth/reset_password.html":
            return redirect("/dashboard/")
        return render(request, template, {"token": kw.get("token", ""), "verify": settings.REQUIRE_EMAIL_VERIFICATION})
    return view


@page_role_required()
def dashboard(request):
    u = request.user
    if u.role in R.HR_ROLES:
        return render(request, "dashboards/hr.html", {"d": selectors.hr_dashboard(u), "title": "Dashboard"})
    if u.role == R.RECRUITER:
        return render(request, "dashboards/recruiter.html", {"d": selectors.recruiter_dashboard(u), "title": "Dashboard"})
    tpl = "dashboards/manager.html" if u.role == R.MANAGER else "dashboards/employee.html"
    ctx = {"d": selectors.employee_dashboard(u), "title": "Dashboard"}
    if u.role == R.MANAGER:
        ctx["m"] = selectors.manager_dashboard(u)
    return render(request, tpl, ctx)


def simple(template, title, roles=()):
    @page_role_required(*roles)
    def view(request, **kw):
        return render(request, template, {"title": title, **kw})
    return view


@page_role_required(*R.HR_ROLES)
def employee_detail(request, pk):
    if not Employee.objects.filter(pk=pk).exists():
        raise Http404
    return render(request, "pages/employee_detail.html", {"title": "Employee", "emp_id": pk})


@page_role_required(*R.APPROVER_ROLES)
def team(request):
    return render(request, "pages/team.html", {"title": "My Team"})


def careers(request):
    jobs = Job.objects.filter(status="OPEN").select_related("department").order_by("-published_at", "-id")
    dept_names = sorted(list({j.department.name for j in jobs if j.department}))
    locations = sorted(list({j.location for j in jobs if j.location}))
    return render(request, "public/careers.html", {
        "jobs": jobs,
        "departments": dept_names,
        "locations": locations,
        "total_jobs": jobs.count(),
        "title": "Careers · Join the Dayflow Team",
    })


def career_detail(request, pk):
    job = Job.objects.filter(pk=pk, status="OPEN").select_related("department").first()
    if not job:
        raise Http404
    skills_list = [s.strip() for s in job.skills_required.split(",") if s.strip()] if job.skills_required else []
    related_jobs = Job.objects.filter(status="OPEN", department=job.department).exclude(pk=job.pk)[:3]
    return render(request, "public/job.html", {
        "job": job,
        "skills_list": skills_list,
        "related_jobs": related_jobs,
        "title": f"{job.title} · Careers",
    })


def offer_page(request, token):
    return render(request, "public/offer.html", {"token": token})
