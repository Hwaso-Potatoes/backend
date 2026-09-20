from django.urls import path

from .views import (
    DetailView,
    EmailChangeVerifyView,
    EmailChangeView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetView,
    RefreshView,
    RegisterEmailRequestView,
    RegisterEmailVerifyView,
    RegisterView,
    SocialLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("register/email/request/", RegisterEmailRequestView.as_view(), name="register-email-request"),
    path("register/email/verify/", RegisterEmailVerifyView.as_view(), name="register-email-verify"),

    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("social/<str:provider>/", SocialLoginView.as_view(), name="social-login"),

    path("<int:user_id>/", DetailView.as_view(), name="detail"),

    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("email/change/", EmailChangeView.as_view(), name="email-change"),
    path("email/change/verify/", EmailChangeVerifyView.as_view(), name="email-change-verify"),
]