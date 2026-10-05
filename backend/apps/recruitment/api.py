from django.http import HttpResponse
from django.utils import timezone
from django_filters import rest_framework as df
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.common.files import validate_upload
from apps.common.permissions import IsRecruitmentStaff
from apps.common.responses import ok
from apps.employees.models import Employee

from . import services
from .models import Application, Candidate, Interview, InterviewFeedback, Job, Offer
from .pdf import offer_letter_pdf


# ---------------- serializers
class JobSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    applications_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Job
        fields = ["id", "title", "department", "department_name", "designation", "hiring_manager", "description", "skills_required",
                  "experience_min", "location", "employment_type", "status", "published_at", "applications_count", "created_at"]
        read_only_fields = ["status", "published_at"]


class CandidateSerializer(serializers.ModelSerializer):
    resume_url = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = ["id", "name", "email", "phone", "skills", "experience_years", "education", "current_company",
                  "expected_salary", "notice_period_days", "source", "resume_url", "created_at"]

    def get_resume_url(self, o):
        return f"/api/candidates/{o.pk}/resume/" if o.resume else None


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.name", read_only=True)
    candidate_email = serializers.CharField(source="candidate.email", read_only=True)
    experience = serializers.DecimalField(source="candidate.experience_years", max_digits=4, decimal_places=1, read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    resume_url = serializers.SerializerMethodField()
    next_interview = serializers.SerializerMethodField()
    offer_status = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ["id", "candidate", "candidate_name", "candidate_email", "experience", "job", "job_title", "stage", "applied_at",
                  "resume_url", "next_interview", "offer_status", "notes"]
        read_only_fields = ["stage"]

    def get_resume_url(self, o):
        return f"/api/candidates/{o.candidate_id}/resume/" if o.candidate.resume else None

    def get_next_interview(self, o):
        iv = next((i for i in o.interviews.all() if i.scheduled_at >= timezone.now() and i.status == "SCHEDULED"), None)
        return iv.scheduled_at if iv else None

    def get_offer_status(self, o):
        return o.offer.status if hasattr(o, "offer") else None


class FeedbackSerializer(serializers.ModelSerializer):
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)

    class Meta:
        model = InterviewFeedback
        fields = ["id", "reviewer_email", "rating", "recommendation", "notes", "created_at"]

    def validate_rating(self, v):
        if not 1 <= v <= 5:
            raise serializers.ValidationError("Rating must be 1-5.")
        return v


class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="application.candidate.name", read_only=True)
    job_title = serializers.CharField(source="application.job.title", read_only=True)
    interviewer_names = serializers.SerializerMethodField()
    feedback = FeedbackSerializer(many=True, read_only=True)
    interviewers = serializers.PrimaryKeyRelatedField(many=True, queryset=Employee.objects.all())

    class Meta:
        model = Interview
        fields = ["id", "application", "candidate_name", "job_title", "interview_type", "scheduled_at", "interviewers",
                  "interviewer_names", "meeting_link", "status", "feedback"]
        read_only_fields = ["status"]

    def get_interviewer_names(self, o):
        return [e.full_name for e in o.interviewers.all()]


class OfferSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="application.candidate.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Offer
        fields = ["id", "application", "candidate_name", "position", "department", "department_name", "salary", "joining_date",
                  "offer_date", "expiry_date", "status"]
        read_only_fields = ["status", "offer_date"]
        extra_kwargs = {"position": {"required": False}, "department": {"required": False}}


# ---------------- viewsets
class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    permission_classes = [IsRecruitmentStaff]
    filterset_fields = ["status", "department"]
    search_fields = ["title", "skills_required"]

    def get_queryset(self):
        from django.db.models import Count
        return Job.objects.select_related("department").annotate(applications_count=Count("applications"))

    def perform_create(self, s):
        j = s.save(created_by=self.request.user)
        audit.log(self.request, "JOB_CREATED", "Job", j.pk, new={"title": j.title})

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        j = self.get_object()
        j.status, j.published_at = "OPEN", j.published_at or timezone.now()
        j.save(update_fields=["status", "published_at", "updated_at"])
        audit.log(request, "JOB_PUBLISHED", "Job", j.pk)
        return ok(JobSerializer(j).data, "Job published")

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        j = self.get_object()
        j.status = "CLOSED"
        j.save(update_fields=["status", "updated_at"])
        audit.log(request, "JOB_CLOSED", "Job", j.pk)
        return ok(JobSerializer(j).data, "Job closed")


class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    permission_classes = [IsRecruitmentStaff]
    queryset = Candidate.objects.all()
    search_fields = ["name", "email", "skills", "applications__job__title", "applications__stage"]
    filterset_fields = ["source"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, s):
        c = s.save()
        resume = self.request.FILES.get("resume")
        if resume:
            validate_upload(resume, allowed=("pdf",))
            c.resume = resume
            c.save()
        audit.log(self.request, "CANDIDATE_CREATED", "Candidate", c.pk)

    @action(detail=True, methods=["get"])
    def resume(self, request, pk=None):
        from django.http import FileResponse
        c = self.get_object()
        if not c.resume:
            raise ServiceError("No resume uploaded.", 404)
        r = FileResponse(c.resume.open("rb"), content_type="application/pdf")
        r["Content-Disposition"] = f'inline; filename="resume-{c.pk}.pdf"'
        return r


class ApplicationFilter(df.FilterSet):
    exp_min = df.NumberFilter(field_name="candidate__experience_years", lookup_expr="gte")
    date_from = df.DateFilter(field_name="applied_at", lookup_expr="date__gte")
    date_to = df.DateFilter(field_name="applied_at", lookup_expr="date__lte")

    class Meta:
        model = Application
        fields = ["job", "stage"]


class ApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsRecruitmentStaff]
    filterset_class = ApplicationFilter
    search_fields = ["candidate__name", "candidate__email", "candidate__skills", "job__title"]
    ordering_fields = ["applied_at"]

    def get_queryset(self):
        return Application.objects.select_related("candidate", "job", "offer").prefetch_related("interviews")

    @action(detail=True, methods=["patch", "post"])
    def stage(self, request, pk=None):
        app = services.move_stage(request, int(pk), request.data.get("stage", ""), request.data.get("notes", ""))
        return ok(self.get_serializer(app).data, "Stage updated")

    @action(detail=False, methods=["get"])
    def pipeline(self, request):
        qs = self.filter_queryset(self.get_queryset())
        cols = {s: [] for s in ("APPLIED", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED", "REJECTED")}
        for a in qs:
            cols[a.stage].append(self.get_serializer(a).data)
        return ok(cols)

    @action(detail=True, methods=["post"])
    def hire(self, request, pk=None):
        from apps.onboarding.services import onboard_candidate
        emp, temp = onboard_candidate(request, self.get_object())
        from django.conf import settings
        out = {"employee_id": emp.employee_id, "employee": emp.pk}
        if settings.DEBUG:
            out["temp_password"] = temp
        return ok(out, "Candidate hired and onboarding created", 201)


class InterviewViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    filterset_fields = ["application", "interview_type", "status"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Interview.objects.select_related("application__candidate", "application__job").prefetch_related("interviewers", "feedback__reviewer")
        if self.request.user.role in R.RECRUITMENT_ROLES:
            return qs
        return qs.filter(interviewers__user=self.request.user)

    def _staff(self):
        if self.request.user.role not in R.RECRUITMENT_ROLES:
            raise PermissionDenied()

    def create(self, request, *a, **kw):
        self._staff()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        iv = services.schedule_interview(request, d["application"], interview_type=d["interview_type"], scheduled_at=d["scheduled_at"],
                                         interviewers=d["interviewers"], meeting_link=d.get("meeting_link", ""))
        return ok(self.get_serializer(iv).data, "Interview scheduled", 201)

    def partial_update(self, request, *a, **kw):
        self._staff()
        iv = self.get_object()
        if "status" in request.data and request.data["status"] in ("SCHEDULED", "COMPLETED", "CANCELLED"):
            iv.status = request.data["status"]
            iv.save(update_fields=["status", "updated_at"])
        return ok(self.get_serializer(iv).data, "Interview updated")

    @action(detail=True, methods=["post"])
    def feedback(self, request, pk=None):
        iv = self.get_object()   # staff or an assigned interviewer only
        s = FeedbackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        fb, _ = InterviewFeedback.objects.update_or_create(interview=iv, reviewer=request.user, defaults=s.validated_data)
        iv.status = "COMPLETED"
        iv.save(update_fields=["status", "updated_at"])
        audit.log(request, "INTERVIEW_FEEDBACK", "Interview", iv.pk, new={"rating": fb.rating})
        return ok(FeedbackSerializer(fb).data, "Feedback submitted", 201)


class OfferViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = OfferSerializer
    permission_classes = [IsRecruitmentStaff]
    filterset_fields = ["status"]
    queryset = Offer.objects.select_related("application__candidate", "application__job", "department")

    def create(self, request, *a, **kw):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        o = services.create_offer(request, d["application"], salary=d["salary"], joining_date=d["joining_date"], expiry_date=d["expiry_date"],
                                  position=d.get("position", ""), department=d.get("department"), send=bool(request.data.get("send")))
        return ok(self.get_serializer(o).data, "Offer generated", 201)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        o = services.send_offer(request, self.get_object())
        return ok(self.get_serializer(o).data, "Offer sent")

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        o = self.get_object()
        r = HttpResponse(offer_letter_pdf(o), content_type="application/pdf")
        r["Content-Disposition"] = f'attachment; filename="offer-{o.pk}.pdf"'
        return r


# ---------------- public (candidate-facing) endpoints
class PublicJobSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Job
        fields = ["id", "title", "department_name", "description", "skills_required", "experience_min", "location", "employment_type"]


class ApplySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    skills = serializers.CharField(max_length=300, required=False, allow_blank=True)
    experience_years = serializers.DecimalField(max_digits=4, decimal_places=1, min_value=0, max_value=60, required=False, default=0)
    education = serializers.CharField(max_length=160, required=False, allow_blank=True)
    current_company = serializers.CharField(max_length=120, required=False, allow_blank=True)
    expected_salary = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    notice_period_days = serializers.IntegerField(min_value=0, max_value=365, required=False, default=0)


class CareersViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    throttle_scope = "public_apply"
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicJobSerializer
    queryset = Job.objects.filter(status="OPEN").select_related("department")
    pagination_class = None
    filter_backends = []

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def apply(self, request, pk=None):
        job = self.get_object()
        s = ApplySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        resume = request.FILES.get("resume")
        if resume:
            validate_upload(resume, allowed=("pdf",))
        services.apply_to_job(request, job, dict(s.validated_data), resume)
        return ok({}, "Application submitted successfully", 201)


from drf_spectacular.types import OpenApiTypes as _T
from drf_spectacular.utils import extend_schema as _es


@_es(request=_T.OBJECT, responses=_T.OBJECT)
class PublicOfferView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "public_apply"

    def get(self, request, token):
        o = Offer.objects.select_related("application__candidate", "department").filter(token=token).first()
        if not o:
            raise ServiceError("Offer not found.", 404)
        return ok({"candidate": o.application.candidate.name, "position": o.position, "department": o.department.name if o.department else None,
                   "salary": o.salary, "joining_date": o.joining_date, "expiry_date": o.expiry_date, "status": o.status})

    def post(self, request, token):
        if not Offer.objects.filter(token=token).exists():
            raise ServiceError("Offer not found.", 404)
        o = services.respond_offer(token, request.data.get("decision", ""))
        return ok({"status": o.status}, f"Offer {o.status.lower()}")
