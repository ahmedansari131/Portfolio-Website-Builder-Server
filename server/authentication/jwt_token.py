import jwt
from django.utils import timezone
from datetime import timedelta
import os
from .models import User
from .serializers import MyTokenObtainPairSerializer
from django.http.response import JsonResponse
from django.conf import settings
from .constants import (
    CHANGE_FORGOT_PASSWORD,
    DIRECT_LOGIN,
    EMAIL_VERIFICATION_TOKEN_TYPE,
)
from rest_framework_simplejwt.tokens import RefreshToken
from portfolio.models import PortfolioProject


class EmailVerification:
    @staticmethod
    def portfolio_contact_email_verification(decoded_token):
        try:
            user_id = decoded_token.get("id")
            project_id = decoded_token.get("project_id")
            portfolio_project_instance = PortfolioProject.objects.get(
                id=project_id, created_by=user_id
            )
            portfolio_project_instance.is_verified_portfolio_contact_email = True
            portfolio_project_instance.save()

            return "Portfolio contact email is now verified."
        except jwt.ExpiredSignatureError:
            return "Email verification link is expired."
        except jwt.InvalidTokenError:
            return "Email verification token is invalid"
        except Exception as error:
            return str(error)

    @staticmethod
    def auth_email_verification(decoded_token, token_type):
        try:
            user_instance = User.objects.filter(id=decoded_token.get("id")).first()
            if user_instance:
                if user_instance.is_active and (
                    token_type == DIRECT_LOGIN or token_type == CHANGE_FORGOT_PASSWORD
                ):
                    return decoded_token
                else:
                    user_instance.is_active = True
                    user_instance.save()
                    return f"{user_instance.username} is verified and can login."

        except jwt.ExpiredSignatureError:
            if token_type == DIRECT_LOGIN or token_type == CHANGE_FORGOT_PASSWORD:
                return (
                    "Your request for forgot password is expired. Please request again!"
                )
            return ""
        except jwt.InvalidTokenError:
            return "Token is invalid."
        except Exception as error:
            return str(error)


class Token:
    def __init__(self, user_id=None, token_type=None, **kwargs):
        self.user_id = user_id
        self.token_type = token_type
        self.additional_data = kwargs

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
                **self.additional_data,
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
            token_type = decoded_token.get("token_type")
            if token_type == EMAIL_VERIFICATION_TOKEN_TYPE:
                verify_contact_email = (
                    EmailVerification.portfolio_contact_email_verification(
                        decoded_token
                    )
                )
                return verify_contact_email
            else:
                verification = EmailVerification.auth_email_verification(
                    decoded_token=decoded_token, token_type=self.token_type
                )
                return verification

            # user = User.objects.filter(id=decoded_token.get("id")).first()
            # if user and user.is_active:
            #     if (
            #         self.token_type == DIRECT_LOGIN
            #         or self.token_type == CHANGE_FORGOT_PASSWORD
            #     ):
            #         return decoded_token
            #     return (
            #         f"{user.username}'s is already has an active account and can login."
            #     )
            # return decoded_token
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
            return str(error)

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
