from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.auth.permissions import IsAdminOrStaff

from ..serializers import ForecastRequestSerializer, ForecastResultSerializer
from ..services.forecast_service import forecast_service


class RunForecastView(APIView):
    """POST endpoint: compute and persist a demand forecast for a scope.

    Runs exponential-smoothing forecasting over the supplied historical series
    and stores the result, returning the forecast points. Restricted to admin/staff.
    """

    permission_classes = [IsAdminOrStaff]

    def post(self, request) -> Response:
        serializer = ForecastRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        points = forecast_service.forecast_series(
            series=serializer.validated_data["series"],
            horizon=serializer.validated_data["horizon"],
        )
        item = forecast_service.persist(
            scope=serializer.validated_data["scope"],
            points=points,
            metadata={"series_len": len(serializer.validated_data["series"])},
        )
        # normalize for response
        return Response(
            {
                "scope": item["scope"],
                "horizon": item["horizon"],
                "computed_at": item["computed_at"],
                "points": [
                    {"period_index": p["period_index"], "value": float(p["value"])}
                    for p in item["points"]
                ],
            }
        )


class LatestForecastView(APIView):
    """GET endpoint: return the most recent persisted forecast for a scope.

    Looks up the latest stored forecast for the given scope, or null if none
    exists. Restricted to admin/staff.
    """

    permission_classes = [IsAdminOrStaff]

    def get(self, request, scope: str) -> Response:
        item = forecast_service.latest(scope)
        if not item:
            return Response({"forecast": None})
        return Response(
            {
                "scope": item["scope"],
                "horizon": int(item["horizon"]),
                "computed_at": item["computed_at"],
                "points": [
                    {"period_index": int(p["period_index"]), "value": float(p["value"])}
                    for p in item["points"]
                ],
            }
        )
