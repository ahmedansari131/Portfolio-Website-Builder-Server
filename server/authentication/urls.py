from django.urls import path
from .views import (
    UserRegistration,
    UserLogin,
    UserEmailVerification,
    ResetPassword,
    ForgotPasswordRequest,
    UserProfile,
    UserSignout,
    CheckUsernameAvailability,
    ForgotPasswordConfirmation,
    DirectSignin,
    VerifyValidForgotPasswordRequest,
    GoogleOAuthView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    path("register/", UserRegistration.as_view(), name="registeration"),
    path("verify-email/", UserEmailVerification.as_view(), name="email_verification"),
    path("login/", UserLogin.as_view(), name="login"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("reset-password/", ResetPassword.as_view(), name="reset_password"),
    path("forgot-password/", ForgotPasswordRequest.as_view(), name="forgot_password"),
    path(
        "forgot-password-confirmation/<uid>/<token>/",
        ForgotPasswordConfirmation.as_view(),
        name="forgot_password_confirmation",
    ),
    path(
        "verify-valid-forgot-password-request/<uid>/<token>/",
        VerifyValidForgotPasswordRequest.as_view(),
        name="verify_valid_forgot_password_request",
    ),
    path(
        "direct-signin/<uid>/<signin_token>/",
        DirectSignin.as_view(),
        name="direct_signin",
    ),
    path("change-password/", ForgotPasswordRequest.as_view(), name="change_password"),
    path("user/", UserProfile.as_view(), name="user_identity"),
    path("signout/", UserSignout.as_view(), name="signout"),
    path(
        "check-username-availability/",
        CheckUsernameAvailability.as_view(),
        name="check_username",
    ),
    path('google/', GoogleOAuthView.as_view(), name='google_auth'),
]
