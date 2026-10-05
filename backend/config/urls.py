from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

api = [
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.employees.urls")),
    path("", include("apps.attendance.urls")),
    path("", include("apps.leave.urls")),
    path("", include("apps.payroll.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.announcements.urls")),
    path("", include("apps.goals.urls")),
    path("", include("apps.skills.urls")),
    path("", include("apps.recognition.urls")),
    path("", include("apps.recruitment.urls")),
    path("", include("apps.onboarding.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.common.api_urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include("apps.common.page_urls")),
]
if settings.DEBUG:   # profile photos / resumes are served by Django only in development (documents always go through permission-checked views)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "apps.common.pages.error_403"
handler404 = "apps.common.pages.error_404"
handler500 = "apps.common.pages.error_500"
