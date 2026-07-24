from django.urls import path
from .views import RegisterView, LoginView, LogoutView, RefreshView, DetailView, PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),         
    path("token/refresh/", RefreshView.as_view(), name="refresh"), 
    path("logout/", LogoutView.as_view(), name="logout"),
    path("<int:pk>/", DetailView.as_view(), name="detail"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]