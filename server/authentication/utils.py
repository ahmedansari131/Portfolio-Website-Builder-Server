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


def get_existing_user(user_id):
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        return "User does not exist"
    except Exception as error:
        return error


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