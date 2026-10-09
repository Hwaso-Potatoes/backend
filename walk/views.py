from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction

from walk.geo import classify_walk

from .models import WalkingSession, WalkPreference
from .serializers import (
    WalkingSessionSerializer,
    WalkingPathBatchSerializer
)
from .services import calculate_walk_experience, append_locations, get_last_path
from .realtime import broadcast_location, broadcast_location_hidden
from .signals import send_walk_finished

from pets.services import add_experience
from missions.services.mission import update_walk_missions
from missions.services.badge import check_level_badges, check_walk_badges


# ─────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────

def parse_bool(value):
    """JSON true/false, 문자열 'true'/'false', 1/0 모두 처리. 해석 불가면 None"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ('true', '1', 'on', 'yes'):
            return True
        if v in ('false', '0', 'off', 'no'):
            return False
    return None


def get_default_share_setting(user):
    pref = WalkPreference.objects.filter(user=user).only('share_location_on_walk').first()
    return pref.share_location_on_walk if pref else False


def sync_user_share_setting(user, value):
    WalkPreference.objects.update_or_create(
        user=user,
        defaults={'share_location_on_walk': value}
    )


def apply_location_share(session, value, user):
    """
    세션의 위치 공유 상태를 변경하고 필요한 브로드캐스트를 예약.
    session.save()는 호출하지 않음 (호출부에서 저장).
    반환값: 실제로 값이 바뀌었는지 여부
    """
    if session.is_location_shared == value:
        return False

    session.is_location_shared = value
    sync_user_share_setting(user, value)

    if value:
        # 켜는 순간 마지막 좌표를 바로 보내서 친구 지도에 즉시 표시
        last_path = get_last_path(session)
        if last_path:
            broadcast_location(session, last_path.latitude, last_path.longitude)
    else:
        broadcast_location_hidden(session, reason='sharing_off')

    return True


# [1. 산책 시작 API]
class WalkStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        active_session = WalkingSession.objects.filter(
            user=request.user,
            status__in=['WALKING', 'PAUSED']
        ).first()

        if active_session:
            return Response({
                "error": "이미 진행 중인 산책 세션이 존재합니다. 기존 산책을 종료한 후 시작해주세요.",
                "walk_id": active_session.id,
                "status": active_session.status
            }, status=status.HTTP_400_BAD_REQUEST)

        user_pet = request.user.pets.first()

        session = WalkingSession.objects.create(
            user=request.user,
            pet=user_pet,
            status='WALKING',
            # 설정 화면의 "산책 시 위치 공유" 값을 기본값으로 사용
            is_location_shared=get_default_share_setting(request.user)
        )
        # 시작 시점엔 좌표가 없으므로 브로드캐스트 없음 (첫 위치 저장 때 전송됨)

        serializer = WalkingSessionSerializer(session)
        return Response({
            "message": "산책이 시작되었습니다.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


# [2. 산책 일시정지 / 재개 및 설정 변경 API]
class WalkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, walk_id):
        try:
            session = WalkingSession.objects.get(id=walk_id, user=request.user)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않거나 본인의 산책 세션이 아닙니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WalkingSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def patch(self, request, walk_id):
        try:
            session = WalkingSession.objects.select_for_update().get(id=walk_id, user=request.user)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않거나 본인의 산책 세션이 아닙니다."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'FINISHED':
            return Response({"error": "이미 종료된 산책 세션은 상태를 변경할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status')
        raw_shared = request.data.get('is_location_shared')
        current_status = session.status

        if new_status is None and raw_shared is None:
            return Response({"error": "수정할 데이터(status 또는 is_location_shared)를 제공해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 1) 입력 검증을 먼저 전부 끝낸 뒤 변경 적용
        is_location_shared = None
        if raw_shared is not None:
            is_location_shared = parse_bool(raw_shared)
            if is_location_shared is None:
                return Response({"error": "is_location_shared는 true/false 값이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        status_changed = False
        if new_status:
            if new_status not in ['WALKING', 'PAUSED']:
                return Response({"error": "올바르지 않은 상태 값입니다. (WALKING 또는 PAUSED만 가능)"}, status=status.HTTP_400_BAD_REQUEST)

            if new_status == current_status:
                # 상태만 보냈는데 동일하면 에러, 위치 공유와 함께 보냈으면 상태는 무시
                if is_location_shared is None:
                    return Response({"error": f"이미 현재 산책 상태가 '{current_status}' 입니다."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                status_changed = True

        # 2) 상태 변경
        if status_changed:
            now = timezone.now()
            if new_status == 'PAUSED' and current_status == 'WALKING':
                session.last_paused_at = now
            elif new_status == 'WALKING' and current_status == 'PAUSED':
                if session.last_paused_at:
                    paused_duration = (now - session.last_paused_at).total_seconds()
                    session.paused_time += int(paused_duration)
                    session.last_paused_at = None
            session.status = new_status

        # 3) 위치 공유 변경 (하위 호환용 — 신규 프론트는 location-share/ 사용 권장)
        if is_location_shared is not None:
            apply_location_share(session, is_location_shared, request.user)

        session.save()

        serializer = WalkingSessionSerializer(session)
        return Response({
            "message": "산책 상태가 변경되었습니다.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# [2-1. 산책 중 위치 공유 On/Off API] — 산책 중 화면 토글 전용
class WalkLocationShareView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, walk_id):
        try:
            session = WalkingSession.objects.select_for_update().get(id=walk_id, user=request.user)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않거나 본인의 산책 세션이 아닙니다."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'FINISHED':
            return Response({"error": "이미 종료된 산책은 위치 공유를 변경할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        value = parse_bool(request.data.get('is_location_shared'))
        if value is None:
            return Response({"error": "is_location_shared(true/false)를 제공해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        changed = apply_location_share(session, value, request.user)
        if changed:
            session.save(update_fields=['is_location_shared'])

        return Response({
            "message": "위치 공유가 켜졌습니다." if value else "위치 공유가 꺼졌습니다.",
            "data": {
                "walk_id": session.id,
                "is_location_shared": session.is_location_shared,
                "changed": changed,
            }
        }, status=status.HTTP_200_OK)


# [3. 산책 종료 API]
class WalkEndView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, walk_id):
        try:
            session = WalkingSession.objects.select_for_update().get(id=walk_id, user=request.user)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않거나 본인의 산책 세션이 아닙니다."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'FINISHED':
            return Response({"error": "이미 종료된 산책입니다."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        if session.status == 'PAUSED' and session.last_paused_at:
            paused_duration = (now - session.last_paused_at).total_seconds()
            session.paused_time += int(paused_duration)
            session.last_paused_at = None

        was_shared = session.is_location_shared

        session.end_time = now
        session.status = 'FINISHED'
        session.is_location_shared = False

        pure_seconds = session.get_pure_duration_seconds()
        session.total_duration = pure_seconds // 60
        session.total_distance = round(session.total_distance, 2)
        session.save()

        # 공유 중이었다면 친구 지도에서 마커 제거
        # (종료 자체는 설정 변경이 아니므로 사용자 설정은 건드리지 않음)
        if was_shared:
            broadcast_location_hidden(session, reason='walk_ended')

        # 오늘 첫 산책인지 (출석 처리용)
        walk_date = timezone.localdate(now)
        is_first_walk_today = not WalkingSession.objects.filter(
            user=request.user,
            status='FINISHED',
            end_time__date=walk_date,
        ).exclude(id=session.id).exists()

        earned_experience = calculate_walk_experience(session.total_distance)

        # 숲 / 도시 / 새로운 지역 판정을 먼저 완료
        classify_walk(session.id)

        session.refresh_from_db(
            fields=[
                'is_forest_walk',
                'is_city_walk',
                'is_new_area',
                'classified_at',
            ]
        )

        acquired_badges = []

        if session.pet:
            pet = add_experience(
                pet=session.pet,
                amount=earned_experience,
            )

            level_badges = check_level_badges(
                pet
            ) or []

            walk_badges = check_walk_badges(
                pet=pet,
                session=session,
            ) or []

            acquired_badges.extend(level_badges)
            acquired_badges.extend(walk_badges)

        acquired_badge_data = [
            {
                "id": pet_badge.badge.id,
                "name": pet_badge.badge.name,
                "description": pet_badge.badge.description,
                "acquired_at": pet_badge.acquired_at,
            }
            for pet_badge in acquired_badges
        ]

        update_walk_missions(session)

        # 산책 종료 신호 발송 (출석 처리 등) — DB 커밋 후 실행
        transaction.on_commit(
            lambda: send_walk_finished(
                session,
                is_first_walk_today
            )
        )

        serializer = WalkingSessionSerializer(session)
        return Response({
            "message": "산책이 성공적으로 종료되었습니다.",
            "earned_experience": earned_experience,
            "is_first_walk_today": is_first_walk_today,
            "acquired_badges": acquired_badge_data,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# [4. 실시간 위치 경로(GPS) 저장 API]
class WalkPathCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, walk_id):
        try:
            session = WalkingSession.objects.select_for_update().get(id=walk_id, user=request.user)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않거나 본인의 산책 세션이 아닙니다."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'FINISHED':
            return Response({"error": "이미 종료된 산책에는 위치를 기록할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
        if session.status == 'PAUSED':
            return Response({"error": "일시정지 상태에서는 위치를 기록할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        data_list = request.data if isinstance(request.data, list) else [request.data]
        serializer = WalkingPathBatchSerializer(data=data_list, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        created_paths = append_locations(session, serializer.validated_data)

        # 공유 On일 때만 최신 좌표를 친구들에게 전송 (Off여도 경로 저장/거리 계산은 계속)
        if session.is_location_shared and created_paths:
            latest = created_paths[-1]
            broadcast_location(session, latest.latitude, latest.longitude)

        return Response({
            "message": f"{len(created_paths)}개의 위치 정보가 추가되었습니다.",
            "current_total_distance_km": round(session.total_distance, 2),
            "is_location_shared": session.is_location_shared,
        }, status=status.HTTP_201_CREATED)


# [5. 위치 공유 설정 API] — 알림설정 화면의 '산책 시 위치 공유' 토글
class LocationShareSettingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "share_location_on_walk": get_default_share_setting(request.user)
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def patch(self, request):
        value = parse_bool(request.data.get('share_location_on_walk'))
        if value is None:
            return Response({"error": "share_location_on_walk(true/false)를 제공해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        active_session = WalkingSession.objects.select_for_update().filter(
            user=request.user,
            status__in=['WALKING', 'PAUSED']
        ).first()

        if active_session and apply_location_share(active_session, value, request.user):
            # 산책 중이면 세션에도 반영 + 친구 브로드캐스트 (설정 저장은 내부에서 처리)
            active_session.save(update_fields=['is_location_shared'])
        else:
            sync_user_share_setting(request.user, value)

        return Response({
            "message": "위치 공유 설정이 변경되었습니다.",
            "share_location_on_walk": value,
            "applied_to_active_walk": active_session.id if active_session else None,
        }, status=status.HTTP_200_OK)
