from django.db import models


class Mission(models.Model):
    class Period(models.TextChoices):
        DAILY = "DAILY", "일일"
        WEEKLY = "WEEKLY", "주간"

    class MissionType(models.TextChoices):
        TOTAL_DISTANCE = "TOTAL_DISTANCE", "누적 산책 거리"
        TOTAL_DURATION = "TOTAL_DURATION", "누적 산책 시간"
        WALK_COUNT = "WALK_COUNT", "산책 횟수"
        WALK_DISTANCE_AT_LEAST = "WALK_DISTANCE_AT_LEAST", "1회 산책 거리"
        WALK_DURATION_AT_LEAST = "WALK_DURATION_AT_LEAST", "1회 산책 시간"
        DISTINCT_WALK_DAYS = "DISTINCT_WALK_DAYS", "산책 일수"
        NEW_FRIEND_COUNT = "NEW_FRIEND_COUNT", "새 친구 수"

    title = models.CharField(max_length=100)
    period = models.CharField(choices=Period.choices)
    mission_type = models.CharField(choices=MissionType.choices)
    
    goal = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    required_count = models.PositiveIntegerField(
        default=1,
    )


class PetMission(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        CLAIMABLE = "CLAIMABLE", "보상 수령 가능"
        CLAIMED = "CLAIMED", "보상 수령 완료"

    pet = models.ForeignKey(
        "pets.Pet",
        on_delete=models.CASCADE,
        related_name="pet_missions",
    )

    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name="pet_missions",
    )

    period_start = models.DateField()
    period_end = models.DateField()

    # 거리 또는 시간의 현재 누적값
    # 거리: 미터, 시간: 초
    current_value = models.PositiveIntegerField(default=0)

    # 산책 횟수, 조건 달성 횟수, 친구 수 등의 현재값
    current_count = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    claimed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("pet", "mission", "period_start"),
                name="unique_pet_mission_period",
            ),
        ]

    def __str__(self):
        return f"{self.pet.name} - {self.mission.title}"