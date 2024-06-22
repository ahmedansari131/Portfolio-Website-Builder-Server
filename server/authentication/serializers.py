from rest_framework import serializers
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db.models import Q
from server.utils.response import BaseResponse
from .utils import get_existing_user


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=100)
    password = serializers.CharField(
        write_only=True
    )  # Excluded when returning the user
    profile_image = serializers.ImageField(required=False)
    username = serializers.CharField(required=True)
    is_terms_agree = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ["email", "username", "password", "profile_image", "is_terms_agree"]

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        return value

    def validate(self, data):
        if not data.get("is_terms_agree"):
            raise serializers.ValidationError(
                "Terms and conditions must be agreed before registering"
            )
        return data

    def to_internal_value(self, data):
        email = data.get("email")
        if email and "username" not in data:
            data["username"] = email.split("@")[0]

        return super().to_internal_value(data)

    def create(self, validated_data):
        profile_image = validated_data.pop("profile_image", None)
        password = validated_data.pop("password", None)

        if not password:
            raise serializers.ValidationError("Password is required")

        user = User(**validated_data)
        user.profile_image = profile_image
        user.set_password(password)

        user.save()
        return user


class LoginSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "identifier",
            "password",
        ]

    def authenticate(self, request, identifier, password):
        try:
            user = User.objects.get(Q(email=identifier) | Q(username=identifier))
        except User.DoesNotExist:
            return {"message": {"identifier": "User does not exist"}}

        if user and not user.check_password(password):
            return {"message": {"password": "Incorrect password"}}
        print(request.user)
        return user

    def validate_identifier(self, value):
        if not value:
            raise serializers.ValidationError(
                "Either username or email must be provided"
            )
        return value

    def validate(self, data):
        identifier = data.get("identifier")
        password = data.get("password")
        request = self.context.get("request")
        user = None

        authenticated_user = self.authenticate(
            request=request, identifier=identifier, password=password
        )

        if not isinstance(authenticated_user, User):
            return BaseResponse.error(message=authenticated_user.get("message"))

        user = authenticated_user

        data["user"] = user
        return data


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["username"] = user.username
        token["email"] = user.email

        return token


class ResetPasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["new_password", "password"]

    def validate(self, data):
        password = data.get("password")
        request = self.context.get("request")

        try:
            user = User.objects.get(id=request.user.id)
            if user and not user.check_password(password):
                raise serializers.ValidationError("Incorrect password")
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        except Exception as error:
            raise serializers.ValidationError(error)

        return data


class ForgotPasswordSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(max_length=100)

    class Meta:
        model = User
        fields = ["identifier"]

    def validate(self, data):
        identifier = data.get("identifier")

        try:
            user = User.objects.get(Q(email=identifier) | Q(username=identifier))
        except User.DoesNotExist:
            return {"message": {"identifier": "User does not exist"}}
        except Exception as error:
            raise serializers.ValidationError(error)

        data["user"] = user
        return data


class ChangeForgotPasswordSerializer(serializers.ModelSerializer):
    new_password = serializers.CharField(max_length=100, write_only=True)

    class Meta:
        model = User
        fields = ["new_password"]

    def validate(self, data):
        new_password = data.get("new_password")
        user_id = self.context.get("user_id")
        try:
            user = get_existing_user(user_id=user_id)

            if not isinstance(user, User):
                raise serializers.ValidationError(user)

            if user.check_password(new_password):
                return {
                    "message": "New password must be different from previous password"
                }
            return data
        except Exception as error:
            raise serializers.ValidationError(error)
