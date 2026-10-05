from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.common.responses import ok
from apps.employees.models import Employee
from apps.employees.services import visible_employee_ids

from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    progress = serializers.IntegerField(min_value=0, max_value=100, required=False)

    class Meta:
        model = Goal
        fields = ["id", "owner", "owner_name", "manager", "title", "description", "start_date", "due_date", "progress", "priority", "status"]
        read_only_fields = ["status", "manager"]
        extra_kwargs = {"owner": {"required": False}}

    def validate(self, d):
        if d.get("due_date") and d.get("start_date") and d["due_date"] < d["start_date"]:
            raise serializers.ValidationError({"due_date": "Due date cannot be before start date."})
        return d


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    filterset_fields = ["status", "priority", "owner"]
    search_fields = ["title", "owner__first_name", "owner__last_name"]
    ordering_fields = ["due_date", "progress"]

    def get_queryset(self):
        qs = Goal.objects.select_related("owner")
        ids = visible_employee_ids(self.request.user)
        return qs if ids is None else qs.filter(owner_id__in=ids)

    def _owner(self, request, data):
        me = request.user.employee
        oid = data.get("owner")
        if not oid or int(getattr(oid, "pk", oid)) == me.pk:
            return me
        owner = Employee.objects.get(pk=getattr(oid, "pk", oid))
        if request.user.role in R.HR_ROLES or (request.user.role == R.MANAGER and owner.manager_id == me.pk):
            return owner
        raise PermissionDenied("You can only create goals for yourself or your team.")

    def create(self, request, *a, **kw):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        owner = self._owner(request, s.validated_data)
        s.validated_data.pop("owner", None)
        g = Goal(owner=owner, manager=owner.manager, **s.validated_data)
        g.save()
        return ok(self.get_serializer(g).data, "Goal created", 201)

    def _can_edit(self, request, g):
        me = request.user.employee
        return g.owner_id == me.pk or request.user.role in R.HR_ROLES or (request.user.role == R.MANAGER and g.owner.manager_id == me.pk)

    def partial_update(self, request, *a, **kw):
        g = self.get_object()
        if not self._can_edit(request, g):
            raise PermissionDenied()
        s = self.get_serializer(g, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        for k, v in s.validated_data.items():
            if k != "owner":
                setattr(g, k, v)
        g.save()
        return ok(self.get_serializer(g).data, "Goal updated")

    update = partial_update

    def destroy(self, request, *a, **kw):
        g = self.get_object()
        if not self._can_edit(request, g):
            raise PermissionDenied()
        g.delete()
        return ok({}, "Goal deleted")
