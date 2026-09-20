from .auth import (
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
    SocialLoginView,
)

from .email import (
    EmailChangeVerifyView,
    EmailChangeView,
    RegisterEmailRequestView,
    RegisterEmailVerifyView,
)

from .password import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetView,
)

from .profile import DetailView