from datetime import timedelta

from django.utils import timezone
from django_filters import rest_framework as df
from rest_framework import serializers, viewsets
from rest_framework.decorators import action

from apps.common.exceptions import ServiceError
from apps.common.responses import ok
from apps.employees.services import visible_employee_ids

from . import services
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    department = serializers.CharField(source="employee.department.name", read_only=True, default=None)
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["id", "employee", "employee_name", "employee_code", "department", "attendance_date", "check_in",
                  "check_out", "total_hours", "overtime_hours", "status", "remarks", "timeline"]

    def get_timeline(self, obj):
        return services.timeline(obj) if self.context.get("with_timeline") else []


class AttendanceFilter(df.FilterSet):
    date = df.DateFilter(field_name="attendance_date")
    date_from = df.DateFilter(field_name="attendance_date", lookup_expr="gte")
    date_to = df.DateFilter(field_name="attendance_date", lookup_expr="lte")
    department = df.NumberFilter(field_name="employee__department")

    class Meta:
        model = Attendance
        fields = ["status", "employee"]


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceSerializer
    filterset_class = AttendanceFilter
    search_fields = ["employee__first_name", "employee__last_name", "employee__employee_id"]
    ordering_fields = ["attendance_date", "total_hours"]

    def get_queryset(self):
        qs = Attendance.objects.select_related("employee", "employee__department")
        ids = visible_employee_ids(self.request.user)
        return qs if ids is None else qs.filter(employee_id__in=ids)

    def _me(self, request):
        emp = getattr(request.user, "employee", None)
        if not emp:
            raise ServiceError("No employee profile.", 404)
        return emp

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        rec = services.check_in(self._me(request), bool(request.data.get("work_from_home")))
        return ok(AttendanceSerializer(rec, context={"with_timeline": True}).data, "Checked in", 201)

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request):
        rec = services.check_out(self._me(request))
        return ok(AttendanceSerializer(rec, context={"with_timeline": True}).data, "Checked out")

    @action(detail=False, methods=["post"], url_path="break-start")
    def break_start(self, request):
        services.start_break(self._me(request))
        return ok({}, "Break started")

    @action(detail=False, methods=["post"], url_path="break-end")
    def break_end(self, request):
        services.end_break(self._me(request))
        return ok({}, "Back to work")

    @action(detail=False, methods=["get"])
    def today(self, request):
        rec = Attendance.objects.filter(employee=self._me(request), attendance_date=timezone.localdate()).first()
        return ok(AttendanceSerializer(rec, context={"with_timeline": True}).data if rec else None)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """?view=daily|weekly|monthly (relative to ?date=)"""
        qs = self.filter_queryset(self.get_queryset())
        view = request.query_params.get("view", "monthly")
        ref = timezone.localdate()
        start = {"daily": ref, "weekly": ref - timedelta(days=ref.weekday())}.get(view, ref.replace(day=1))
        if view == "weekly":
            qs = qs.filter(attendance_date__range=(start, start + timedelta(days=6)))
        elif view == "daily":
            qs = qs.filter(attendance_date=ref)
        else:
            qs = qs.filter(attendance_date__year=ref.year, attendance_date__month=ref.month)
        return ok({"view": view, "from": start, **services.summarise(qs)})
