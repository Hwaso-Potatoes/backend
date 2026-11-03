from django.utils import timezone
from rest_framework import serializers


class ReportPeriod:
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"

    CHOICES = [
        (DAY, "하루"),
        (MONTH, "월간"),
        (YEAR, "연간"),
    ]


class ComparisonType:
    RECENT_AVERAGE = "RECENT_AVERAGE"
    PREVIOUS_MONTH = "PREVIOUS_MONTH"
    PREVIOUS_YEAR = "PREVIOUS_YEAR"

    CHOICES = [
        (RECENT_AVERAGE, "최근 평균"),
        (PREVIOUS_MONTH, "지난달"),
        (PREVIOUS_YEAR, "작년"),
    ]


class ReportQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=ReportPeriod.CHOICES,
        default=ReportPeriod.DAY,
    )
    date = serializers.DateField(
        required=False,
        default=timezone.localdate,
    )

    def validate_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("미래 날짜의 리포트는 조회할 수 없습니다.")

        return value


class DistanceComparisonSerializer(serializers.Serializer):
    current_distance_km = serializers.FloatField()
    baseline_distance_km = serializers.FloatField()
    difference_km = serializers.FloatField()

    baseline_type = serializers.ChoiceField(
        choices=ComparisonType.CHOICES,
    )


class TrendItemSerializer(serializers.Serializer):
    key = serializers.IntegerField()
    label = serializers.CharField()
    distance_km = serializers.FloatField()


class TrendSerializer(serializers.Serializer):
    current = TrendItemSerializer(many=True)
    comparison = TrendItemSerializer(many=True)


class HighlightItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    distance_km = serializers.FloatField()


class HighlightSerializer(serializers.Serializer):
    top_label = serializers.CharField(
        allow_null=True,
    )
    top_distance_km = serializers.FloatField()
    items = HighlightItemSerializer(many=True)


class PetWalkReportSerializer(serializers.Serializer):
    pet_id = serializers.IntegerField()

    period = serializers.ChoiceField(
        choices=ReportPeriod.CHOICES,
    )

    date = serializers.DateField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    comparison = DistanceComparisonSerializer()
    trend = TrendSerializer()
    highlight = HighlightSerializer()