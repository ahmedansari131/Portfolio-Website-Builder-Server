from django.urls import path
from .views import UserRegistration, UserLogin, UserEmailVerification
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)


urlpatterns = [
    path("register/", UserRegistration.as_view(), name="registeration"),
    path("verify-email/", UserEmailVerification.as_view(), name="email_verification"),
    path("login/", UserLogin.as_view(), name="login"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
