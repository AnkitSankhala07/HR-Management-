"""Employee creation shared by public registration, HR create and the hiring flow."""
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError

from .models import Employee

User = get_user_model()


def next_employee_id() -> str:
    year = date.today().year
    prefix = f"DF{year}"
    last = Employee.objects.filter(employee_id__startswith=prefix).order_by("-employee_id").first()
    seq = int(last.employee_id[len(prefix):]) + 1 if last and last.employee_id[len(prefix):].isdigit() else 1
    return f"{prefix}{seq:04d}"


@transaction.atomic
def create_employee(*, request=None, employee_id, email, first_name, last_name, password, role=R.EMPLOYEE,
                    email_verified=True, joining_date=None, actor=None, **profile) -> Employee:
    email = email.strip().lower()
    if User.objects.filter(email__iexact=email).exists():
        raise ServiceError("Email already registered.", 409, {"email": "Email already registered."})
    if User.objects.filter(employee_id__iexact=employee_id).exists():
        raise ServiceError("Employee ID already exists.", 409, {"employee_id": "Employee ID already exists."})
    user = User.objects.create_user(email=email, password=password, employee_id=employee_id, role=role,
                                    email_verified=email_verified)
    emp = Employee.objects.create(user=user, employee_id=employee_id, first_name=first_name, last_name=last_name,
                                  joining_date=joining_date or date.today(), **profile)
    from apps.leave.services import ensure_balances
    ensure_balances(emp)
    audit.log(request, "EMPLOYEE_CREATED", "Employee", emp.pk, new={"employee_id": employee_id, "email": email, "role": role},
              user=actor or (request.user if request is not None and request.user.is_authenticated else None))
    return emp


def team_ids(user):
    """Employee ids visible to a manager: themself + direct reports."""
    emp = getattr(user, "employee", None)
    if not emp:
        return []
    return [emp.pk, *Employee.objects.filter(manager=emp).values_list("pk", flat=True)]


def visible_employee_ids(user):
    """None means 'all employees'. Otherwise a list of Employee pks the user may see."""
    if user.role in R.HR_ROLES:
        return None
    if user.role == R.MANAGER:
        return team_ids(user)
    emp = getattr(user, "employee", None)
    return [emp.pk] if emp else []
