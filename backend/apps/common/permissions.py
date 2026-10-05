"""Server-side RBAC. Frontend hiding is cosmetic; these classes are the real gate."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import render
from rest_framework.permissions import BasePermission

from . import roles as R


def has_role(user, *roles) -> bool:
    return bool(user and user.is_authenticated and user.role in roles)


def role_permission(*roles) -> type[BasePermission]:
    """Factory: DRF permission class allowing only the given roles."""
    class _P(BasePermission):
        message = "You do not have permission to perform this action."

        def has_permission(self, request, view):
            return has_role(request.user, *roles)
    _P.__name__ = "Role_" + "_".join(roles)
    return _P


IsHR = role_permission(*R.HR_ROLES)
IsPayrollAdmin = role_permission(*R.PAYROLL_ROLES)
IsApprover = role_permission(*R.APPROVER_ROLES)
IsRecruitmentStaff = role_permission(*R.RECRUITMENT_ROLES)


def page_role_required(*roles):
    """Template-view decorator: login required + role check (renders friendly 403)."""
    def deco(view):
        @wraps(view)
        def wrapper(request, *a, **kw):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if roles and request.user.role not in roles:
                return render(request, "errors/403.html", status=403)
            return view(request, *a, **kw)
        return wrapper
    return deco
