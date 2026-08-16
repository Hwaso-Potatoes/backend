from rest_framework import serializers

from missions.models import Mission, PetMission


class MissionListQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=Mission.Period.choices,
    )


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = (
            "id",
            "title",
            "period",
            "mission_type",
        )
        read_only_fields = fields


class MissionListSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        source="mission.title",
        read_only=True,
    )

    progress = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()

    class Meta:
        model = PetMission
        fields = (
            "id",
            "title",
            "progress",
            "status",
            "can_claim",
        )
        read_only_fields = fields

    def get_progress(self, obj):
        mission_type = obj.mission.mission_type

        if mission_type == Mission.MissionType.WALK_COUNT:
            current = obj.current_count
            target = obj.mission.required_count
            unit = "회"

        elif mission_type == Mission.MissionType.DISTINCT_WALK_DAYS:
            current = obj.current_count
            target = obj.mission.required_count
            unit = "일"

        elif mission_type == Mission.MissionType.NEW_FRIEND_COUNT:
            current = obj.current_count
            target = obj.mission.required_count
            unit = "명"

        elif mission_type in (
            Mission.MissionType.TOTAL_DISTANCE,
            Mission.MissionType.WALK_DISTANCE_AT_LEAST,
        ):
            current = round(obj.current_value / 1000, 2)
            target = round((obj.mission.goal or 0) / 1000, 2)
            unit = "km"

        elif mission_type in (
            Mission.MissionType.TOTAL_DURATION,
            Mission.MissionType.WALK_DURATION_AT_LEAST,
        ):
            current = round(obj.current_value / 60, 1)
            target = round((obj.mission.goal or 0) / 60, 1)
            unit = "분"

        else:
            current = 0
            target = 0
            unit = ""

        percent = (
            min(100, int(current / target * 100))
            if target > 0
            else 0
        )

        return {
            "current": current,
            "target": target,
            "unit": unit,
            "percent": percent,
        }

    def get_can_claim(self, obj):
        return (
            obj.status == PetMission.Status.CLAIMABLE
            and obj.claimed_at is None
        )