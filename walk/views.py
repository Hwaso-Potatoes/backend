from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import WalkingSession, WalkingPath
from geopy.distance import geodesic
from rest_framework.permissions import IsAuthenticated

# [1. 산책 시작 API]
class WalkStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 이미 진행 중인 산책(WALKING 또는 PAUSED)이 있는지 확인
        active_session = WalkingSession.objects.filter(
            user=request.user, 
            status__in=['WALKING', 'PAUSED']
        ).first()

        if active_session:
            return Response({
                "error": "이미 진행 중인 산책 세션이 존재합니다.",
                "walk_id": active_session.id,
                "status": active_session.status
            }, status=status.HTTP_400_BAD_REQUEST)

        session = WalkingSession.objects.create(
            user=request.user,
            start_time=timezone.now(),
            status='WALKING',
            is_location_shared=True
        )
        
        return Response({
            "message": "산책이 시작되었습니다.",
            "walk_id": session.id,
            "status": session.status
        }, status=status.HTTP_201_CREATED)


# [2. 산책 일시정지 / 재개 및 설정 변경 API]
class WalkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, walk_id):
        try:
            session = WalkingSession.objects.get(id=walk_id, user=request.user)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않거나 본인의 산책 세션이 아닙니다."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        is_location_shared = request.data.get('is_location_shared')
        current_status = session.status
        
        # 유효성 검사: 둘 다 넘어오지 않은 경우
        if new_status is None and is_location_shared is None:
            return Response({"error": "수정할 데이터(status 또는 is_location_shared)를 제공해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 위치 공유 여부 온오프 토글 처리
        if is_location_shared is not None:
            session.is_location_shared = bool(is_location_shared)

        # 2. 산책 상태 변경 요청이 들어온 경우
        if new_status:
            if new_status not in ['WALKING', 'PAUSED']:
                return Response({"error": "올바르지 않은 상태 값입니다."}, status=status.HTTP_400_BAD_REQUEST)

            # 1) WALKING -> PAUSED : 정지 시각 기록
            if new_status == 'PAUSED' and current_status != 'PAUSED':
                session.last_paused_at = timezone.now()

            # 2) PAUSED -> WALKING : 정지 시간 계산 후 paused_time에 누적
            elif new_status == 'WALKING' and current_status == 'PAUSED':
                if session.last_paused_at:
                    paused_duration = (timezone.now() - session.last_paused_at).total_seconds()
                    session.paused_time += int(paused_duration)
                    session.last_paused_at = None

            session.status = new_status

        session.save()

        # paused_time(초 단위)을 "X시간 Y분 Z초" 문자열로 변환
        total_paused_seconds = session.paused_time
        hours = total_paused_seconds // 3600
        minutes = (total_paused_seconds % 3600) // 60
        seconds = total_paused_seconds % 60

        paused_parts = []
        if hours > 0:
            paused_parts.append(f"{hours}시간")
        if minutes > 0 or hours > 0:
            paused_parts.append(f"{minutes}분")
        paused_parts.append(f"{seconds}초")

        paused_time_str = " ".join(paused_parts)

        return Response({
            "message": "산책 상태가 변경되었습니다.",
            "walk_id": session.id,
            "status": session.status,
            "paused_time": session.paused_time,
            "paused_time_str": paused_time_str,
            "is_location_shared": session.is_location_shared
        }, status=status.HTTP_200_OK)


# [3. 산책 종료 API]
class WalkEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, walk_id):
        try:
            session = WalkingSession.objects.get(id=walk_id, user=request.user)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않거나 본인의 산책 세션이 아닙니다."}, status=status.HTTP_404_NOT_FOUND)
        
        if session.status == 'FINISHED':
            return Response({"error": "이미 종료된 산책입니다."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        # PAUSED 상태에서 바로 종료 시, 마지막 정지 시간 처리
        if session.status == 'PAUSED' and session.last_paused_at:
            paused_duration = (now - session.last_paused_at).total_seconds()
            session.paused_time += int(paused_duration)
            session.last_paused_at = None

        # 최종 종료 시간 및 상태 업데이트
        session.end_time = now
        session.status = 'FINISHED'

        # 1) 순수 산책 시간 계산 (총 소요 시간 - 일시정지 누적 시간)
        total_delta = session.end_time - session.start_time
        total_seconds = int(total_delta.total_seconds())
        
        if session.paused_time:
            total_seconds -= session.paused_time
            
        total_seconds = max(0, total_seconds)

        # DB 저장용 (분 단위)
        session.total_duration = total_seconds // 60

        # 응답용 "X시간 Y분 Z초" 문자열 생성
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        duration_parts = []
        if hours > 0:
            duration_parts.append(f"{hours}시간")
        if minutes > 0 or hours > 0:
            duration_parts.append(f"{minutes}분")
        duration_parts.append(f"{seconds}초")

        total_duration_str = " ".join(duration_parts)

        # 2) 이동 거리 계산 (메모리 최적화: values_list 활용)
        path_coords = list(
            WalkingPath.objects.filter(session=session)
            .order_by('timestamp')
            .values_list('latitude', 'longitude')
        )
        
        total_distance_km = 0.0
        if len(path_coords) > 1:
            for i in range(len(path_coords) - 1):
                total_distance_km += geodesic(path_coords[i], path_coords[i+1]).km
        
        session.total_distance = round(total_distance_km, 2)
        session.save()

        return Response({
            "message": "산책이 성공적으로 종료되었습니다.",
            "walk_id": session.id,
            "total_distance_km": session.total_distance,
            "total_duration_str": total_duration_str
        }, status=status.HTTP_200_OK)