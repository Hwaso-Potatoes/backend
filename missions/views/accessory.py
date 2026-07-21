from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from missions.models import PetAccessory
from missions.serializers.accessory import AccessoryEquipResultSerializer, AccessoryEquipSerializer, AccessoryListSerializer
from pets.models import Pet


class AccessoryListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["액세서리"],
        summary="반려견 액세서리 목록 조회",
        description="해당 반려견이 보유한 액세서리 목록을 조회합니다.",
        responses={
            200: AccessoryListSerializer(many=True),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="반려견을 찾을 수 없음"),
        },
    )
    def get(self, request, pet_id):
        pet = get_object_or_404(
            Pet,
            pk=pet_id,
            user=request.user,
        )

        pet_accessories = (
            PetAccessory.objects
            .filter(pet=pet)
            .select_related("accessory")
            .order_by("-is_equipped", "-acquired_at")
        )

        serializer = AccessoryListSerializer(
            pet_accessories,
            many=True,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AccessoryDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["액세서리"],
        summary="반려견 액세서리 착용 상태 변경",
        description=(
            "반려견이 보유한 액세서리를 착용하거나 해제합니다. "
            "is_equipped가 true이면 기존에 착용 중인 액세서리는 "
            "자동으로 해제됩니다."
        ),
        request=AccessoryEquipSerializer,
        responses={
            200: AccessoryEquipResultSerializer,
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="반려견 또는 보유 액세서리를 찾을 수 없음"),
        },
    )
    def patch(self, request, pet_id, accessory_id):
        request_serializer = AccessoryEquipSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        is_equipped = request_serializer.validated_data[
            "is_equipped"
        ]

        with transaction.atomic():
            pet = get_object_or_404(
                Pet,
                pk=pet_id,
                user=request.user,
            )

            pet_accessory = get_object_or_404(
                PetAccessory.objects
                .select_for_update()
                .select_related("accessory"),
                pet=pet,
                accessory_id=accessory_id,
            )

            if is_equipped:
                PetAccessory.objects.filter(
                    pet=pet,
                    is_equipped=True,
                ).exclude(
                    pk=pet_accessory.pk,
                ).update(
                    is_equipped=False,
                )

            if pet_accessory.is_equipped != is_equipped:
                pet_accessory.is_equipped = is_equipped
                pet_accessory.save(
                    update_fields=["is_equipped"],
                )

        response_serializer = AccessoryEquipResultSerializer(
            pet_accessory,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )