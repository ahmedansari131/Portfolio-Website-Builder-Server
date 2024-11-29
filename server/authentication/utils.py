from .models import User
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import os
import secrets
from .jwt_token import Token
from django.conf import settings
import requests
from rest_framework.validators import ValidationError
from django.core.files.base import ContentFile
import time
from server.exceptions import GeneralServiceError, CustomAPIException
from authentication.models import Provider
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.http import JsonResponse
import random
from .constants import PROFILE_PLACEHOLDER_COLORS


def get_existing_user(user_id):
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        return "User does not exist"
    except Exception as error:
        return error


def is_username_available(username):
    if not username:
        raise ValidationError("Username is not provided.")

    try:
        is_unique = not User.objects.filter(username__iexact=username).exists()
        if not is_unique:
            return False

        return True
    except Exception as error:
        print("Error occurred while checking the username availability -> ", error)
        raise ValidationError("Error occurred while checking the username")


def verify_simple_jwt(token):
    try:
        # Verify the token
        UntypedToken(token)

        # Decode token to get data
        token_backend = TokenBackend(
            algorithm="HS256", signing_key=os.environ.get("JWT_SECRET")
        )
        valid_data = token_backend.decode(token, verify=True)
        return valid_data
    except TokenError as e:
        raise InvalidToken(e)


def generate_otp(length=6):
    otp = "".join([str(secrets.randbelow(10)) for _ in range(length)])
    return otp


def set_cookie_helper(
    response, key, value, life, path="/", httponly=True, samesite="None", secure=True
):
    response.set_cookie(
        key,
        value,
        max_age=life,
        path=path,
        httponly=httponly,
        samesite=samesite,
        secure=secure,
    )
    return response


def generate_email_verification_link(user_id, token_type, **kwargs):
    tokenization = Token(user_id=user_id, token_type=token_type, **kwargs)
    token = tokenization.generate_token()
    if token:
        verification_link = (
            f'{os.environ.get("CLIENT_PATH_PREFIX")}/verify-email/?token={token}'
        )
        return verification_link


def google_get_access_token(*, code: str, redirect_uri: str) -> str:
    data = {
        "code": code,
        "client_id": settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        "client_secret": settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    response = requests.post("https://oauth2.googleapis.com/token", data=data)

    if not response.ok:
        raise ValidationError("Failed to obtain access token from Google.")

    access_token = response.json()

    return access_token


class GoogleOAuthProvider:
    def exchange_auth_code(self, code, redirect_uri):
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        token_response = requests.post(token_url, data=token_data)
        token_response_data = token_response.json()

        if "error" in token_response_data:
            raise ValidationError(token_response_data)

        access_token = token_response_data["access_token"]
        return access_token

    def get_user_info(self, access_token):
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        user_info_response = requests.get(
            user_info_url, headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_response.json()

        if "error" in user_info:
            raise ValidationError(user_info)

        return user_info

    def create_or_get_user(self, username, user_email, profile_pic):
        try:
            user = User.objects.filter(email=user_email).first()
            if user:
                return user
            print("Profile -> ", profile_pic)
            if profile_pic:
                file_content = self.upload_profile_picture_to_s3(
                    profile_pic_url=profile_pic
                )
            else:
                file_content = None

            user = User.objects.create(
                email=user_email,
                username=username,
                is_active=True,
                provider=Provider.GOOGLE,
                profile_image=file_content,
                profile_placeholder_color_code=random.choice(
                    PROFILE_PLACEHOLDER_COLORS
                ),
            )

            return user
        except Exception as error:
            print("Error occurred while creating or getting the user -> ", error)
            raise GeneralServiceError(str(error))

    def upload_profile_picture_to_s3(self, profile_pic_url):
        # Download the profile picture
        try:
            response = requests.get(profile_pic_url, stream=True)
            if response.status_code != 200:
                raise Exception("Failed to download profile picture.")
        except Exception as error:
            raise GeneralServiceError(str(error))

        # Create a file-like object
        file_name = f"profile-{int(time.time())}.jpg"
        file_content = ContentFile(response.content, name=file_name)

        if file_content:
            return file_content
        return None


class GenerateAndSetJWT:
    def __init__(self, user):
        self.user = user
        self.__access_token_life = timedelta(
            minutes=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds() / 60
        )
        self.__refresh_token_life = timedelta(
            days=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days
        )
        self.__refresh_token = ""

    def generate_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        # Customize token payload
        refresh["username"] = self.user.username
        refresh["email"] = self.user.email
        self.__refresh_token = refresh

        try:
            user = User.objects.get(id=self.user.id)
            if not user.is_active:
                raise CustomAPIException(
                    "User is inactive. Please sign up again to make it active."
                )

            user.refresh_token = self.__refresh_token
            user.save()
            return
        except User.DoesNotExist:
            raise ValidationError("User does not exist.")
        except Exception as error:
            print("Error occurred while generating tokens -> ", error)
            raise CustomAPIException(str(error))

    def set_jwt_cookie(self):
        cookies = [
            {
                "key": "access",
                "value": str(self.__refresh_token.access_token),
                "life": self.__access_token_life,
            },
            {
                "key": "refresh",
                "value": str(self.__refresh_token),
                "life": self.__refresh_token_life,
            },
        ]

        response = JsonResponse(
            {"status": 200, "message": "You are now signed in to your account."}
        )
        for cookie in cookies:
            response = set_cookie_helper(
                key=cookie["key"],
                value=cookie["value"],
                life=cookie["life"],
                response=response,
            )

        return response
