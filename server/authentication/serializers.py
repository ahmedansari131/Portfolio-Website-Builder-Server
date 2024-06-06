from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length = 100)
    password = serializers.CharField(write_only=True) # exluded when returning the user
    class Meta:
        model = User
        fields = ['email', 'username', 'password']