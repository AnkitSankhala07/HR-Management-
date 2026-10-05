from collections import defaultdict

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.common import roles as R
from apps.common.responses import ok
from apps.employees.services import visible_employee_ids

from .models import EmployeeSkill, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "category"]


class EmployeeSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    new_skill = serializers.CharField(write_only=True, required=False, max_length=60)
    skill = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.all(), required=False)

    class Meta:
        model = EmployeeSkill
        fields = ["id", "employee", "employee_name", "skill", "skill_name", "new_skill", "level", "level_label", "years_experience", "certification", "last_updated"]
        read_only_fields = ["employee"]


class SkillViewSet(viewsets.ModelViewSet):
    serializer_class = SkillSerializer
    queryset = Skill.objects.all()
    search_fields = ["name"]
    pagination_class = None

    def get_permissions(self):
        return [IsAuthenticated()]

    def create(self, request, *a, **kw):
        return super().create(request, *a, **kw)

    def update(self, request, *a, **kw):
        if request.user.role not in R.HR_ROLES:
            raise PermissionDenied()
        return super().update(request, *a, **kw)

    def destroy(self, request, *a, **kw):
        if request.user.role not in R.HR_ROLES:
            raise PermissionDenied()
        return super().destroy(request, *a, **kw)


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    """Skill matrix data. Informational only - never an automated basis for employment decisions."""
    serializer_class = EmployeeSkillSerializer
    filterset_fields = ["employee", "skill", "level"]
    search_fields = ["skill__name", "employee__first_name", "employee__last_name"]

    def get_queryset(self):
        qs = EmployeeSkill.objects.select_related("skill", "employee", "employee__department")
        ids = visible_employee_ids(self.request.user)
        return qs if ids is None else qs.filter(employee_id__in=ids)

    def create(self, request, *a, **kw):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        name = d.pop("new_skill", None)
        if name:
            d["skill"], _ = Skill.objects.get_or_create(name=name.strip().title())
        if "skill" not in d:
            raise serializers.ValidationError({"skill": "Choose a skill or enter a new one."})
        emp = request.user.employee
        obj, created = EmployeeSkill.objects.update_or_create(employee=emp, skill=d.pop("skill"), defaults=d)
        return ok(self.get_serializer(obj).data, "Skill saved", 201 if created else 200)

    def _own(self, request):
        obj = self.get_object()
        if obj.employee.user_id != request.user.pk:
            raise PermissionDenied("You can only edit your own skills.")
        return obj

    def partial_update(self, request, *a, **kw):
        obj = self._own(request)
        s = self.get_serializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        for k, v in s.validated_data.items():
            if k not in ("skill", "new_skill"):
                setattr(obj, k, v)
        obj.save()
        return ok(self.get_serializer(obj).data, "Skill updated")

    update = partial_update

    def destroy(self, request, *a, **kw):
        self._own(request).delete()
        return ok({}, "Skill removed")

    @action(detail=False, methods=["get"])
    def matrix(self, request):
        """Department x skill matrix + distribution + gap (people who hold each skill vs team size)."""
        if request.user.role not in R.HR_ROLES + (R.MANAGER,):
            raise PermissionDenied()
        qs = self.filter_queryset(self.get_queryset())
        matrix, dist = defaultdict(lambda: defaultdict(list)), defaultdict(int)
        for es in qs:
            dept = es.employee.department.name if es.employee.department else "Unassigned"
            matrix[dept][es.skill.name].append(es.level)
            dist[es.get_level_display()] += 1
        out = {d: {s: {"people": len(l), "avg_level": round(sum(l) / len(l), 2)} for s, l in skills.items()} for d, skills in matrix.items()}
        return ok({"matrix": out, "distribution": dict(dist)})
