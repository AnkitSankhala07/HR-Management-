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


def logout_view(request):
    user_id = request.GET.get("user_id")
    from apps.accounts.services import logout_user
    if user_id and str(user_id).isdigit():
        logout_user(request, user_id=int(user_id))
    elif request.GET.get("all"):
        from django.contrib.auth import logout
        logout(request)
    else:
        logout_user(request)
    return redirect("/login/")


def switch_account_view(request, user_id):
    multi = list(request.session.get("_multi_accounts", [])) if hasattr(request, "session") else []
    if user_id in multi:
        from apps.accounts.models import User
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user:
            request.session["_active_account_id"] = user.pk
            request.session["_auth_user_id"] = str(user.pk)
            request.session["_auth_user_hash"] = user.get_session_auth_hash()
            request.session.modified = True
            return redirect(f"/dashboard/?as={user.pk}")
    return redirect("/dashboard/")


def auth_page(template):
    def view(request, **kw):
        if request.user.is_authenticated and template != "auth/reset_password.html":
            if template == "auth/login.html":
                u = request.user
                emp = getattr(u, "employee", None)
                multi_users = getattr(request, "multi_accounts", [u])
                logged_in_accounts = [
                    {
                        "id": user.pk,
                        "name": getattr(user, "employee", None).full_name if getattr(user, "employee", None) else user.email,
                        "role": user.get_role_display(),
                        "email": user.email,
                        "initials": getattr(user, "employee", None).initials if getattr(user, "employee", None) else user.email[:2].upper(),
                        "is_active": user.pk == u.pk,
                    }
                    for user in multi_users
                ]
                return render(request, template, {
                    "token": kw.get("token", ""),
                    "verify": settings.REQUIRE_EMAIL_VERIFICATION,
                    "already_authenticated": True,
                    "logged_in_name": emp.full_name if emp else u.email,
                    "logged_in_role": u.get_role_display(),
                    "logged_in_email": u.email,
                    "logged_in_initials": emp.initials if emp else u.email[:2].upper(),
                    "logged_in_accounts": logged_in_accounts,
                })
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
    return render(request, "public/careers.html", {"jobs": Job.objects.filter(status="OPEN").select_related("department")})


def career_detail(request, pk):
    job = Job.objects.filter(pk=pk, status="OPEN").select_related("department").first()
    if not job:
        raise Http404
    return render(request, "public/job.html", {"job": job})


def offer_page(request, token):
    return render(request, "public/offer.html", {"token": token})
