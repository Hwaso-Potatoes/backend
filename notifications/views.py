from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)

from .models import (
    DeviceToken,
    NotificationPreference,
)
from .serializers import (
    DeviceTokenRegisterSerializer,
    DeviceTokenUnregisterSerializer,
    NotificationPreferenceSerializer,
)


class NotificationPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["알림"],
        summary="알림 설정 조회",
        responses={
            200: NotificationPreferenceSerializer,
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def get(self, request):
        preference, _ = (
            NotificationPreference.objects
            .get_or_create(
                user=request.user,
            )
        )

        serializer = (
            NotificationPreferenceSerializer(
                preference
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["알림"],
        summary="알림 설정 변경",
        request=NotificationPreferenceSerializer,
        responses={
            200: NotificationPreferenceSerializer,
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def patch(self, request):
        preference, _ = (
            NotificationPreference.objects
            .get_or_create(
                user=request.user,
            )
        )

        serializer = (
            NotificationPreferenceSerializer(
                preference,
                data=request.data,
                partial=True,
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class DeviceTokenRegisterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["알림"],
        summary="푸시 알림 기기 등록",
        request=DeviceTokenRegisterSerializer,
        responses={
            200: OpenApiResponse(description="기기 등록 성공"),
        },
    )
    def post(self, request):
        serializer = (
            DeviceTokenRegisterSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        token = serializer.validated_data["token"]

        platform = serializer.validated_data.get("platform", "")

        device, _ = (
            DeviceToken.objects
            .update_or_create(
                token=token,
                defaults={
                    "user": request.user,
                    "platform": platform,
                    "is_active": True,
                },
            )
        )

        return Response(
            {
                "message": "기기가 등록되었습니다.",
                "device_id": device.id,
            },
            status=status.HTTP_200_OK,
        )


class DeviceTokenUnregisterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["알림"],
        summary="푸시 알림 기기 해제",
        request=DeviceTokenUnregisterSerializer,
        responses={
            200: OpenApiResponse(description="기기 해제 성공"),
        },
    )
    def post(self, request):
        serializer = (
            DeviceTokenUnregisterSerializer(
                data=request.data
            )
        )

        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        DeviceToken.objects.filter(
            user=request.user,
            token=token,
        ).update(
            is_active=False,
        )

        return Response(
            {
                "message": "기기가 해제되었습니다."
            },
            status=status.HTTP_200_OK,
        )