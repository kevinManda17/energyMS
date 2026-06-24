"""Root URL configuration for the EMS backend."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path("api/auth/", include("apps.users.urls")),
    # Domain apps
    path("api/", include("apps.houses.urls")),
    path("api/", include("apps.energy_assets.urls")),
    path("api/", include("apps.devices.urls")),
    path("api/", include("apps.measurements.urls")),
    path("api/", include("apps.forecasting.urls")),
    path("api/", include("apps.fuzzy_engine.urls")),
    path("api/", include("apps.alerts.urls")),
    path("api/", include("apps.reports.urls")),
    # OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
