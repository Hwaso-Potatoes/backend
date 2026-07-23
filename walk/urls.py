from django.urls import path
from . import views

urlpatterns = [
    path('', views.WalkStartView.as_view(), name='walk-start'), # api/walks/
    path('<int:walk_id>/', views.WalkEndView.as_view(), name='walk-end'), # api/walks/:walk_id/
    path('<int:walk_id>/status/', views.WalkStatusView.as_view(), name='walk-status'), # api/walks/:walk_id/status/
]