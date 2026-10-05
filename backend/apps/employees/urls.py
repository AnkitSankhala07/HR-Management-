from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("employees", api.EmployeeViewSet, basename="employee")
router.register("departments", api.DepartmentViewSet, basename="department")
router.register("directory", api.DirectoryViewSet, basename="directory")
router.register("designations", api.DesignationViewSet, basename="designation")
urlpatterns = router.urls
