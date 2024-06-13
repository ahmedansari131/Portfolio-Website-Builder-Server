from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from .models import User
from .serializers import (
    ChangeForgotPasswordSerializer,
    UserSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    ForgotPasswordSerializer,
)
from server.response.api_response import ApiResponse
from django.db import IntegrityError
from .email import UserVerificationEmail
from .utils import get_existing_user
from .jwt_token import Token, CustomRefreshToken
import os
from .serializers import MyTokenObtainPairSerializer
from server.email import BaseEmail
from .constants import DIRECT_LOGIN, CHANGE_FORGOT_PASSWORD
from django.http import JsonResponse

class UserRegistration(APIView):
    def verification_token(self, user_id, request):
        tokenization = Token(user_id=user_id)
        token = tokenization.generate_token()
        if token:
            verification_link = (
                f'{os.environ.get("CLIENT_PATH_PREFIX")}/verify-email/?token={token}'
            )
            return verification_link

    def verification_email(self, data):
        return UserVerificationEmail(
            sender=os.environ.get("NO_REPLY_EMAIL"),
            recipient=data.get("recipient"),
            content=data.get("content"),
        ).send_verification_email()

    def post(self, request):
        data = request.data
        serializer = UserSerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            try:
                email = data.get("email")
                user_exist = User.objects.filter(email=email).first()
                if user_exist:
                    is_user_active = user_exist.is_active
                    if is_user_active:
                        return ApiResponse.response_failed(
                            message="User already exist. Please login!", status=403
                        )
                    else:
                        verification_link = self.verification_token(
                            user_exist.id, request
                        )
                        email_data = {
                            "recipient": user_exist.email,
                            "content": {
                                "username": user_exist.username,
                                "verification_link": verification_link,
                            },
                        }
                        email_sent = self.verification_email(email_data)

                        if not email_sent:
                            return ApiResponse.response_failed(
                                message="Error occurred on server while sending verification email. Please register again!",
                                status=500,
                            )
                        return ApiResponse.response_succeed(
                            message=f"User is inactive. Account activation email is sent on {user_exist.email}!",
                            status=200,
                        )

                user = serializer.save()
                verification_link = self.verification_token(user.id, request)
                email_data = {
                    "recipient": serializer.validated_data.get("email"),
                    "content": {
                        "username": serializer.validated_data.get("username"),
                        "verification_link": verification_link,
                    },
                }
                email_sent = self.verification_email(email_data)
                if not email_sent:
                    return ApiResponse.response_failed(
                        message="Error occurred on server while sending verification email. Please register again!",
                        status=500,
                    )
                return ApiResponse.response_succeed(
                    message="For verification, check your email",
                    data=serializer.data,
                    status=201,
                )

            except IntegrityError as error:
                if "unique constraint" in str(error).lower():
                    return ApiResponse.response_failed(
                        message="A user with this email address already exists.",
                        status=403,
                    )
            except Exception as error:
                print("Error ->", error)
                return ApiResponse.response_failed(
                    message="Error occurred on server while registering the user. Please try registering again!",
                    status=500,
                )

        return ApiResponse.response_failed(
            message="Error occurred on server while registering the user", status=500
        )


class UserEmailVerification(APIView):
    def get(self, request):
        verification_token = request.GET.get("token")
        if verification_token:
            tokenization = Token()
            decoded_token = tokenization.verify_token(verification_token)

            if isinstance(decoded_token, dict) and "id" in decoded_token:
                try:
                    user = User.objects.get(id=decoded_token["id"])
                    user.is_active = True
                    user.save()

                    return ApiResponse.response_succeed(
                        message=f"{user.username} is verified and can login.",
                        status=200,
                    )
                except Exception as error:
                    return ApiResponse.response_failed(
                        message="Error occurred while saving verified user", status=500
                    )
            elif isinstance(decoded_token, str):
                return ApiResponse.response_failed(message=decoded_token, status=403)
            else:
                return ApiResponse.response_failed(message=decoded_token, status=500)
        else:
            return ApiResponse.response_failed(
                message="Failed to get token", status=404
            )


class UserLogin(APIView):
    def post(self, request):
        data = request.data
        serializer = LoginSerializer(data=data, context={"request": request})

        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data.get("user")

            if not user:
                return ApiResponse.response_failed(
                    message=serializer.validated_data.get("error"), status=403
                )
            email = user.email
            password = serializer.validated_data.get("password")

            token_serializer = MyTokenObtainPairSerializer(
                data={
                    "email": email,
                    "password": password,
                }
            )
            if token_serializer.is_valid(raise_exception=True):
                tokens = token_serializer.validated_data
                response = JsonResponse({"status": 200})
                access_token_lifetime = timedelta(
                    minutes=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
                    / 60
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
        return ApiResponse.response_failed(
            message="Error occurred on server while login", status=500
        )


class ResetPassword(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        user_id = request.user.id

        serializer = ResetPasswordSerializer(data=data, context={"request": request})

        if serializer.is_valid(raise_exception=True):
            try:
                user = User.objects.get(id=user_id)
                user.set_password(serializer.validated_data.get("new_password"))
                user.save()
                reset_email = BaseEmail(
                    sender=os.environ.get("NO_REPLY_EMAIL"),
                    recipient=user.email,
                    subject="Reset Password",
                    message="Password reset successfully",
                    template_path="email_templates/reset_password_email.html",
                    content={"username": user.username},
                )
                email_sent = reset_email.send_email()
                return ApiResponse.response_succeed(
                    message="Password reset successfully!", status=201
                )

            except User.DoesNotExist:
                return ApiResponse.response_failed(
                    message="User does not exist",
                    status=404,
                )
            except Exception as error:
                print("Error occurred while resetting the password -> ", error)
                return ApiResponse.response_failed(
                    message="Error occurred on server while resetting the password",
                    status=500,
                )

        return ApiResponse.response_succeed(message="Successful", status=200)


class ForgotPassword(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token_param = request.GET.get("token")
        token = Token(token_type=DIRECT_LOGIN)
        verified_token = token.verify_token(token=token_param)

        if isinstance(verified_token, str):
            return ApiResponse.response_failed(message=verified_token, status=403)

        user_id = verified_token.get("id")
        token_type = verified_token.get("token_type")

        if token_type == DIRECT_LOGIN and user_id:
            try:
                user = User.objects.get(id=user_id)
                refresh = CustomRefreshToken.for_user(user)
                tokens = {"access": refresh.access_token, "refresh": refresh}
                return token.simple_jwt_response(tokens=tokens)
            except User.DoesNotExist:
                return ApiResponse.response_failed(
                    message="User does not exist", status=404
                )
            except Exception as error:
                print("Error occurred while issuing the tokens -> ", error)
                return ApiResponse.response_failed(
                    message="Error occurred on the server", status=500
                )
        elif token_type == CHANGE_FORGOT_PASSWORD and user_id:
            user = get_existing_user(user_id=user_id)
            if isinstance(user, User):
                return ApiResponse.response_succeed(
                    message="Token is valid", status=200
                )
            else:
                return ApiResponse.response_failed(message=user, status=404)
        return ApiResponse.response_failed(
            message="Error occurred on server", status=500
        )

    def post(self, request):
        data = request.data
        serializer = ForgotPasswordSerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data.get("user")

            for_login_token = Token(user_id=user.id, token_type=DIRECT_LOGIN)
            generated_login_token = for_login_token.generate_token()

            for_change_password_token = Token(
                user_id=user.id, token_type=CHANGE_FORGOT_PASSWORD
            )
            generated_change_password_token = for_change_password_token.generate_token()

            login_url = request.build_absolute_uri(
                f'/{os.environ.get("API_PATH_PREFIX")}/verify-user?token={generated_login_token}'
            )
            change_password_url = request.build_absolute_uri(
                f'/{os.environ.get("API_PATH_PREFIX")}/verify-user?token={generated_change_password_token}'
            )

            forgot_password_email = BaseEmail(
                sender=os.environ.get("NO_REPLY_EMAIL"),
                recipient=user.email,
                message="Forgot Password",
                content={
                    "username": user.username,
                    "login_url": login_url,
                    "reset_password_url": change_password_url,
                },
                subject="Forgot Password",
                template_path="email_templates/forgot_password_email.html",
            )
            email_sent = forgot_password_email.send_email()

            return ApiResponse.response_succeed(
                message=f"Email is sent on your {user.email}", status=200
            )
        return ApiResponse.response_failed(
            message="Error occurred on server", status=500
        )

    def patch(self, request):
        data = request.data

        tokenization = Token(token_type=CHANGE_FORGOT_PASSWORD)
        verified_token = tokenization.verify_token(token=data.get("token"))
        if isinstance(verified_token, str):
            return ApiResponse.response_failed(message=verified_token, status=403)

        user_id = verified_token.get("id")

        serializer = ChangeForgotPasswordSerializer(
            data=data, context={"user_id": user_id}
        )
        if serializer.is_valid(raise_exception=True):
            new_password = serializer.validated_data.get("new_password")
            try:
                user = get_existing_user(user_id=user_id)
                if isinstance(user, User):
                    user.set_password(new_password)
                    user.save()
                    return ApiResponse.response_succeed(
                        message="Password changed successfully", status=201
                    )
                else:
                    return ApiResponse.response_failed(message=user, status=404)
            except Exception as error:
                print("Error occurred while changing the password -> ", error)
                return ApiResponse.response_failed(
                    message="Error occurred on server while changing the password",
                    status=500,
                )

        return ApiResponse.response_failed(
            message="Error occurred on server while changing the password", status=500
        )
