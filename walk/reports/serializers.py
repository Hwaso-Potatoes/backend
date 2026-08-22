from rest_framework import serializers


class ReportPeriodQuerySerializer(serializers.Serializer):
    class Period:
        DAY = "DAY"
        WEEK = "WEEK"
        MONTH = "MONTH"
        SIX_MONTHS = "SIX_MONTHS"
        YEAR = "YEAR"

        CHOICES = [
            (DAY, "1일"),
            (WEEK, "1주"),
            (MONTH, "1개월"),
            (SIX_MONTHS, "6개월"),
            (YEAR, "1년"),
        ]

    period = serializers.ChoiceField(
        choices=Period.CHOICES,
        default=Period.WEEK,
    )


class ReportSummarySerializer(serializers.Serializer):
    total_walk_count = serializers.IntegerField()
    total_distance_km = serializers.FloatField()
    total_duration_minutes = serializers.IntegerField()
    average_distance_km = serializers.FloatField()
    average_duration_minutes = serializers.FloatField()


class ReportChartItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    distance_km = serializers.FloatField()
    duration_minutes = serializers.IntegerField()
    walk_count = serializers.IntegerField()


class PetHistoryItemSerializer(serializers.Serializer):
    before_level = serializers.IntegerField()
    after_level = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class GrowthReportSerializer(serializers.Serializer):
    level_up_count = serializers.IntegerField()
    histories = PetHistoryItemSerializer(many=True)

class EarnedBadgeSerializer(serializers.Serializer):
    badge_id = serializers.IntegerField()
    name = serializers.CharField()
    acquired_at = serializers.DateTimeField()


class PetWalkReportSerializer(serializers.Serializer):
    pet_id = serializers.IntegerField()
    period = serializers.ChoiceField(
        choices=ReportPeriodQuerySerializer.Period.CHOICES
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    summary = ReportSummarySerializer()
    chart = ReportChartItemSerializer(many=True)
    growth = GrowthReportSerializer()
    earned_badges = EarnedBadgeSerializer(many=True)