from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("leaves", api.LeaveRequestViewSet, basename="leave")
router.register("leave-balances", api.LeaveBalanceViewSet, basename="leave-balance")
router.register("leave-types", api.LeaveTypeViewSet, basename="leave-type")
urlpatterns = router.urls
