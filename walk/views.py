from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import WalkingSession, WalkingPath
from geopy.distance import geodesic 

# [산책 시작] API
class WalkStartView(APIView):
    def post(self, request):
        
        session = WalkingSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            start_time=timezone.now(),
            status='WALKING',
            is_location_shared=True
        )
        
        return Response({
            "message": "산책이 시작되었습니다.",
            "walk_id": session.id,
            "status": session.status
        }, status=status.HTTP_201_CREATED)


# [산책 종료] + [거리 및 시간 계산] API
class WalkEndView(APIView):
    def post(self, request, walk_id):
        try:
            session = WalkingSession.objects.get(id=walk_id)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않는 산책 세션입니다."}, status=status.HTTP_404_NOT_FOUND)
        
        if session.status == 'FINISHED':
            return Response({"error": "이미 종료된 산책입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 최종 종료 시간 기록
        session.end_time = timezone.now()
        session.status = 'FINISHED'

        # [산책 시간 계산] (총 소요 시간 - 일시정지 누적 시간)
        total_delta = session.end_time - session.start_time
        total_seconds = total_delta.total_seconds()
        
        # 일시정지 누적 시간(paused_time) 차감
        if session.paused_time:
            total_seconds -= session.paused_time()
            
        session.total_duration = max(0, int(total_seconds // 60))

        # [산책 거리 계산]
        paths = WalkingPath.objects.filter(session=session).order_by('timestamp')
        total_distance_km = 0.0
        
        if paths.count() > 1:
            for i in range(len(paths) - 1):
                point1 = (paths[i].latitude, paths[i].longitude)
                point2 = (paths[i+1].latitude, paths[i+1].longitude)
                total_distance_km += geodesic(point1, point2).km
        
        session.total_distance = round(total_distance_km, 2)
        session.save()

        return Response({
            "message": "산책이 종료되었습니다.",
            "walk_id": session.id,
            "total_distance_km": session.total_distance,
            "total_duration_minutes": session.total_duration
        }, status=status.HTTP_200_OK)


# [산책 중 상태 관리] API (일시정지 / 재개)
class WalkStatusView(APIView):
    def patch(self, request, walk_id):
        try:
            session = WalkingSession.objects.get(id=walk_id)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않는 산책 세션입니다."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')  # 프론트엔드가 'PAUSED' 또는 'WALKING'을 보냄
        
        if new_status not in ['WALKING', 'PAUSED']:
            return Response({"error": "올바르지 않은 상태 값입니다."}, status=status.HTTP_400_BAD_REQUEST)

        session.status = new_status
        session.save()

        return Response({
            "message": f"산책 상태가 {new_status}(으)로 변경되었습니다.",
            "walk_id": session.id,
            "status": session.status
        }, status=status.HTTP_200_OK)


# [현재 위치 저장] API (HTTP POST 방식)
class LocationSaveView(APIView):
    def post(self, request, walk_id):
        try:
            session = WalkingSession.objects.get(id=walk_id)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않는 산책 세션입니다."}, status=status.HTTP_404_NOT_FOUND)

        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude or not longitude:
            return Response({"error": "위도(latitude)와 경도(longitude)를 모두 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 위치 공유 ON 상태일 때만 경로 데이터 적재
        if session.is_location_shared:
            WalkingPath.objects.create(
                session=session,
                latitude=latitude,
                longitude=longitude
            )
            return Response({"message": "위치 경로가 성공적으로 저장되었습니다."}, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "위치 공유가 꺼져 있어 저장되지 않았습니다."}, status=status.HTTP_200_OK)