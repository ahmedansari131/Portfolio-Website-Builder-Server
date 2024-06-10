from rest_framework import serializers
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db.models import Q
from server.utils import BaseResponse
from .utils import get_existing_user


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=100)
    password = serializers.CharField(
        write_only=True
    )  # Excluded when returning the user
    profile_image = serializers.ImageField(required=False)
    username = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ["email", "username", "password", "profile_image"]

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

    @staticmethod
    def user_exist(data):
        identifier = data

        if not identifier:
            return None

        try:
            user = User.objects.get(Q(email=identifier) | Q(username=identifier))
            if user and not user.is_active:
                return None

            return user
        except User.DoesNotExist:
            return None

    def authenticate(self, request, identifier, password):
        try:
            user = User.objects.get(Q(email=identifier) | Q(username=identifier))
        except User.DoesNotExist:
            return BaseResponse.error(message="User does not exist")

        if user and user.check_password(password):
            return user
        return BaseResponse.error(message="Incorrect password")

    def validate(self, data):
        identifier = data.get("identifier")
        password = data.get("password")
        request = self.context.get("request")
        authentication_error = None
        user = None

        if not identifier:
            raise serializers.ValidationError(
                "Either username or email must be provided"
            )

        does_user_exist = self.user_exist(data=identifier)
        if not does_user_exist:
            raise serializers.ValidationError(
                "User does not exist. Please register first!"
            )

        if does_user_exist:
            is_authenticated_user = self.authenticate(
                request=request, identifier=identifier, password=password
            )

            if isinstance(is_authenticated_user, dict):
                authentication_error = is_authenticated_user.get("message")
            else:
                user = is_authenticated_user

        data["user"] = user
        data["error"] = authentication_error
        print(data)
        return data


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        print(user)
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

        user = LoginSerializer.user_exist(data=identifier)

        if not user:
            raise serializers.ValidationError("User does not exist")

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
                raise serializers.ValidationError(
                    "New password must be different from previous password"
                )
            return data
        except Exception as error:
            raise serializers.ValidationError(error)

