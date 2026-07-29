from rest_framework import generics, permissions, status
from rest_framework.response import Response
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