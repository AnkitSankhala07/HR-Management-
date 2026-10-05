from django.urls import path

from . import reports

urlpatterns = [
    path("reports/<str:kind>/", reports.ReportView.as_view()),
]
