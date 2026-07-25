from django.db import models
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
        related_name='walking_sessions', 
        null=True, 
        blank=True
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
    
    # 실시간 위치 공유 여부
    is_location_shared = models.BooleanField(default=True)

    def __str__(self):
        user_info = self.user.email if self.user else "비회원"
        return f"{user_info}의 산책 ({self.start_time.strftime('%Y-%m-%d %H:%M')})"


class WalkingPath(models.Model):
    session = models.ForeignKey(
        WalkingSession, 
        on_delete=models.CASCADE, 
        related_name='paths'
    )
    latitude = models.FloatField()   # 위도
    longitude = models.FloatField()  # 경도
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']  # 경로 좌표 시간순 정렬

    def __str__(self):
        return f"Session {self.session_id} - [{self.latitude}, {self.longitude}]"