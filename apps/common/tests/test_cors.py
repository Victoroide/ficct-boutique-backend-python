"""CORS allow-list regression tests.

Guards the Angular Admin AI panel outage: the production browser origins must
always be allowed so that a preflight returns ``Access-Control-Allow-Origin``.
Without it the browser blocks the response and the panel reports
``Http failure response ... 0 Unknown Error``.
"""

from django.conf import settings
from django.test import Client, override_settings

ANGULAR_ORIGINS = [
    "https://angular-admin-production.up.railway.app",
    "https://admin.boutique.ficct.com",
]

# Endpoints the admin AI panel calls (forecast, clustering, segment list).
PREFLIGHT_PATHS = [
    "/api/v1/forecasting/run/",
    "/api/v1/clustering/run/",
    "/api/v1/clustering/segments/",
]


def test_production_angular_origins_are_always_allowed():
    for origin in ANGULAR_ORIGINS:
        assert origin in settings.CORS_ALLOWED_ORIGINS


def test_env_origins_are_preserved_without_duplicates():
    # The localhost dev default must survive next to the baked-in prod origins,
    # and merging must not introduce duplicates.
    assert "http://localhost:4200" in settings.CORS_ALLOWED_ORIGINS
    assert len(settings.CORS_ALLOWED_ORIGINS) == len(set(settings.CORS_ALLOWED_ORIGINS))


@override_settings(CORS_ALLOW_ALL_ORIGINS=False)
def test_preflight_reflects_angular_origin_on_ai_endpoints():
    client = Client()
    for origin in ANGULAR_ORIGINS:
        for path in PREFLIGHT_PATHS:
            resp = client.options(
                path,
                HTTP_ORIGIN=origin,
                HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
                HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,authorization",
            )
            assert (
                resp.headers.get("Access-Control-Allow-Origin") == origin
            ), f"preflight for {path} did not allow origin {origin}"
