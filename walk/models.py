from django.db import models
from django.utils import timezone
from django.conf import settings


class WalkingSession(models.Model):
    STATUS_CHOICES = [
        ('WALKING', '산책 중'),
        ('PAUSED', '일시 정지'),
        ('FINISHED', '산책 종료'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='walking_sessions'
    )

    pet = models.ForeignKey(
        'pets.Pet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='walking_sessions'
    )

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='WALKING')

    # 누적 데이터 (단위: km, 분)
    total_distance = models.FloatField(default=0.0)   # 단위: km
    total_duration = models.IntegerField(default=0)  # 단위: 분(minutes)

    # 일시정지 누적 시간 (단위: 초)
    paused_time = models.IntegerField(default=0)
    last_paused_at = models.DateTimeField(null=True, blank=True)

    # 실시간 위치 공유 여부 (이번 산책 세션 기준)
    is_location_shared = models.BooleanField(default=False)

    # 위치 유형 판정 결과 (산책 종료 후 백그라운드에서 채워짐. None = 판정 전/판정 불가)
    is_forest_walk = models.BooleanField(null=True, blank=True)
    is_city_walk = models.BooleanField(null=True, blank=True)
    is_new_area = models.BooleanField(null=True, blank=True)
    classified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-start_time']),
        ]

    def __str__(self):
        pet_name = self.pet.name if self.pet else "반려견 미지정"
        user_info = getattr(self.user, 'email', str(self.user))
        return f"{pet_name}(보호자: {user_info})의 산책 ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

    def get_pure_duration_seconds(self):
        """총 소요 시간 중 일시정지 시간을 뺀 '순수 산책 시간(초)'"""
        end = self.end_time or timezone.now()
        total_seconds = int((end - self.start_time).total_seconds())

        current_paused = self.paused_time
        if self.status == 'PAUSED' and self.last_paused_at:
            current_paused += int((timezone.now() - self.last_paused_at).total_seconds())

        return max(0, total_seconds - current_paused)


class WalkingPath(models.Model):
    session = models.ForeignKey(
        WalkingSession,
        on_delete=models.CASCADE,
        related_name='paths'
    )

    latitude = models.DecimalField(max_digits=11, decimal_places=8)
    longitude = models.DecimalField(max_digits=12, decimal_places=8)

    # 서버에 저장된 시각
    timestamp = models.DateTimeField(auto_now_add=True)
    # 기기에서 측정한 시각 (미전송 시 서버 시각, 기존 데이터는 timestamp로 채움)
    recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['recorded_at', 'id']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['session', 'recorded_at'], name='walkpath_session_recorded_idx'),
        ]

    def __str__(self):
        return f"Session {self.session_id} - [{self.latitude}, {self.longitude}]"


class WalkPreference(models.Model):
    """산책 관련 사용자 설정"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='walk_preference'
    )
    # 알림설정 화면의 '산책 시 위치 공유'
    share_location_on_walk = models.BooleanField(default=False)
    # 근처 친구 목록 반경 (km) — 사용자가 변경 가능, 기본 5km
    nearby_radius_km = models.FloatField(default=5.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - 위치 공유 {'ON' if self.share_location_on_walk else 'OFF'}"


class GreenAreaTile(models.Model):
    """OSM 숲·공원 영역 캐시 (약 5km 타일 단위로 한 번만 외부 조회)"""
    key = models.CharField(max_length=32, unique=True)
    polygons = models.JSONField(default=list)   # [[ [lng, lat], ... ], ...]
    is_ok = models.BooleanField(default=True)   # False = 조회 실패 (일정 시간 후 재시도)
    fetched_at = models.DateTimeField()

    def __str__(self):
        return f"Tile {self.key} ({len(self.polygons)} areas)"


class VisitedCell(models.Model):
    """사용자가 산책으로 지나간 약 200m 격자 칸 (새로운 지역 판정용)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='visited_cells'
    )
    cell_key = models.CharField(max_length=32)
    first_visited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'cell_key'], name='unique_user_visited_cell'),
        ]
