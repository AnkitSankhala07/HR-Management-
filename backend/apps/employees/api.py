import secrets

from django.db import transaction
from django.db.models import Count
from rest_framework import filters, mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as df

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.common.permissions import IsHR, has_role
from apps.common.responses import ok

from . import services
from .models import Department, Designation, Employee
from .serializers import (DepartmentSerializer, DesignationSerializer, EmployeeSelfSerializer,
                          EmployeeSerializer, EmployeeWriteSerializer)


class EmployeeFilter(df.FilterSet):
    status = df.CharFilter(method="by_status")

    class Meta:
        model = Employee
        fields = ["department", "designation", "employment_type", "manager"]

    def by_status(self, qs, name, value):
        return qs.filter(user__is_active=(value.lower() == "active"))


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    filterset_class = EmployeeFilter
    search_fields = ["employee_id", "first_name", "last_name", "user__email", "department__name", "designation__title"]
    ordering_fields = ["first_name", "employee_id", "joining_date", "department__name"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Employee.objects.select_related("user", "department", "designation", "manager")
        ids = services.visible_employee_ids(self.request.user)
        if self.request.user.role == R.RECRUITER:
            return qs.none()
        return qs if ids is None else qs.filter(pk__in=ids)

    def get_serializer_class(self):
        if self.action in ("create",) or (self.action == "partial_update" and has_role(self.request.user, *R.HR_ROLES)):
            return EmployeeWriteSerializer
        if self.action == "partial_update":
            return EmployeeSelfSerializer
        return EmployeeSerializer

    def create(self, request, *a, **kw):
        if not has_role(request.user, *R.HR_ROLES):
            raise PermissionDenied()
        s = EmployeeWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        for req in ("email", "first_name", "last_name"):
            if not d.get(req):
                raise ServiceError("Validation failed", 400, {req: "This field is required."})
        role = d.pop("role", R.EMPLOYEE)
        if role in (R.SUPER_ADMIN, R.HR_ADMIN) and request.user.role != R.SUPER_ADMIN:
            raise PermissionDenied("Only a Super Admin can create admin accounts.")
        password = d.pop("password", None) or secrets.token_urlsafe(10) + "aA1!"
        emp = services.create_employee(request=request, employee_id=d.pop("employee_id", None) or services.next_employee_id(),
                                       role=role, password=password, email_verified=True, **d)
        out = {"employee": EmployeeSerializer(emp).data}
        from django.conf import settings
        if settings.DEBUG:
            out["temp_password"] = password   # dev convenience only; never returned when DEBUG=False
        return ok(out, "Employee created", 201)

    def partial_update(self, request, *a, **kw):
        emp = self.get_object()
        is_hr = has_role(request.user, *R.HR_ROLES)
        if not is_hr and emp.user_id != request.user.pk:
            raise PermissionDenied("You can only edit your own profile.")
        if not is_hr:
            forbidden = set(request.data) - set(EmployeeSelfSerializer.Meta.fields)
            if forbidden:
                raise PermissionDenied(f"You cannot modify: {', '.join(sorted(forbidden))}")
        old = EmployeeSerializer(emp).data
        s = self.get_serializer(emp, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        with transaction.atomic():
            new_role = d.pop("role", None)
            email = d.pop("email", None)
            d.pop("password", None)
            if "employee_id" in d and d["employee_id"] != emp.employee_id:
                if Employee.objects.exclude(pk=emp.pk).filter(employee_id=d["employee_id"]).exists():
                    raise ServiceError("Employee ID already exists.", 409)
                emp.user.employee_id = d["employee_id"]
                emp.user.save(update_fields=["employee_id"])
            for k, v in d.items():
                setattr(emp, k, v)
            emp.save()
            if new_role and new_role != emp.user.role:
                if request.user.role != R.SUPER_ADMIN and (new_role in (R.SUPER_ADMIN, R.HR_ADMIN) or emp.user.role in (R.SUPER_ADMIN, R.HR_ADMIN)):
                    raise PermissionDenied("Only a Super Admin can change admin roles.")
                audit.log(request, "ROLE_CHANGED", "User", emp.user_id, old={"role": emp.user.role}, new={"role": new_role})
                emp.user.role = new_role
                emp.user.save(update_fields=["role"])
            if email and email.lower() != emp.user.email:
                if emp.user.__class__.objects.filter(email__iexact=email).exclude(pk=emp.user_id).exists():
                    raise ServiceError("Email already registered.", 409)
                emp.user.email = email.lower()
                emp.user.save(update_fields=["email"])
        emp.refresh_from_db()
        audit.log(request, "EMPLOYEE_UPDATED", "Employee", emp.pk, old=old, new=EmployeeSerializer(emp).data)
        return ok(EmployeeSerializer(emp).data, "Profile updated")

    def destroy(self, request, *a, **kw):
        return self._set_active(request, False)

    def _set_active(self, request, active):
        if not has_role(request.user, *R.HR_ROLES):
            raise PermissionDenied()
        emp = self.get_object()
        if emp.user_id == request.user.pk:
            raise ServiceError("You cannot deactivate your own account.", 400)
        if emp.user.role in (R.SUPER_ADMIN, R.HR_ADMIN) and request.user.role != R.SUPER_ADMIN:
            raise PermissionDenied("Only a Super Admin can deactivate admin accounts.")
        emp.user.is_active = active
        emp.user.save(update_fields=["is_active"])
        audit.log(request, "EMPLOYEE_DEACTIVATED" if not active else "EMPLOYEE_UPDATED", "Employee", emp.pk, new={"is_active": active})
        return ok({}, "Employee " + ("activated" if active else "deactivated"))

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._set_active(request, True)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        return self._set_active(request, False)

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        emp = getattr(request.user, "employee", None)
        if not emp:
            raise ServiceError("No employee profile.", 404)
        if request.method == "PATCH":
            forbidden = set(request.data) - set(EmployeeSelfSerializer.Meta.fields)
            if forbidden:
                raise PermissionDenied(f"You cannot modify: {', '.join(sorted(forbidden))}")
            old = EmployeeSerializer(emp).data
            s = EmployeeSelfSerializer(emp, data=request.data, partial=True)
            s.is_valid(raise_exception=True)
            s.save()
            audit.log(request, "EMPLOYEE_UPDATED", "Employee", emp.pk, old=old, new=EmployeeSerializer(emp).data)
            return ok(EmployeeSerializer(emp).data, "Profile updated")
        return ok(EmployeeSerializer(emp).data)

    @action(detail=False, methods=["get"])
    def team(self, request):
        if not has_role(request.user, R.MANAGER, *R.HR_ROLES):
            raise PermissionDenied()
        emp = request.user.employee
        qs = self.filter_queryset(self.get_queryset().filter(manager=emp) if request.user.role == R.MANAGER else self.get_queryset())
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(EmployeeSerializer(page, many=True).data)


class _ReadAllWriteHR(viewsets.ModelViewSet):
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method in ("GET", "HEAD", "OPTIONS") else [IsHR()]


class DepartmentViewSet(_ReadAllWriteHR):
    serializer_class = DepartmentSerializer
    search_fields = ["name"]
    pagination_class = None

    def get_queryset(self):
        return Department.objects.annotate(employee_count=Count("employees"))


class DesignationViewSet(_ReadAllWriteHR):
    serializer_class = DesignationSerializer
    queryset = Designation.objects.select_related("department")
    filterset_fields = ["department"]
    search_fields = ["title"]
    pagination_class = None



class DirectorySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Employee
        fields = ["id", "employee_id", "full_name", "department_name"]


class DirectoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Minimal company directory (name/department only) - safe for every signed-in user."""
    serializer_class = DirectorySerializer
    search_fields = ["first_name", "last_name", "employee_id"]
    queryset = Employee.objects.filter(user__is_active=True).select_related("department")
    pagination_class = None
