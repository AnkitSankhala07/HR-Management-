from decimal import Decimal

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django_filters import rest_framework as df
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.common.responses import ok
from apps.notifications.services import notify

from .models import Payroll
from .pdf import salary_slip_pdf

MONEY = dict(max_digits=12, decimal_places=2, min_value=Decimal("0"))


class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    department = serializers.CharField(source="employee.department.name", read_only=True, default=None)
    basic_salary = serializers.DecimalField(**MONEY)
    hra = serializers.DecimalField(required=False, **MONEY)
    allowances = serializers.DecimalField(required=False, **MONEY)
    bonus = serializers.DecimalField(required=False, **MONEY)
    deductions = serializers.DecimalField(required=False, **MONEY)

    class Meta:
        model = Payroll
        fields = ["id", "employee", "employee_name", "employee_code", "department", "pay_month", "pay_year", "basic_salary",
                  "hra", "allowances", "bonus", "deductions", "gross_salary", "net_salary", "payment_status", "updated_at"]
        read_only_fields = ["gross_salary", "net_salary"]   # never trusted from the client
        validators = []   # uniqueness is enforced by the DB constraint and surfaced as HTTP 409

    def validate_pay_month(self, v):
        if not 1 <= v <= 12:
            raise serializers.ValidationError("Month must be 1-12.")
        return v

    def validate(self, d):
        basic, hra = d.get("basic_salary", getattr(self.instance, "basic_salary", 0)), d.get("hra", getattr(self.instance, "hra", 0))
        alw, bon = d.get("allowances", getattr(self.instance, "allowances", 0)), d.get("bonus", getattr(self.instance, "bonus", 0))
        if d.get("deductions", getattr(self.instance, "deductions", 0)) > basic + hra + alw + bon:
            raise serializers.ValidationError({"deductions": "Deductions cannot exceed gross salary."})
        return d


class PayrollFilter(df.FilterSet):
    month = df.NumberFilter(field_name="pay_month")
    year = df.NumberFilter(field_name="pay_year")
    department = df.NumberFilter(field_name="employee__department")

    class Meta:
        model = Payroll
        fields = ["payment_status", "employee"]


class PayrollViewSet(viewsets.ModelViewSet):
    """Employees: read-only on their OWN rows. Payroll admins: full CRUD. Everyone else: own only."""
    serializer_class = PayrollSerializer
    filterset_class = PayrollFilter
    search_fields = ["employee__first_name", "employee__last_name", "employee__employee_id"]
    ordering_fields = ["pay_year", "pay_month", "net_salary"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def _is_admin(self):
        return self.request.user.role in R.PAYROLL_ROLES

    def get_queryset(self):
        qs = Payroll.objects.select_related("employee", "employee__department", "employee__designation")
        if self._is_admin():
            return qs
        return qs.filter(employee__user=self.request.user)

    def _guard_write(self):
        if not self._is_admin():
            raise PermissionDenied("Only payroll administrators can modify payroll.")

    @transaction.atomic
    def create(self, request, *a, **kw):
        self._guard_write()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        p = Payroll(**s.validated_data, updated_by=request.user)
        p.recalculate()
        try:
            with transaction.atomic():
                p.save()
        except IntegrityError:
            raise ServiceError("Payroll already exists for this employee and period.", 409)
        audit.log(request, "PAYROLL_CREATED", "Payroll", p.pk, new={"employee": p.employee_id, "net": str(p.net_salary)})
        audit.log(request, "SALARY_CREATED", "Payroll", p.pk, new={"basic": str(p.basic_salary)})
        notify(p.employee.user, "Payroll updated", f"Your payroll for {p.pay_month}/{p.pay_year} is available.", "PAYROLL", "/payroll/", email=True)
        return ok(self.get_serializer(p).data, "Payroll created", 201)

    @transaction.atomic
    def partial_update(self, request, *a, **kw):
        self._guard_write()
        p = Payroll.objects.select_for_update().get(pk=self.get_object().pk)
        old = PayrollSerializer(p).data
        s = self.get_serializer(p, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        for k, v in s.validated_data.items():
            if k not in ("employee", "pay_month", "pay_year"):   # period/employee are immutable
                setattr(p, k, v)
        p.updated_by = request.user
        p.recalculate()
        p.save()
        audit.log(request, "SALARY_UPDATED", "Payroll", p.pk, old=old, new=PayrollSerializer(p).data)
        notify(p.employee.user, "Payroll updated", f"Your payroll for {p.pay_month}/{p.pay_year} was updated.", "PAYROLL", "/payroll/", email=True)
        return ok(self.get_serializer(p).data, "Payroll updated")

    def destroy(self, request, *a, **kw):
        self._guard_write()
        p = self.get_object()
        audit.log(request, "PAYROLL_DELETED", "Payroll", p.pk)
        p.delete()
        return ok({}, "Payroll deleted")

    @action(detail=True, methods=["get"])
    def slip(self, request, pk=None):
        p = self.get_object()   # get_queryset already blocks other employees' rows (404)
        resp = HttpResponse(salary_slip_pdf(p), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="salary-slip-{p.employee.employee_id}-{p.pay_year}-{p.pay_month:02d}.pdf"'
        return resp

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Own latest payroll for the dashboard."""
        p = Payroll.objects.filter(employee__user=request.user).select_related("employee").first()
        return ok(PayrollSerializer(p).data if p else None)
