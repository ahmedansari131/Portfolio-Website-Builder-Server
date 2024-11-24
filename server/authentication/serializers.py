from rest_framework import serializers
from .models import User, PasswordReset
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db.models import Q
from server.utils.response import BaseResponse


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "profile_image", "is_active"]


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=100)
    password = serializers.CharField(
        write_only=True
    )  # Excluded when returning the user
    profile_image = serializers.ImageField(required=False)
    username = serializers.CharField(required=True)
    is_terms_agree = serializers.BooleanField(default=False, write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "password", "profile_image", "is_terms_agree"]

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        return value

    def validate_is_terms_agree(self, value):
        if not value:
            raise serializers.ValidationError(
                "Terms and conditions must be agreed before registering"
            )
        return value

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
            raise serializers.ValidationError(
                {"identifier": "User does not exist with this email or username."}
            )
        except Exception as error:
            raise serializers.ValidationError(
                {
                    "error": "An unexpected error occurred. Please contact support or try again in some time."
                }
            )

        if user and not user.check_password(password):
            raise serializers.ValidationError(
                {"password": "Password entered is incorrect."}
            )
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

        authenticated_user = self.authenticate(
            request=request, identifier=identifier, password=password
        )

        if not authenticated_user:
            raise serializers.ValidationError(
                {
                    "error": "An unexpected error occurred. Please contact support or try again in some time."
                }
            )

        data["user"] = authenticated_user
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
        new_password = data.get("new_password")
        request = self.context.get("request")

        if len(new_password) < 8:
            return {
                "message": {"new_password": "Password must be of atleast 8 characters"}
            }

        try:
            user = User.objects.get(id=request.user.id)
            if user and not user.check_password(password):
                return {"message": {"old_password": "Incorrect Password"}}
        except User.DoesNotExist:
            return {"message": "User does not exist"}
        except Exception as error:
            return {"message": "Error occured on server"}

        return data


class ForgotPasswordRequestSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(max_length=100)

    class Meta:
        model = User
        fields = ["identifier"]

    def validate_identifier(self, value):
        try:
            user = User.objects.get(Q(email=value) | Q(username=value))
            self.user_instance = user
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "User does not exist with this email or username"
            )
        except Exception as error:
            raise serializers.ValidationError(error)

        return value

    def validate(self, attrs):
        attrs["user"] = self.user_instance
        return attrs


class ForgotPasswordConfirmationSerializer(serializers.ModelSerializer):
    otp = serializers.CharField(max_length=6, write_only=True)
    new_password = serializers.CharField(write_only=True)

    class Meta:
        model = PasswordReset
        fields = ["otp", "new_password"]

    def validate(self, data):
        otp = data.get("otp")
        new_password = data.get("new_password")
        user = self.context.get("user")
        token = self.context.get("token")
        request = self.context.get("request")

        if len(new_password) < 8:
            return {
                "message": {"new_password": "Password must be of 8 characters long"}
            }

        if len(otp) < 6:
            return {"message": {"otp": "OTP must be of 6 digits"}}

        return data
