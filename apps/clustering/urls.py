from django.urls import path

from .viewsets import AllSegmentsView, CustomerSegmentView, RunClusteringView

urlpatterns = [
    path("run/", RunClusteringView.as_view(), name="run"),
    path("segments/", AllSegmentsView.as_view(), name="segments"),
    path("segments/<str:customer_id>/", CustomerSegmentView.as_view(), name="segment-detail"),
]
