from datetime import date

from django.http import FileResponse
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.files import safe_name, validate_upload
from apps.common.responses import ok
from apps.employees.models import Employee
from apps.notifications.services import notify

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    file = serializers.FileField(write_only=True)
    effective_status = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "employee", "employee_name", "category", "title", "file", "original_name", "mime_type", "size",
                  "status", "effective_status", "expiry_date", "created_at", "download_url"]
        read_only_fields = ["original_name", "mime_type", "size", "status", "employee"]

    def get_effective_status(self, o):
        return "EXPIRED" if o.expiry_date and o.expiry_date < date.today() else o.status

    def get_download_url(self, o):
        return f"/api/documents/{o.pk}/download/"


class DocumentViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["category", "status", "employee"]
    search_fields = ["title", "employee__first_name", "employee__last_name"]

    def get_queryset(self):
        qs = Document.objects.select_related("employee")
        return qs if self.request.user.role in R.HR_ROLES else qs.filter(employee__user=self.request.user)

    def create(self, request, *a, **kw):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        f = s.validated_data["file"]
        orig = safe_name(f.name)
        mime = validate_upload(f)
        target = getattr(request.user, "employee", None)
        if request.user.role in R.HR_ROLES and request.data.get("employee"):
            target = Employee.objects.get(pk=request.data["employee"])
        d = Document.objects.create(employee=target, uploaded_by=request.user, original_name=orig, mime_type=mime, size=f.size,
                                    category=s.validated_data["category"], title=s.validated_data["title"],
                                    file=f, expiry_date=s.validated_data.get("expiry_date"))
        audit.log(request, "DOCUMENT_UPLOADED", "Document", d.pk, new={"category": d.category, "employee": target.pk})
        return ok(self.get_serializer(d).data, "Document uploaded", 201)

    def destroy(self, request, *a, **kw):
        d = self.get_object()
        if request.user.role not in R.HR_ROLES and (d.employee.user_id != request.user.pk or d.status == "VERIFIED"):
            raise PermissionDenied("You cannot delete this document.")
        audit.log(request, "DOCUMENT_DELETED", "Document", d.pk, old={"title": d.title})
        try:
            d.file.close()
            d.file.delete(save=False)
        except OSError:
            pass
        d.delete()
        return ok({}, "Document deleted")

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        d = self.get_object()     # scoped queryset => other employees' files return 404
        resp = FileResponse(d.file.open("rb"), content_type=d.mime_type)
        disp = "inline" if request.query_params.get("preview") else "attachment"
        resp["Content-Disposition"] = f'{disp}; filename="{d.original_name}"'
        resp["X-Content-Type-Options"] = "nosniff"
        return resp

    def _review(self, request, pk, status_):
        if request.user.role not in R.HR_ROLES:
            raise PermissionDenied()
        d = self.get_object()
        d.status, d.verified_by = status_, request.user
        d.save(update_fields=["status", "verified_by", "updated_at"])
        audit.log(request, "DOCUMENT_" + status_, "Document", d.pk)
        notify(d.employee.user, f"Document {status_.lower()}", f"'{d.title}' was {status_.lower()}.", "DOCUMENT", "/documents/")
        return ok(self.get_serializer(d).data, f"Document {status_.lower()}")

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        return self._review(request, pk, "VERIFIED")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._review(request, pk, "REJECTED")
