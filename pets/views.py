from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from .models import Dog
from .serializers import DogSerializer


class DogViewSet(viewsets.ModelViewSet):
    serializer_class = DogSerializer
    permission_classes = [permissions.IsAuthenticated]  

    def get_queryset(self):
        return Dog.objects.filter(owner=self.request.user)  

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)   