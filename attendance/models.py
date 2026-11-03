from django.conf import settings
from django.db import models


# 하루 출석 기록
class Attendance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendances",
    )

    pet = models.ForeignKey(
        "pets.Pet",
        on_delete=models.CASCADE,
        related_name="attendances",
    )

    attendance_date = models.DateField(db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attendance_date"]

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "user",
                    "attendance_date",
                ),
                name="unique_daily_attendance",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.attendance_date}"
        )


# 관리자가 지정하는 보상 날짜
class AttendanceRewardDay(models.Model):
    reward_date = models.DateField(
        unique=True,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reward_date"]

    def __str__(self):
        return str(self.reward_date)


# 액세서리 지급 기록
class AttendanceReward(models.Model):
    attendance = models.OneToOneField(
        Attendance,
        on_delete=models.CASCADE,
        related_name="reward",
    )

    accessory = models.ForeignKey(
        "missions.Accessory",
        on_delete=models.PROTECT,
        related_name="attendance_rewards",
    )

    opened = models.BooleanField(default=False)

    opened_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.attendance} - "
            f"{self.accessory.name}"
        )