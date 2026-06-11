from rest_framework import serializers


class CustomerFeatureSerializer(serializers.Serializer):
    """Validates one customer's RFM (recency/frequency/monetary) features."""

    customer_id = serializers.CharField(max_length=64)
    recency_days = serializers.FloatField(min_value=0)
    frequency = serializers.FloatField(min_value=0)
    monetary = serializers.FloatField(min_value=0)


class ClusterRequestSerializer(serializers.Serializer):
    """Validates a clustering request: cluster count k and customer features."""

    k = serializers.IntegerField(required=False, min_value=2, max_value=10, default=4)
    customers = CustomerFeatureSerializer(many=True)


class SegmentSerializer(serializers.Serializer):
    """Serializes a customer segment assignment with its RFM features."""

    customer_id = serializers.CharField()
    cluster = serializers.IntegerField()
    distance = serializers.FloatField()
    recency_days = serializers.FloatField()
    frequency = serializers.FloatField()
    monetary = serializers.FloatField()
