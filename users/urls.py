from django.urls import path

from .views import (
    RegisterView, LoginView, LogoutView, RefreshView, DetailView,
    PasswordResetView, EmailChangeView, EmailChangeVerifyView, SocialLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("social/<str:provider>/", SocialLoginView.as_view(), name="social-login"),
    path("<int:user_id>/", DetailView.as_view(), name="detail"),
    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path("email/change/", EmailChangeView.as_view(), name="email-change"),
    path("email/change/verify/", EmailChangeVerifyView.as_view(), name="email-change-verify"),
]