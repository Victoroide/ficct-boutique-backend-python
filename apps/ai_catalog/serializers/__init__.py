from rest_framework import serializers


class SimilarityRequestSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)


class SimilarityResultItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    category = serializers.CharField(allow_blank=True)
    image_url = serializers.CharField(allow_blank=True)
    sku = serializers.CharField(allow_blank=True)
    score = serializers.FloatField()


class CatalogSyncItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    image_url = serializers.URLField()
    name = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    sku = serializers.CharField(required=False, allow_blank=True)


class CatalogSyncBatchSerializer(serializers.Serializer):
    items = CatalogSyncItemSerializer(many=True)
