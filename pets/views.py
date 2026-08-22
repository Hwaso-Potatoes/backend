from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pet
from .serializers import PetSerializer, PetGrowthSerializer

@extend_schema_view(
    get=extend_schema(summary="반려견 목록 조회", tags=["pets"]),
    post=extend_schema(summary="반려견 등록", tags=["pets"]),
)
class PetListCreateView(generics.ListCreateAPIView):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Pet.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"id": serializer.instance.id},   
                        status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(summary="반려견 상세 조회", tags=["pets"]),
    patch=extend_schema(summary="반려견 수정", responses={204: None}, tags=["pets"]),
    delete=extend_schema(summary="반려견 삭제", tags=["pets"]),
)
class PetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "pet_id"                               
    http_method_names = ["get", "patch", "delete", "head", "options"]  

    def get_queryset(self):
        return Pet.objects.filter(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        super().partial_update(request, *args, **kwargs)       
        return Response(status=status.HTTP_204_NO_CONTENT)    


class PetGrowthView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["반려견"],
        summary="반려견 성장 정보 조회",
        description=(
            "반려견의 현재 레벨, 경험치, 다음 레벨까지 필요한 "
            "경험치와 진행률을 조회합니다."
        ),
        responses={
            200: PetGrowthSerializer,
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(
                description="반려견을 찾을 수 없음",
            ),
        },
    )
    def get(self, request, pet_id):
        pet = get_object_or_404(
            Pet,
            pk=pet_id,
            user=request.user,
        )

        serializer = PetGrowthSerializer(pet)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )