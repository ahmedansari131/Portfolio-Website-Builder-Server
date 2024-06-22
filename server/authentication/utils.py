from .models import User
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import os

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
