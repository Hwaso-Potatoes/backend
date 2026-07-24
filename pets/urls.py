from rest_framework.routers import DefaultRouter
from .views import DogViewSet

router = DefaultRouter()
router.register("pets", DogViewSet, basename="pet")

urlpatterns = router.urls