from . import roles as R
from .navigation import menu_for


def layout(request):
    u = getattr(request, "user", None)
    if not u or not u.is_authenticated:
        return {}
    from apps.notifications.models import Notification
    emp = getattr(u, "employee", None)
    multi_users = getattr(request, "multi_accounts", [u])
    return {
        "menu": menu_for(u.role),
        "unread_count": Notification.objects.filter(user=u, is_read=False).count(),
        "me_id": u.pk,
        "me_name": emp.full_name if emp else u.email,
        "me_initials": emp.initials if emp else u.email[:2].upper(),
        "me_role": u.get_role_display(),
        "me_email": u.email,
        "role": u.role,
        "is_hr": u.role in R.HR_ROLES,
        "is_payroll_admin": u.role in R.PAYROLL_ROLES,
        "is_approver": u.role in R.APPROVER_ROLES,
        "is_recruit": u.role in R.RECRUITMENT_ROLES,
        "is_admin": u.role in R.ADMIN_ROLES,
        "logged_in_accounts": [
            {
                "id": user.pk,
                "name": getattr(user, "employee", None).full_name if getattr(user, "employee", None) else user.email,
                "role": user.get_role_display(),
                "email": user.email,
                "initials": getattr(user, "employee", None).initials if getattr(user, "employee", None) else user.email[:2].upper(),
                "is_active": user.pk == u.pk,
            }
            for user in multi_users
        ],
        "has_multi_accounts": len(multi_users) > 1,
    }
