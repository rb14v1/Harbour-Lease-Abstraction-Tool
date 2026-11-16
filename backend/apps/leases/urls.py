from rest_framework.routers import DefaultRouter

from .views import LeaseViewSet, PropertyViewSet

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="property")
router.register("leases", LeaseViewSet, basename="lease")

urlpatterns = router.urls
