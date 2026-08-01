from django.urls import path
from .views import (
    WalkStartView,
    WalkStatusView,
    WalkEndView,
    WalkPathCreateView,
)

urlpatterns = [
    path('start/', WalkStartView.as_view(), name='walk-start'),
    path('<int:walk_id>/', WalkStatusView.as_view(), name='walk-status'),
    path('<int:walk_id>/end/', WalkEndView.as_view(), name='walk-end'),
    path('<int:walk_id>/locations/', WalkPathCreateView.as_view(), name='walk-locations'),
]