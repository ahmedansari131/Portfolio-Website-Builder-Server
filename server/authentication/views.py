from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from .models import User
from .serializers import UserSerializer
from server.response.api_response import ApiResponse
from django.db import IntegrityError


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
                serializer.save()
                # Sending verification mail while saving
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
        return ApiResponse.response_succeed(
            message="This is get method", data={"key": "value"}, status=200
        )

    def put(self):
        pass


# {"username": "ahmedansari", "email": "ahmed@gmail.com", "password": "12345678"}
