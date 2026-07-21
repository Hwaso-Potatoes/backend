from django.db import models
from django.conf import settings

class WalkingSession(models.Model):
    STATUS_CHOICES = [
        ('WALKING', '산책 중'),
        ('PAUSED', '일시 정지'),
        ('FINISHED', '산책 종료'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='walking_sessions', null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='WALKING')
    
    # 누적 계산되어 저장될 데이터들
    total_distance = models.FloatField(default=0.0)  # 단위: 미터(m)
    total_duration = models.IntegerField(default=0)  # 단위: 초(seconds)
    
    # ⏱️ 일시정지 누적 시간 필드 추가 (단위: 초)
    # 사용자가 일시정지를 누르고 다시 시작할 때마다 멈춰있던 시간을 여기에 계속 더해줄 겁니다.
    paused_time = models.IntegerField(default=0)
    
    # 실시간 위치 공유 여부 토글
    is_location_shared = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email}의 산책 ({self.start_time.strftime('%Y-%m-%d')})"

class WalkingPath(models.Model):
    session = models.ForeignKey(WalkingSession, on_delete=models.CASCADE, related_name='paths')
    latitude = models.FloatField()   # 위도
    longitude = models.FloatField()  # 경도
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']  # 시간순 정렬