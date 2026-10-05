from django_filters import rest_framework as df
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.common.responses import ok
from apps.employees.services import visible_employee_ids

from . import services
from .models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "name", "code", "annual_allocation", "is_paid"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    reviewer = serializers.CharField(source="reviewed_by.email", read_only=True, default=None)
    can_review = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = ["id", "employee", "employee_name", "leave_type", "leave_type_name", "start_date", "end_date",
                  "total_days", "reason", "status", "admin_comment", "reviewer", "reviewed_at", "created_at", "can_review"]
        read_only_fields = ["employee", "total_days", "status", "admin_comment", "reviewed_at"]

    def get_can_review(self, obj):
        u = self.context["request"].user
        return obj.status == "PENDING" and services.can_review(u, obj)


class BalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    remaining = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "employee", "leave_type", "leave_type_name", "year", "allocated", "used", "remaining"]


class LeaveFilter(df.FilterSet):
    department = df.NumberFilter(field_name="employee__department")
    date_from = df.DateFilter(field_name="start_date", lookup_expr="gte")
    date_to = df.DateFilter(field_name="end_date", lookup_expr="lte")

    class Meta:
        model = LeaveRequest
        fields = ["status", "leave_type", "employee"]


class LeaveRequestViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = LeaveRequestSerializer
    filterset_class = LeaveFilter
    search_fields = ["employee__first_name", "employee__last_name", "reason"]
    ordering_fields = ["created_at", "start_date"]

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("employee", "employee__user", "leave_type", "reviewed_by")
        ids = visible_employee_ids(self.request.user)
        return qs if ids is None else qs.filter(employee_id__in=ids)

    def create(self, request, *a, **kw):
        emp = getattr(request.user, "employee", None)
        if not emp:
            raise ServiceError("No employee profile.", 404)
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        lr = services.apply_leave(request, emp, **s.validated_data)
        return ok(self.get_serializer(lr).data, "Leave request created successfully", 201)

    @action(detail=True, methods=["patch", "post"])
    def approve(self, request, pk=None):
        lr = services.review_leave(request, int(pk), True, request.data.get("comment", ""))
        return ok(self.get_serializer(lr).data, "Leave approved")

    @action(detail=True, methods=["patch", "post"])
    def reject(self, request, pk=None):
        lr = services.review_leave(request, int(pk), False, request.data.get("comment", ""))
        return ok(self.get_serializer(lr).data, "Leave rejected")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return ok(self.get_serializer(services.cancel_leave(request, int(pk))).data, "Leave cancelled")


class LeaveBalanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = BalanceSerializer
    filterset_fields = ["employee", "year"]
    pagination_class = None

    def get_queryset(self):
        qs = LeaveBalance.objects.select_related("leave_type")
        ids = visible_employee_ids(self.request.user)
        return qs if ids is None else qs.filter(employee_id__in=ids)

    def list(self, request, *a, **kw):
        emp = getattr(request.user, "employee", None)
        if emp and not request.query_params.get("employee"):
            services.ensure_balances(emp)
            qs = self.get_queryset().filter(employee=emp)
        else:
            qs = self.filter_queryset(self.get_queryset())
        return ok(self.get_serializer(qs, many=True).data)


class LeaveTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LeaveTypeSerializer
    pagination_class = None

    def get_queryset(self):
        services.ensure_leave_types()
        return LeaveType.objects.all()
