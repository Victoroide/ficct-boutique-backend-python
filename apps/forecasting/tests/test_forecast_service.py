from apps.forecasting.services.forecast_service import ForecastService


def test_constant_series_is_forecast_constant():
    svc = ForecastService()
    points = svc.forecast_series([100, 100, 100, 100, 100], horizon=3)
    assert len(points) == 3
    for p in points:
        assert 90 < p.value < 110


def test_increasing_series_extrapolates_upward():
    svc = ForecastService()
    points = svc.forecast_series([10, 20, 30, 40, 50], horizon=2)
    assert points[1].value > points[0].value > 50


def test_empty_series_returns_empty():
    svc = ForecastService()
    assert svc.forecast_series([], horizon=4) == []
