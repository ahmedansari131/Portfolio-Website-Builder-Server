import jwt
from django.utils import timezone
from datetime import timedelta
import os
from .models import User

class Token:
    @staticmethod
    def generate_token(user_id):
        if not user_id:
            return "User id not found"

        expiration_time = timezone.now() + timedelta(
            minutes=int(os.environ.get("VERIFICATION_TIME_LIMIT"))
        )

        try:
            encoded_token = jwt.encode(
                {"id": user_id, "exp": expiration_time},
                os.environ.get("VERIFICATION_EMAIL_SECRET"),
                algorithm="HS256",
            )
            return encoded_token
        except Exception as error:
            return "Error occurred on server while generating verification token"

    @staticmethod
    def verify_token(token):
        try:
            decoded_token = jwt.decode(
                token, os.environ.get("VERIFICATION_EMAIL_SECRET"), algorithms="HS256"
            )
            user = User.objects.filter(id=decoded_token.get("id")).first()

            if user and user.is_active:
                return (
                    f"{user.username}'s is already has an active account and can login."
                )
            return decoded_token
        except jwt.ExpiredSignatureError:
            return "Token has expired. Please register again."
        except jwt.InvalidTokenError:
            return "Invalid token"
        except Exception as error:
            return "Error occurred on server while decoding verification token"
        