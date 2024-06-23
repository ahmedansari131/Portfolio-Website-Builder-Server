from django.http import JsonResponse
from .models import User
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import os
import secrets


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
    response, key, value, life, path="/", httponly=False, samesite="None", secure=True
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
