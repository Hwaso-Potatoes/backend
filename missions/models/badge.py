from django.db import models


class Badge(models.Model):
    class ConditionType(models.TextChoices):
        FIRST_FRIEND = "FIRST_FRIEND", "첫 친구 추가"
        LEVEL = "LEVEL", "레벨 달성"

        RAINY_WALK = "RAINY_WALK", "비 오는 날 산책"
        SNOWY_WALK = "SNOWY_WALK", "눈 오는 날 산책"

        TOTAL_DURATION = "TOTAL_DURATION", "누적 산책 시간"
        TOTAL_DISTANCE = "TOTAL_DISTANCE", "누적 산책 거리"

        FIRST_WALK = "FIRST_WALK", "첫 산책"
        CONSECUTIVE_DAYS = "CONSECUTIVE_DAYS", "연속 산책 일수"
        DAILY_WALK_COUNT = "DAILY_WALK_COUNT", "하루 산책 횟수"

        NEW_REGION = "NEW_REGION", "새로운 지역 산책"
        FOREST_WALK = "FOREST_WALK", "숲속 산책"
        CITY_WALK = "CITY_WALK", "도시 산책"

    name = models.CharField(max_length=100)

    image = models.ImageField(upload_to="badges/")

    description = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    condition_type = models.CharField(
        max_length=30,
        choices=ConditionType.choices,
    )

    goal = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class PetBadge(models.Model):
    pet = models.ForeignKey(
        "pets.Pet",
        on_delete=models.CASCADE,
        related_name="pet_badges",
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="pet_badges",
    )
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("pet", "badge"),
                name="unique_pet_badge",
            ),
        ]

    def __str__(self):
        return f"{self.pet.name} - {self.badge.name}"