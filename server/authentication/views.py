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
    def post(self, request):
        data = request.data
        email = data.get("email")

        if not email:
            return ApiResponse.response_failed(message="Email is required", status=404)

        data["username"] = email[: email.find("@") :]
        serializer = UserSerializer(data=data)

        if serializer.is_valid(raise_exception=True):
            try:
                user = serializer.save()
                # print(user.profile_image.url)
                token = VerificationEmail.generate_token(user.id)

                if token:
                    email = BaseEmail(
                        sender=os.environ.get("ADMIN_EMAIL"),
                        recipient=serializer.validated_data.get("email"),
                        subject="Email verification",
                        content={
                            "username": serializer.validated_data.get("username"),
                            "verification_link": f"http://127.0.01:8000/api/v1/auth/verify-email/?token={token}",
                        },
                    )
                    email.send_email()

            except IntegrityError as error:
                print("In integrity error", error)
                if "unique constraint" in str(error).lower():
                    return ApiResponse.response_failed(
                        message="A user with this email address already exists.",
                        status=400,
                    )
            except Exception as error:
                return ApiResponse.response_failed(
                    message="Error occurred on server. Please try registering again!",
                    status=500,
                )

            return ApiResponse.response_succeed(
                message="For verification, check your email",
                data=serializer.data,
                status=201,
            )

        return ApiResponse.response_failed(message="Failed", status=404)

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
