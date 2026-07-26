from rest_framework import serializers
from .models import WalkingSession, WalkingPath


class WalkingPathBatchSerializer(serializers.Serializer):
    """실시간 위치(GPS) 보낼 때 데이터 형식 검증"""
    latitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=12, decimal_places=8)


class WalkingSessionSerializer(serializers.ModelSerializer):
    """산책 세션 정보를 프론트엔드로 내보낼 때 규격 정리"""
    total_paused_seconds = serializers.ReadOnlyField(source='paused_time')
    paused_time_str = serializers.SerializerMethodField()
    total_duration_str = serializers.SerializerMethodField()

    class Meta:
        model = WalkingSession
        fields = [
            'id', 'user', 'pet', 'status', 'is_location_shared',
            'start_time', 'end_time', 'total_distance', 'total_duration',
            'total_paused_seconds', 'paused_time_str', 'total_duration_str'
        ]
        read_only_fields = ['id', 'user', 'start_time', 'end_time', 'total_distance', 'total_duration']

    def _format_seconds(self, total_seconds):
        """초(seconds)를 'X시간 Y분 Z초' 형식의 예쁜 문자열로 변환하는 내부 헬퍼 함수"""
        if not total_seconds:
            return "0초"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}시간")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}분")
        parts.append(f"{seconds}초")
        return " ".join(parts)

    def get_paused_time_str(self, obj):
        # 일시정지 누적 시간을 문자열로 변환
        return self._format_seconds(obj.paused_time)

    def get_total_duration_str(self, obj):
        # 순수 산책 시간을 계산해서 'X시간 Y분 Z초' 문자열로 변환
        return self._format_seconds(obj.get_pure_duration_seconds())