from rest_framework import serializers


class ForecastRequestSerializer(serializers.Serializer):
    """Validates a forecast request: scope, historical series, and horizon."""

    scope = serializers.CharField(max_length=120)
    series = serializers.ListField(
        child=serializers.FloatField(min_value=0),
        min_length=1,
        max_length=240,
    )
    horizon = serializers.IntegerField(required=False, min_value=1, max_value=24, default=4)


class ForecastPointSerializer(serializers.Serializer):
    """Serializes a single forecast point (period index and value)."""

    period_index = serializers.IntegerField()
    value = serializers.FloatField()


class ForecastResultSerializer(serializers.Serializer):
    """Serializes a complete forecast result with its points."""

    scope = serializers.CharField()
    horizon = serializers.IntegerField()
    computed_at = serializers.CharField()
    points = ForecastPointSerializer(many=True)
