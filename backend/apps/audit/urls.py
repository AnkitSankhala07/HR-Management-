from rest_framework.routers import DefaultRouter

from .api import AuditViewSet

router = DefaultRouter()
router.register("audit", AuditViewSet, basename="audit")
urlpatterns = router.urls
