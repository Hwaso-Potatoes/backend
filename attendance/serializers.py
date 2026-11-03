from rest_framework import serializers

from missions.models import Accessory

from .models import AttendanceReward


class AttendanceAccessorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory

        fields = (
            "id",
            "name",
            "image",
            "category",
        )

        read_only_fields = fields


class AttendanceRewardSerializer(serializers.ModelSerializer):
    attendance_date = serializers.DateField(
        source="attendance.attendance_date",
        read_only=True,
    )

    accessory = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceReward

        fields = (
            "id",
            "attendance_date",
            "opened",
            "opened_at",
            "accessory",
        )

        read_only_fields = fields

    def get_accessory(self, obj):
        if not obj.opened:
            return None

        return AttendanceAccessorySerializer(
            obj.accessory,
            context=self.context,
        ).data


class AttendanceCalendarQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(
        min_value=2000,
        max_value=2100,
    )

    month = serializers.IntegerField(
        min_value=1,
        max_value=12,
    )