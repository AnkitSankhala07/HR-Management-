from rest_framework.routers import DefaultRouter

from .api import PayrollViewSet

router = DefaultRouter()
router.register("payroll", PayrollViewSet, basename="payroll")
urlpatterns = router.urls
