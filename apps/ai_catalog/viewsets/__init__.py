from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.auth.permissions import IsAdminOrStaff

from ..serializers import (
    CatalogSyncBatchSerializer,
    SimilarityRequestSerializer,
    SimilarityResultItemSerializer,
)
from ..services.catalog_sync_service import catalog_sync_service
from ..services.similarity_service import similarity_service


class SimilaritySearchView(APIView):
    """POST endpoint: visual similarity search.

    Accepts a multipart-uploaded image and returns the top-k most similar
    catalog products by embedding cosine similarity. Requires authentication.
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        serializer = SimilarityRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        img = serializer.validated_data["image"]
        top_k = serializer.validated_data["top_k"]
        image_bytes = img.read()
        results = similarity_service.search(image_bytes, top_k=top_k)
        return Response(
            {"results": SimilarityResultItemSerializer(results, many=True).data},
            status=status.HTTP_200_OK,
        )


class CatalogSyncView(APIView):
    """POST endpoint: batch-sync catalog products into the embedding store.

    Computes and upserts reference-image embeddings for a batch of products,
    returning per-item sync results and errors. Restricted to admin/staff.
    """

    parser_classes = [JSONParser]
    permission_classes = [IsAdminOrStaff]

    def post(self, request) -> Response:
        serializer = CatalogSyncBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        synced = []
        errors = []
        for item in serializer.validated_data["items"]:
            try:
                result = catalog_sync_service.sync_from_image_url(
                    product_id=item["product_id"],
                    image_url=item["image_url"],
                    name=item.get("name"),
                    category=item.get("category"),
                    sku=item.get("sku"),
                )
                synced.append(
                    {"product_id": item["product_id"], "embedding_dim": result["embedding_dim"]}
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"product_id": item["product_id"], "error": str(exc)})
        return Response({"synced": synced, "errors": errors})


class EmbeddingListView(APIView):
    """GET endpoint: list stored catalog embeddings (vectors omitted).

    Returns embedding metadata for all synced products, stripping the bulky
    vector itself from each item. Restricted to admin/staff.
    """

    permission_classes = [IsAdminOrStaff]

    def get(self, request) -> Response:
        items = catalog_sync_service.all_embeddings()
        # Strip the embedding vector itself from the listing endpoint;
        # full vectors are large and only the search endpoint needs them.
        thin = [{k: v for k, v in item.items() if k not in {"embedding"}} for item in items]
        return Response({"items": thin})
