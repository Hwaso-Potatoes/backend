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
    
    # 실시간 위치 공유 여부
    is_location_shared = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            # 유저의 진행 중/최근 산책 조회 최적화
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-start_time']),
        ]

    def __str__(self):
        pet_name = self.pet.name if self.pet else "반려견 미지정"
        user_info = getattr(self.user, 'email', str(self.user))
        return f"{pet_name}(보호자: {user_info})의 산책 ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

    def get_pure_duration_seconds(self):
        """총 소요 시간 중 일시정지 시간을 뺀 '순수 산책 시간(초)'을 계산해주는 헬퍼 메서드"""
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

    # float 오차 방지를 위해 DecimalField 적용 (소수점 8자리 = 1mm 수준 정밀도)
    latitude = models.DecimalField(max_digits=11, decimal_places=8)
    longitude = models.DecimalField(max_digits=12, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True)
   
    class Meta:
        ordering = ['timestamp']
        indexes = [
            # 특정 산책 세션의 좌표를 시간 순서대로 빠르게 불러오는 인덱스
            models.Index(fields=['session', 'timestamp']),
        ]

    def __str__(self):
        return f"Session {self.session_id} - [{self.latitude}, {self.longitude}]"