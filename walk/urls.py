from django.urls import path
from .views import (
    WalkStartView,
    WalkStatusView,
    WalkLocationShareView,
    WalkEndView,
    WalkPathCreateView,
    LocationShareSettingView,
)

urlpatterns = [
    path('start/', WalkStartView.as_view(), name='walk-start'),
    path('settings/location-share/', LocationShareSettingView.as_view(), name='walk-location-share-setting'),
    path('<int:walk_id>/', WalkStatusView.as_view(), name='walk-status'),
    path('<int:walk_id>/location-share/', WalkLocationShareView.as_view(), name='walk-location-share'),
    path('<int:walk_id>/end/', WalkEndView.as_view(), name='walk-end'),
    path('<int:walk_id>/locations/', WalkPathCreateView.as_view(), name='walk-locations'),
]
