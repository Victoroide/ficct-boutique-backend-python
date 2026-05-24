from django.urls import path

from .viewsets import LatestForecastView, RunForecastView

urlpatterns = [
    path("run/", RunForecastView.as_view(), name="run"),
    path("latest/<str:scope>/", LatestForecastView.as_view(), name="latest"),
]
