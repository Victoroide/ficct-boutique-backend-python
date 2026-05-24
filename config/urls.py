from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.common.views.health import HealthView

api_v1 = [
    path("health/", HealthView.as_view(), name="health"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="v1:schema"),
        name="swagger",
    ),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="v1:schema"),
        name="redoc",
    ),
    path("ai/", include(("apps.ai_catalog.urls", "ai_catalog"), namespace="ai_catalog")),
    path(
        "forecasting/",
        include(("apps.forecasting.urls", "forecasting"), namespace="forecasting"),
    ),
    path(
        "clustering/",
        include(("apps.clustering.urls", "clustering"), namespace="clustering"),
    ),
]

urlpatterns = [
    path("api/v1/", include((api_v1, "v1"), namespace="v1")),
]
