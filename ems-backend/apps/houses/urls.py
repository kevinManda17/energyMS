from django.urls import path
from rest_framework.routers import DefaultRouter

from .reference_views import ReferenceView
from .views import HouseViewSet

router = DefaultRouter()
router.register("houses", HouseViewSet, basename="house")

urlpatterns = router.urls + [
    # Énumérations de référence. Servies par l'API pour que les libellés
    # cessent d'être écrits en dur dans le web et le mobile — trois listes
    # pour la même énumération, qui ne coïncidaient pas.
    path("reference/", ReferenceView.as_view(), name="reference"),
]
