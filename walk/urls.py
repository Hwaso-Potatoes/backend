from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.WalkStartView.as_view(), name='walk-start'),
    path('<int:walk_id>/', views.WalkStatusView.as_view(), name='walk-status'),
    path('<int:walk_id>/end/', views.WalkEndView.as_view(), name='walk-end'),
]