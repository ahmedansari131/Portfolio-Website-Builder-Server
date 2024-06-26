from datetime import timedelta
from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from .models import User, PasswordReset
from .serializers import (
    UserSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    ForgotPasswordRequestSerializer,
    ForgotPasswordConfirmationSerializer,
)
from server.response.api_response import ApiResponse
from django.db import IntegrityError
from .email import UserVerificationEmail
from .utils import get_existing_user, verify_simple_jwt, generate_otp, set_cookie_helper
from .jwt_token import Token, CustomRefreshToken
import os
from .serializers import MyTokenObtainPairSerializer
from server.email import BaseEmail
from .constants import DIRECT_LOGIN, CHANGE_FORGOT_PASSWORD
from django.http import JsonResponse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.tokens import UntypedToken
from datetime import datetime, timedelta, timezone


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
                password = data.get("password")
                user_exist = User.objects.filter(email=email).first()

                if user_exist:
                    is_valid_user = user_exist.check_password(password)

                    if not is_valid_user:
                        return ApiResponse.response_failed(
                            message={"password": "Incorrect password"}, status=403
                        )

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
                    message=serializer.validated_data.get("message"), status=403
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
                cookies = [
                    {
                        "key": "access",
                        "value": tokens.get("access"),
                        "life": access_token_lifetime,
                    },
                    {
                        "key": "refresh",
                        "value": tokens.get("refresh"),
                        "life": refresh_token_lifetime,
                    },
                ]
                response = JsonResponse({"status": 200})
                for cookie in cookies:
                    response = set_cookie_helper(
                        key=cookie["key"],
                        value=cookie["value"],
                        life=cookie["life"],
                        response=response,
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


class ForgotPasswordRequest(APIView):
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
        serializer = ForgotPasswordRequestSerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data.get("user")
            if not user:
                return ApiResponse.response_failed(
                    message=serializer.validated_data.get("message"), status=403
                )

            otp = generate_otp()
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            refresh = RefreshToken.for_user(user)
            signin_token = str(refresh.access_token)

            reset_forgot_password_link = f'{request.scheme}://{os.environ.get("CLIENT_PATH_PREFIX")}/reset-forgot-password/{uid}/{token}/'
            direct_signin_link = f'{request.scheme}://{os.environ.get("CLIENT_PATH_PREFIX")}/direct-signin/{uid}/{signin_token}/'

            try:
                PasswordReset.objects.create(
                    user=user,
                    token=token,
                    signin_token=signin_token,
                    ip_address=request.ip_address,
                    user_agent=request.user_agent,
                    otp=otp,
                )
            except Exception as error:
                print("Error occurred while creating password reset object -> ", error)
                return ApiResponse.response_failed(
                    message="Error occurred on server. Please try again in some time",
                    status=500,
                )

            reset_password_request_email = BaseEmail(
                sender=os.environ.get("NO_REPLY_EMAIL"),
                recipient=user.email,
                message="Forgot Password",
                content={
                    "username": user.username,
                    "signin_link": direct_signin_link,
                    "reset_password_link": reset_forgot_password_link,
                    "otp": otp,
                },
                subject="Forgot Password",
                template_path="email_templates/forgot_password_email.html",
            )
            reset_password_request_email.send_email()
            return ApiResponse.response_succeed(
                message=f"Email is sent to your {user.email} address", status=200
            )

        return ApiResponse.response_failed(
            message="Error occurred on server. Please try again or contact our support team at support@portify.com",
            status=500,
        )


class ForgotPasswordConfirmation(APIView):
    def post(self, request, uid, token):
        data = request.data

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = get_existing_user(user_id=user_id)
        except Exception as error:
            return ApiResponse.response_failed(message="Invalid request", status=400)

        serializer = ForgotPasswordConfirmationSerializer(
            data=data, context={"user": user, "token": token, "request": request}
        )
        if serializer.is_valid(raise_exception=True):
            valid_otp = serializer.validated_data.get("otp")
            valid_password = serializer.validated_data.get("new_password")

            if not valid_password or not valid_otp:
                return ApiResponse.response_failed(
                    message=serializer.validated_data.get("message"), status=400
                )

            try:
                reset_record = PasswordReset.objects.filter(
                    user=user, token=token
                ).first()
            except Exception as error:
                print(
                    "Error occurred in serializer while getting the reset records -> ",
                    error,
                )
                return ApiResponse.response_failed(
                    message="Invalid request!", status=400
                )

            if (
                reset_record.ip_address != request.ip_address
                or reset_record.user_agent != request.user_agent
            ):
                return ApiResponse.response_failed(
                    message="Invalid request!", status=400
                )

            if reset_record.created_at < datetime.now(timezone.utc) - timedelta(
                minutes=15
            ):
                return ApiResponse.response_failed(
                    message="Token expired! Please try again", status=403
                )

            if reset_record.otp != valid_otp:
                reset_record.attempts += 1
                reset_record.save()
                if reset_record.attempts >= 3:
                    # lock_account(user)
                    return ApiResponse.response_failed(
                        message="Account has been locked for multiple invalid request",
                        status=400,
                    )
                return ApiResponse.response_failed(
                    message={
                        "otp": f"Invalid OTP. You have left {3 - reset_record.attempts} attempts. Account will be locked for sometime if the limit exceeds"
                    },
                    status=401,
                )

            user.set_password(valid_password)
            user.save()
            return ApiResponse.response_succeed(
                message="Password reset successfully", status=200
            )
        return ApiResponse.response_failed(
            message="Error occurred on the server", status=500
        )


class VerifyValidForgotPasswordRequest(APIView):
    def post(self, request, uid, token):
        try:
            token = PasswordReset.objects.get(token=token)
            if token:
                return ApiResponse.response_succeed(message="Valid request", status=200)

        except PasswordReset.DoesNotExist:
            return ApiResponse.response_failed(message="Invalid Request!", status=400)
        except Exception as error:
            return ApiResponse.response_failed(message="Invalid request!", status=400)
        return ApiResponse.response_failed(
            message="Error occurred on server", status=500
        )


class DirectSignin(APIView):
    def post(self, request, uid, signin_token):
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = get_existing_user(user_id=uid)
        except Exception as error:
            print("Error occurred -> ", error)
            return ApiResponse.response_failed(message="Invalid token!", status=400)
        # Check for token if it is in the db or not && And also delete the token from the db after hitting this view
        try:
            access_token = AccessToken(signin_token)
            if access_token.get("user_id") != user.id:
                return ApiResponse.response_failed(message="Invalid token!", status=400)
        except Exception as error:
            print("Error occurred while verifying the signin token -> ", error)
            return ApiResponse.response_failed(message="Invalid token!", status=400)

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        refresh["username"] = user.username
        refresh["email"] = user.email
        access_token.payload["username"] = user.username
        access_token.payload["email"] = user.email
        response = JsonResponse({"status": 200})

        access_token_lifetime = timedelta(
            minutes=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds() / 60
        )
        refresh_token_lifetime = timedelta(
            days=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days
        )
        cookies = [
            {
                "key": "access",
                "value": access_token,
                "life": access_token_lifetime,
            },
            {
                "key": "refresh",
                "value": refresh,
                "life": refresh_token_lifetime,
            },
        ]

        response = JsonResponse({"status": 200})
        for cookie in cookies:
            response = set_cookie_helper(
                key=cookie["key"],
                value=cookie["value"],
                life=cookie["life"],
                response=response,
            )
        return response


class UserProfile(APIView):
    def get(self, request):
        cookie = request.COOKIES
        if not cookie:
            return ApiResponse.response_failed(
                message="Please login to proceed further", status=403
            )
        try:
            verified_token = verify_simple_jwt(cookie.get("access"))
        except Exception as error:
            return ApiResponse.response_failed(
                message=str(error),
                status=403,
            )

        user = get_existing_user(user_id=verified_token.get("user_id"))
        if isinstance(user, User):
            user = {
                "username": user.username,
                "email": user.email,
                "user_id": user.id,
                "profile_img": user.profile_image.url,
            }
            return ApiResponse.response_succeed(
                data=user,
                status=200,
            )
        else:
            return ApiResponse.response_failed(
                message=user or "User does not exist", status=404
            )


class UserToken(APIView):
    def get(self, request):
        cookie = request.COOKIES
        return JsonResponse({"token": cookie.get("access")})


class UserSignout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            response = JsonResponse({"message": "Signed out successfully."})
            response.set_cookie(
                "access",
                "",
                max_age=0,
                path="/",
                httponly=False,
                samesite="None",
                secure=True,
            )

            response.set_cookie(
                "refresh",
                "",
                max_age=0,
                path="/",
                httponly=False,
                samesite="None",
                secure=True,
            )

            return response
        except Exception as error:
            print("Error occurred while signing out the user -> ", error)
            return ApiResponse.response_failed(
                message="Error occurred on server while signing out the user. Please try again in sometime!",
                status=500,
            )


class CheckUsernameAvailability(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        username = request.GET.get("username")
        print("Username -> ", username)
        if not username:
            return ApiResponse.response_failed(
                message="Please provide the username", status=404
            )

        if username.lower() == request.user.username.lower():
            return ApiResponse.response_succeed(
                message="Username is available", status=200
            )

        try:
            is_unique = not User.objects.filter(username=username.lower()).exists()
            if not is_unique:
                return ApiResponse.response_failed(
                    message="Username is already taken", status=404
                )

            return ApiResponse.response_succeed(
                message="Username is available", status=200
            )
        except Exception as error:
            print("Error occurred while validating the username -> ", error)
            return ApiResponse.response_failed(
                message="Error occurred on server while validating the username. Please try again in some time or contact at support@portify.com",
                status=500,
            )
