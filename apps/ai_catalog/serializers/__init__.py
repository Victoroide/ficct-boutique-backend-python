from rest_framework import serializers


class SimilarityRequestSerializer(serializers.Serializer):
    """Validates a similarity-search request: an uploaded image and top_k."""

    image = serializers.ImageField(required=True)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)


class SimilarityResultItemSerializer(serializers.Serializer):
    """Serializes a single similarity-search hit with its similarity score."""

    product_id = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    category = serializers.CharField(allow_blank=True)
    image_url = serializers.CharField(allow_blank=True)
    sku = serializers.CharField(allow_blank=True)
    score = serializers.FloatField()


class CatalogSyncItemSerializer(serializers.Serializer):
    """Validates one product entry in a catalog-sync batch."""

    product_id = serializers.CharField()
    image_url = serializers.URLField()
    name = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    sku = serializers.CharField(required=False, allow_blank=True)


class CatalogSyncBatchSerializer(serializers.Serializer):
    """Validates a catalog-sync request wrapping a list of product items."""

    items = CatalogSyncItemSerializer(many=True)
