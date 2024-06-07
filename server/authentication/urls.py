from django.urls import path
from .views import UserRegistration, UserLogin, UserEmailVerification

urlpatterns = [
    path("register/", UserRegistration.as_view(), name="registeration"),
    path("verify-email/", UserEmailVerification.as_view(), name="email_verification"),
    path("login/", UserLogin.as_view(), name="login"),
]
