from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # 관리자 페이지
    path('admin/', admin.site.urls),

    # 앱 URL 연동 (팀원 유저 기능 + 내 산책 기능)
    path('api/users/', include('users.urls')),
    path('api/walks/', include('walk.urls')),

    # Swagger 문서 관련
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]