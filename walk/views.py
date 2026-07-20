from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_400  # 혹은 get_object_or_404
from .models import WalkingSession, WalkingPath
from geopy.distance import geodesic  # 거리 계산을 위한 라이브러리 (필요 시 설치)

# 1. [산책 시작] API
class WalkStartView(APIView):
    def post(self, request):
        # 새로운 산책 세션을 생성합니다. (상태는 자동으로 WALKING)
        # user 정보는 프로젝트의 인증 방식(기본 유저 혹은 팀원의 커스텀 유저)에 맞춰 연동됩니다.
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


# 2. [산책 종료] + [거리 및 시간 계산] API
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

        # ⏱️ [산책 시간 계산] (총 소요 시간 - 일시정지 누적 시간)
        total_delta = session.end_time - session.start_time
        total_seconds = total_delta.total_seconds()
        
        # 일시정지 누적 시간(paused_time)이 있다면 초 단위로 빼줍니다.
        if session.paused_time:
            total_seconds -= session.paused_time.total_seconds()
            
        # 음수가 되지 않도록 방어 코드 추가 후 분(Minute) 단위로 저장 (필요에 따라 초 단위 변경 가능)
        session.total_duration = max(0, int(total_seconds // 60))

        # 📐 [산책 거리 계산] (그동안 쌓인 WalkingPath 좌표들 사이의 직선거리 누적합)
        paths = WalkingPath.objects.filter(session=session).order_by('timestamp')
        total_distance_km = 0.0
        
        if paths.count() > 1:
            for i in range(len(paths) - 1):
                point1 = (paths[i].latitude, paths[i].longitude)
                point2 = (paths[i+1].latitude, paths[i+1].longitude)
                # geopy 라이브러리를 이용해 두 좌표 사이의 거리를 계산 (km 단위)
                total_distance_km += geodesic(point1, point2).km
        
        session.total_distance = round(total_distance_km, 2)  # 소수점 둘째 자리까지 저장
        session.save()

        return Response({
            "message": "산책이 종료되었습니다.",
            "walk_id": session.id,
            "total_distance_km": session.total_distance,
            "total_duration_minutes": session.total_duration
        }, status=status.HTTP_200_OK)


# 3. [산책 중 상태 관리] API (일시정지 / 재개)
class WalkStatusView(APIView):
    def patch(self, request, walk_id):
        try:
            session = WalkingSession.objects.get(id=walk_id)
        except WalkingSession.DoesNotExist:
            return Response({"error": "존재하지 않는 산책 세션입니다."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')  # 프론트엔드가 'PAUSED' 또는 'WALKING'을 보냄
        
        if new_status not in ['WALKING', 'PAUSED']:
            return Response({"error": "올바르지 않은 상태 값입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 상태가 일시정지로 바뀔 때와 다시 시작될 때의 유기적인 처리 로직을 여기에 확장할 수 있습니다.
        session.status = new_status
        session.save()

        return Response({
            "message": f"산책 상태가 {new_status}(으)로 변경되었습니다.",
            "walk_id": session.id,
            "status": session.status
        }, status=status.HTTP_200_OK)


# 4. [현재 위치 저장] API (HTTP POST 방식)
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