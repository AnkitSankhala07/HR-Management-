from django.urls import path
from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("jobs", api.JobViewSet, basename="job")
router.register("candidates", api.CandidateViewSet, basename="candidate")
router.register("applications", api.ApplicationViewSet, basename="application")
router.register("interviews", api.InterviewViewSet, basename="interview")
router.register("offers", api.OfferViewSet, basename="offer")
router.register("careers", api.CareersViewSet, basename="careers")
urlpatterns = [path("offers/public/<uuid:token>/", api.PublicOfferView.as_view())] + router.urls
