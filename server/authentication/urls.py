from django.urls import path
from .views import AuthenticateUser

urlpatterns = [
    path("register/", AuthenticateUser.as_view(), name="registeration"),
]
