from rest_framework.routers import DefaultRouter

from .api import RecognitionViewSet

router = DefaultRouter()
router.register("recognition", RecognitionViewSet, basename="recognition")
urlpatterns = router.urls
