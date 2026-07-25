from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Pet
from .serializers import PetSerializer


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


@extend_schema_view(
    get=extend_schema(summary="반려견 상세 조회", tags=["pets"]),
    put=extend_schema(summary="반려견 수정(전체)", tags=["pets"]),
    patch=extend_schema(summary="반려견 수정(부분)", tags=["pets"]),
    delete=extend_schema(summary="반려견 삭제", tags=["pets"]),
)
class PetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Pet.objects.filter(user=self.request.user)