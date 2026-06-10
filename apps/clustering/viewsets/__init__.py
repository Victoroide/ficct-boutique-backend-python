from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.auth.permissions import IsAdminOrStaff
from ..serializers import ClusterRequestSerializer, SegmentSerializer
from ..services.clustering_service import ClusteringService, CustomerFeatures, clustering_service


class RunClusteringView(APIView):
    permission_classes = [IsAdminOrStaff]

    def post(self, request) -> Response:
        serializer = ClusterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        features = [
            CustomerFeatures(
                customer_id=row["customer_id"],
                recency_days=row["recency_days"],
                frequency=row["frequency"],
                monetary=row["monetary"],
            )
            for row in serializer.validated_data["customers"]
        ]
        segments = clustering_service.fit_segments(features, k=serializer.validated_data["k"])
        run = clustering_service.persist(segments, metadata={"k": serializer.validated_data["k"], "n": len(features)})
        return Response(
            {
                "run": run,
                "segments": SegmentSerializer(
                    [
                        {
                            "customer_id": s.customer_id,
                            "cluster": s.cluster,
                            "distance": s.distance,
                            "recency_days": s.recency_days,
                            "frequency": s.frequency,
                            "monetary": s.monetary,
                        }
                        for s in segments
                    ],
                    many=True,
                ).data,
            }
        )


class CustomerSegmentView(APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request, customer_id: str) -> Response:
        item = clustering_service.segment_for(customer_id)
        if not item:
            return Response({"segment": None})
        return Response(
            {
                "segment": {
                    "customer_id": item["customer_id"],
                    "cluster": int(item.get("cluster", -1)),
                    "distance": float(item.get("distance", 0.0)),
                    "recency_days": float(item.get("recency_days", 0.0)),
                    "frequency": float(item.get("frequency", 0.0)),
                    "monetary": float(item.get("monetary", 0.0)),
                    "run_id": item.get("run_id", ""),
                    "computed_at": item.get("computed_at", ""),
                }
            }
        )


class AllSegmentsView(APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request) -> Response:
        items = clustering_service.all_segments()
        return Response(
            {
                "segments": [
                    {
                        "customer_id": i["customer_id"],
                        "cluster": int(i.get("cluster", -1)),
                        "distance": float(i.get("distance", 0.0)),
                        "recency_days": float(i.get("recency_days", 0.0)),
                        "frequency": float(i.get("frequency", 0.0)),
                        "monetary": float(i.get("monetary", 0.0)),
                        "run_id": i.get("run_id", ""),
                    }
                    for i in items
                ]
            }
        )
