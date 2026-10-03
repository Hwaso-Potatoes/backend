import math
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from rest_framework import serializers
from .models import WalkingSession


class CoordinateField(serializers.FloatField):
    """
    GPS 좌표 필드: float/문자열 입력을 받아 소수점 8자리로 반올림한 Decimal로 변환.
    (DRF DecimalField는 자리수 초과 시 반올림 없이 에러를 내서 실제 GPS 값이 튕김)
    """
    def __init__(self, limit, **kwargs):
        kwargs.setdefault('min_value', -limit)
        kwargs.setdefault('max_value', limit)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            self.fail('invalid')
        return Decimal(str(round(value, 8)))


class FlexibleDateTimeField(serializers.DateTimeField):
    """ISO 8601 문자열 또는 epoch 숫자(초/밀리초)를 받는 시각 필드"""
    def to_internal_value(self, value):
        if isinstance(value, bool):
            self.fail('invalid', format='ISO 8601 또는 epoch(ms)')

        is_number = isinstance(value, (int, float)) or (
            isinstance(value, str) and value.strip().replace('.', '', 1).isdigit()
        )
        if is_number:
            ts = float(value)
            if ts > 1e11:          # 밀리초로 판단
                ts /= 1000
            try:
                return datetime.fromtimestamp(ts, tz=dt_timezone.utc)
            except (OverflowError, OSError, ValueError):
                self.fail('invalid', format='ISO 8601 또는 epoch(ms)')

        return super().to_internal_value(value)


class WalkingPathBatchSerializer(serializers.Serializer):
    """실시간 위치(GPS) 보낼 때 데이터 형식 검증"""
    latitude = CoordinateField(limit=90)
    longitude = CoordinateField(limit=180)
    recorded_at = FlexibleDateTimeField(required=False)


class WalkingSessionSerializer(serializers.ModelSerializer):
    """산책 세션 정보를 프론트엔드로 내보낼 때 규격 정리"""
    total_distance = serializers.SerializerMethodField()
    total_paused_seconds = serializers.ReadOnlyField(source='paused_time')
    paused_time_str = serializers.SerializerMethodField()
    total_duration_str = serializers.SerializerMethodField()

    class Meta:
        model = WalkingSession
        fields = [
            'id', 'user', 'pet', 'status', 'is_location_shared',
            'start_time', 'end_time', 'total_distance', 'total_duration',
            'total_paused_seconds', 'paused_time_str', 'total_duration_str',
            'is_forest_walk', 'is_city_walk', 'is_new_area',
        ]
        read_only_fields = [
            'id', 'user', 'start_time', 'end_time', 'total_duration',
            'is_forest_walk', 'is_city_walk', 'is_new_area',
        ]

    def _format_seconds(self, total_seconds):
        """초(seconds)를 'X시간 Y분 Z초' 형식 문자열로 변환"""
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

    def get_total_distance(self, obj):
        # 산책 중에도 소수점 2자리로 표시 (타입은 float 유지)
        return round(obj.total_distance, 2)

    def get_paused_time_str(self, obj):
        return self._format_seconds(obj.paused_time)

    def get_total_duration_str(self, obj):
        return self._format_seconds(obj.get_pure_duration_seconds())
