from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=100)
    password = serializers.CharField(write_only=True)  # Excluded when returning the user
    profile_image = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = ["email", "username", "password", "profile_image"]

    def create(self, validated_data):
        profile_image = validated_data.pop('profile_image', None)
        user = User.objects.create(**validated_data)
        if profile_image:
            user.profile_image = profile_image
            user.save()
        return user
