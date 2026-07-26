from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from geopy.distance import geodesic

from .models import WalkingSession, WalkingPath
from .serializers import (
    WalkingSessionSerializer, 
    WalkingPathBatchSerializer
)


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

        user_pet = getattr(request.user, 'pet', None)

        session = WalkingSession.objects.create(
            user=request.user,
            pet=user_pet,
            status='WALKING',
            is_location_shared=False
        )
        
        serializer = WalkingSessionSerializer(session)
        return Response({
            "message": "산책이 시작되었습니다.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


# [2. 산책 일시정지 / 재개 및 설정 변경 API]
class WalkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    # GET 메서드 추가: 단순 산책 세션 정보 및 거리/시간 조회
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
        is_location_shared = request.data.get('is_location_shared')
        current_status = session.status
        
        if new_status is None and is_location_shared is None:
            return Response({"error": "수정할 데이터(status 또는 is_location_shared)를 제공해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        if is_location_shared is not None:
            session.is_location_shared = bool(is_location_shared)

        if new_status:
            if new_status not in ['WALKING', 'PAUSED']:
                return Response({"error": "올바르지 않은 상태 값입니다. (WALKING 또는 PAUSED만 가능)"}, status=status.HTTP_400_BAD_REQUEST)

            if new_status == current_status:
                return Response({"error": f"이미 현재 산책 상태가 '{current_status}' 입니다."}, status=status.HTTP_400_BAD_REQUEST)

            now = timezone.now()
            # WALKING -> PAUSED : 정지 시각 기록
            if new_status == 'PAUSED' and current_status == 'WALKING':
                session.last_paused_at = now

            # PAUSED -> WALKING : 정지 시간 누적 계산
            elif new_status == 'WALKING' and current_status == 'PAUSED':
                if session.last_paused_at:
                    paused_duration = (now - session.last_paused_at).total_seconds()
                    session.paused_time += int(paused_duration)
                    session.last_paused_at = None

            session.status = new_status

        session.save()
        
        # 시리얼라이저가 paused_time_str ("X시간 Y분 Z초") 등을 자동으로 변환
        serializer = WalkingSessionSerializer(session)

        return Response({
            "message": "산책 상태가 변경되었습니다.",
            "data": serializer.data
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

        # PAUSED 상태에서 종료 시 처리
        if session.status == 'PAUSED' and session.last_paused_at:
            paused_duration = (now - session.last_paused_at).total_seconds()
            session.paused_time += int(paused_duration)
            session.last_paused_at = None

        session.end_time = now
        session.status = 'FINISHED'
        session.is_location_shared = False

        # 모델 메서드를 호출해 순수 산책 시간을 초단위로 구한 뒤, '분' 단위 저장
        pure_seconds = session.get_pure_duration_seconds()
        session.total_duration = pure_seconds // 60
        
        # total_distance는 실시간 누적 방식 적용 (소수점 둘째 자리 정리)
        session.total_distance = round(session.total_distance, 2)
        session.save()

        # 응답 문자열 포맷팅
        serializer = WalkingSessionSerializer(session)
        return Response({
            "message": "산책이 성공적으로 종료되었습니다.",
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

        valid_locations = serializer.validated_data
        
        last_path = session.paths.order_by('-timestamp').first()
        last_coords = (float(last_path.latitude), float(last_path.longitude)) if last_path else None

        created_paths = []
        added_distance_km = 0.0

        for loc in valid_locations:
            current_coords = (float(loc['latitude']), float(loc['longitude']))

            if last_coords:
                dist_km = geodesic(last_coords, current_coords).km

                # GPS 튐 필터링 (100m 이상 거품 노이즈 제외)
                if dist_km > 0.1:  
                    continue 
                if dist_km >= 0.001:  # 1m 이상 이동 시 계산
                    added_distance_km += dist_km
                    last_coords = current_coords
            else:
                last_coords = current_coords

            created_paths.append(WalkingPath(
                session=session,
                latitude=loc['latitude'],
                longitude=loc['longitude']
            ))

        if created_paths:
            WalkingPath.objects.bulk_create(created_paths)

        if added_distance_km > 0:
            session.total_distance += added_distance_km
            session.save(update_fields=['total_distance'])

        return Response({
            "message": f"{len(created_paths)}개의 위치 정보가 추가되었습니다.",
            "current_total_distance_km": round(session.total_distance, 2)
        }, status=status.HTTP_201_CREATED)