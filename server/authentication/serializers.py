from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length = 100)
    class Meta:
        model = User
        fields = ['email', 'username']