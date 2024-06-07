from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from .models import User
from .serializers import UserSerializer
from server.response.api_response import ApiResponse
from django.db import IntegrityError
from server.utils import BaseEmail
from .utils import VerificationEmail
import os


class AuthenticateUser(APIView):

    def verification_token(self, user_id, request):
        token = VerificationEmail.generate_token(user_id)

        if token:
            verification_link = request.build_absolute_uri(
                f'/{os.environ.get("API_PATH_PREFIX")}/verify-email/?token={token}'
            )
            return verification_link

    def verification_email(self, data):
        email = BaseEmail(
            sender=os.environ.get("ADMIN_EMAIL"),
            recipient=data.get("recepient"),
            subject="Email verification",
            content=data.get("content"),
        )
        email.send_email()

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
                        return ApiResponse.response_succeed(
                            message="User already exist. Please login!", status=403
                        )
                    else:
                        verification_link = self.verification_token(
                            user_exist.id, request
                        )
                        email_data = {
                            "recepient": user_exist.email,
                            "content": {
                                "username": user_exist.username,
                                "verification_link": verification_link,
                            },
                        }
                        self.verification_email(email_data)
                        return ApiResponse.response_succeed(
                            message=f"User is inactive. Account activation email is sent on {user_exist.email}!",
                            status=200,
                        )

                user = serializer.save()
                verification_link = self.verification_token(user.id, request)
                email_data = {
                    "recepient": serializer.validated_data.get("email"),
                    "content": {
                        "username": serializer.validated_data.get("username"),
                        "verification_link": verification_link,
                    },
                }
                self.verification_email(email_data)

            except IntegrityError as error:
                if "unique constraint" in str(error).lower():
                    return ApiResponse.response_failed(
                        message="A user with this email address already exists.",
                        status=403,
                    )
            except Exception as error:
                print("Error ->", error)
                return ApiResponse.response_failed(
                    message="Error occurred on server. Please try registering again!",
                    status=500,
                )

            return ApiResponse.response_succeed(
                message="For verification, check your email",
                data=serializer.data,
                status=201,
            )

        return ApiResponse.response_failed(
            message="Error occurred on server while registering the user", status=500
        )

    def get(self, request):
        verification_token = request.GET.get("token")

        if verification_token:
            decoded_token = VerificationEmail.verify_token(verification_token)

            if isinstance(decoded_token, dict) and "id" in decoded_token:
                try:
                    user = User.objects.get(id=decoded_token["id"])
                    user.is_active = True
                    user.save()
                    return ApiResponse.response_succeed(
                        message="User is verified and can login.", status=200
                    )
                except Exception as error:
                    return ApiResponse.response_failed(
                        message="Error occurred while saving verified user", status=500
                    )

            else:
                return ApiResponse.response_failed(message=decoded_token, status=500)
        else:
            return ApiResponse.response_failed(
                message="Failed to get token", status=404
            )

    def put(self):
        pass
