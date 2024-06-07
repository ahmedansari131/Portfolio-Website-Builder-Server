from rest_framework import serializers
from .models import User


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
        email = data.get('email')
        if email and 'username' not in data:
            data['username'] = email.split('@')[0]
        return super().to_internal_value(data)


    def create(self, validated_data):
        profile_image = validated_data.pop("profile_image", None)
        user = User.objects.create(**validated_data)
        if profile_image:
            user.profile_image = profile_image
            user.save()
        return user
