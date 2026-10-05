from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.common import roles as R
from apps.common.responses import ok

from .models import Onboarding, OnboardingTask


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTask
        fields = ["id", "onboarding", "title", "status", "due_date", "completed_at"]
        read_only_fields = ["onboarding", "title", "due_date", "completed_at"]


class OnboardingSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    progress = serializers.IntegerField(read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Onboarding
        fields = ["id", "employee", "employee_name", "employee_code", "started_at", "progress", "tasks"]


class OnboardingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OnboardingSerializer
    search_fields = ["employee__first_name", "employee__last_name", "employee__employee_id"]

    def get_queryset(self):
        qs = Onboarding.objects.select_related("employee").prefetch_related("tasks")
        return qs if self.request.user.role in R.RECRUITMENT_ROLES else qs.filter(employee__user=self.request.user)


class OnboardingTaskViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = TaskSerializer
    http_method_names = ["patch", "head", "options"]

    def get_queryset(self):
        qs = OnboardingTask.objects.select_related("onboarding__employee")
        return qs if self.request.user.role in R.RECRUITMENT_ROLES else qs.filter(onboarding__employee__user=self.request.user)

    def partial_update(self, request, *a, **kw):
        t = self.get_object()
        s = self.get_serializer(t, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        t.status = s.validated_data.get("status", t.status)
        t.completed_at = timezone.now() if t.status == "COMPLETED" else None
        t.save()
        return ok(self.get_serializer(t).data, "Task updated")
