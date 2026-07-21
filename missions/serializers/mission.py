from rest_framework import serializers

from missions.models import Mission, PetMission


class MissionListQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=Mission.Period.choices,
    )


class MissionListSerializer(serializers.ModelSerializer):
    pet_mission_id = serializers.IntegerField(
        source="id",
        read_only=True,
    )
    mission_id = serializers.IntegerField(
        source="mission.id",
        read_only=True,
    )
    title = serializers.CharField(
        source="mission.title",
        read_only=True,
    )
    period = serializers.CharField(
        source="mission.period",
        read_only=True,
    )
    mission_type = serializers.CharField(
        source="mission.mission_type",
        read_only=True,
    )
    goal = serializers.IntegerField(
        source="mission.goal",
        read_only=True,
        allow_null=True,
    )
    required_count = serializers.IntegerField(
        source="mission.required_count",
        read_only=True,
    )
    reward_experience = serializers.IntegerField(
        source="mission.reward_experience",
        read_only=True,
    )

    reward_badge = serializers.SerializerMethodField()
    reward_accessory = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = PetMission
        fields = (
            "pet_mission_id",
            "mission_id",
            "title",
            "period",
            "mission_type",
            "goal",
            "required_count",
            "current_value",
            "current_count",
            "progress_percent",
            "status",
            "reward_experience",
            "reward_badge",
            "reward_accessory",
            "period_start",
            "period_end",
            "completed_at",
            "claimed_at",
        )
        read_only_fields = fields

    def get_progress_percent(self, obj):
        count_based_types = {
            Mission.MissionType.WALK_COUNT,
            Mission.MissionType.WALK_DISTANCE_AT_LEAST,
            Mission.MissionType.WALK_DURATION_AT_LEAST,
            Mission.MissionType.DISTINCT_WALK_DAYS,
            Mission.MissionType.NEW_FRIEND_COUNT,
        }

        if obj.mission.mission_type in count_based_types:
            current = obj.current_count
            target = obj.mission.required_count
        else:
            current = obj.current_value
            target = obj.mission.goal

        if not target:
            return 0

        return min(
            100,
            int(current / target * 100),
        )

    def get_reward_badge(self, obj):
        badge = obj.mission.reward_badge

        if badge is None:
            return None

        image_url = None

        if badge.image:
            request = self.context.get("request")

            image_url = (
                request.build_absolute_uri(badge.image.url)
                if request
                else badge.image.url
            )

        return {
            "id": badge.id,
            "name": badge.name,
            "image": image_url,
        }

    def get_reward_accessory(self, obj):
        accessory = obj.mission.reward_accessory

        if accessory is None:
            return None

        image_url = None

        if accessory.image:
            request = self.context.get("request")

            image_url = (
                request.build_absolute_uri(accessory.image.url)
                if request
                else accessory.image.url
            )

        return {
            "id": accessory.id,
            "name": accessory.name,
            "image": image_url,
        }