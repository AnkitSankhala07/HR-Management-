from django_filters import rest_framework as df
from rest_framework import mixins, serializers, viewsets

from apps.common.permissions import role_permission
from apps.common import roles as R

from .models import AuditLog


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "user_email", "action", "entity", "entity_id", "timestamp", "ip_address", "user_agent", "old_value", "new_value"]


class AuditFilter(df.FilterSet):
    date_from = df.DateFilter(field_name="timestamp", lookup_expr="date__gte")
    date_to = df.DateFilter(field_name="timestamp", lookup_expr="date__lte")
    user = df.CharFilter(field_name="user_email", lookup_expr="icontains")

    class Meta:
        model = AuditLog
        fields = ["action", "entity"]


class AuditViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditSerializer
    queryset = AuditLog.objects.all()
    permission_classes = [role_permission(*R.ADMIN_ROLES)]
    filterset_class = AuditFilter
    search_fields = ["user_email", "entity", "action"]
