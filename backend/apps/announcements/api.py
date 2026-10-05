from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.common import roles as R
from apps.common.responses import ok
from apps.notifications.services import notify

from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Announcement
        fields = ["id", "title", "description", "audience", "department", "department_name", "priority", "published_at", "expires_at"]

    def validate(self, d):
        if d.get("audience") == "DEPARTMENT" and not d.get("department"):
            raise serializers.ValidationError({"department": "Required for department announcements."})
        if d.get("expires_at") and d["expires_at"] < d.get("published_at", timezone.now()):
            raise serializers.ValidationError({"expires_at": "Expiry must be after publish date."})
        return d


def active_for(user):
    now = timezone.now()
    qs = Announcement.objects.select_related("department").filter(published_at__lte=now).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))
    if user.role in R.HR_ROLES:
        return qs
    dept = getattr(getattr(user, "employee", None), "department_id", None)
    return qs.filter(Q(audience="COMPANY") | Q(department_id=dept))


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    filterset_fields = ["priority", "audience", "department"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        if self.request.user.role in R.HR_ROLES and self.request.query_params.get("all"):
            return Announcement.objects.select_related("department")
        return active_for(self.request.user)

    def _guard(self):
        if self.request.user.role not in R.HR_ROLES:
            raise PermissionDenied("Only HR can manage announcements.")

    def create(self, request, *a, **kw):
        self._guard()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        a_ = s.save(created_by=request.user)
        from django.contrib.auth import get_user_model
        users = get_user_model().objects.filter(is_active=True)
        if a_.audience == "DEPARTMENT":
            users = users.filter(employee__department=a_.department)
        for u in users.iterator():
            notify(u, f"Announcement: {a_.title}", a_.description[:200], "ANNOUNCEMENT", "/announcements/")
        return ok(s.data, "Announcement published", 201)

    def update(self, request, *a, **kw):
        self._guard()
        return super().update(request, *a, **kw)

    def destroy(self, request, *a, **kw):
        self._guard()
        return super().destroy(request, *a, **kw)
