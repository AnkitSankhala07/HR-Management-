from rest_framework.routers import DefaultRouter

from .api import AttendanceViewSet

router = DefaultRouter()
router.register("attendance", AttendanceViewSet, basename="attendance")
urlpatterns = router.urls
