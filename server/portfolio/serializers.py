from rest_framework import serializers
from .models import PortfolioProject, Template
from authentication.serializers import UserSerializer
from server.utils.response import BaseResponse


class CreateProjectSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(max_length=50)
    template_name = serializers.CharField(max_length=100)

    class Meta:
        model = PortfolioProject
        fields = ["project_name", "template_name"]

    def validate_project_name(self, value):
        if PortfolioProject.objects.filter(project_name=value).exists():
            return BaseResponse.error(message="Project with this name already exists")
        return value


class ListTemplatesSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()

    class Meta:
        model = Template
        fields = "__all__"
