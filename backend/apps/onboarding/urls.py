from rest_framework.routers import DefaultRouter

from .api import OnboardingTaskViewSet, OnboardingViewSet

router = DefaultRouter()
router.register("onboarding", OnboardingViewSet, basename="onboarding")
router.register("onboarding-tasks", OnboardingTaskViewSet, basename="onboarding-task")
urlpatterns = router.urls
