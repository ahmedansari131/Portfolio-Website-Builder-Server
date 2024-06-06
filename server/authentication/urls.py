from django.urls import path
from .views import AuthenticateUser

urlpatterns = [
    path("register/", AuthenticateUser.as_view(), name="registeration"),
    path("verify-email/", AuthenticateUser.as_view(), name="email_verification"),
]
