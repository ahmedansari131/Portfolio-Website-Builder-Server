import jwt
from django.utils import timezone
from datetime import timedelta
import os
from .models import User
from .serializers import MyTokenObtainPairSerializer
from django.http.response import JsonResponse
from django.conf import settings
from .constants import CHANGE_FORGOT_PASSWORD, DIRECT_LOGIN
from rest_framework_simplejwt.tokens import RefreshToken


class Token:

    def __init__(self, user_id=None, token_type=None):
        self.user_id = user_id
        self.token_type = token_type

    def generate_token(self):
        if not self.user_id:
            return "User id not found"

        expiration_time = timezone.now() + timedelta(
            minutes=int(os.environ.get("VERIFICATION_TIME_LIMIT"))
        )

        try:
            data = {
                "id": self.user_id,
                "exp": expiration_time,
                "token_type": self.token_type,
            }
            encoded_token = jwt.encode(
                data,
                os.environ.get("VERIFICATION_EMAIL_SECRET"),
                algorithm="HS256",
            )
            return encoded_token
        except Exception as error:
            return "Error occurred on server while generating verification token"

    def verify_token(self, token):
        try:
            decoded_token = jwt.decode(
                token, os.environ.get("VERIFICATION_EMAIL_SECRET"), algorithms="HS256"
            )
            user = User.objects.filter(id=decoded_token.get("id")).first()

            if user and user.is_active:
                if (
                    self.token_type == DIRECT_LOGIN
                    or self.token_type == CHANGE_FORGOT_PASSWORD
                ):
                    return decoded_token
                return (
                    f"{user.username}'s is already has an active account and can login."
                )
            return decoded_token
        except jwt.ExpiredSignatureError:
            if (
                self.token_type == DIRECT_LOGIN
                or self.token_type == CHANGE_FORGOT_PASSWORD
            ):
                return (
                    "Your request for forgot password is expired. Please request again!"
                )
            return "Token has expired. Please register again."
        except jwt.InvalidTokenError:
            return "Invalid token"
        except Exception as error:
            return "Error occurred on server while decoding verification token"

    def simple_jwt_response(self, tokens):
        response = JsonResponse({"status": 200})
        access_token_lifetime = timedelta(
            minutes=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds() / 60
        )
        refresh_token_lifetime = timedelta(
            days=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days
        )
        response.set_cookie(
            "access",
            tokens.get("access"),
            expires=timezone.now() + access_token_lifetime,
            secure=True,
        )
        response.set_cookie(
            "refresh",
            tokens.get("refresh"),
            expires=timezone.now() + refresh_token_lifetime,
            secure=True,
        )
        return response

    def simple_jwt_token(self, data):
        token_serializer = MyTokenObtainPairSerializer(
            data={
                "email": data.get("email"),
                "password": data.get("password"),
            }
        )
        if token_serializer.is_valid(raise_exception=True):
            tokens = token_serializer.validated_data
            return self.simple_jwt_response(tokens)


class CustomRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)

        token["email"] = user.email
        token["username"] = user.username

        return token
