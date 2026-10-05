from rest_framework.routers import DefaultRouter

from .api import EmployeeSkillViewSet, SkillViewSet

router = DefaultRouter()
router.register("skills", EmployeeSkillViewSet, basename="skill")
router.register("skill-catalog", SkillViewSet, basename="skill-catalog")
urlpatterns = router.urls
