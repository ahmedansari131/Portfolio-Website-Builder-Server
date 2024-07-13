from rest_framework import serializers
from .models import PortfolioProject, Template
from authentication.serializers import UserSerializer


class CreateProjectSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(max_length=50)
    template_id = serializers.CharField(max_length=100)
    s3_file_name = serializers.CharField(max_length=50)
    s3_folder_name = serializers.CharField(max_length=50)
    bucket_name = serializers.CharField(max_length=50)

    class Meta:
        model = PortfolioProject
        fields = ["project_name", "template_id", "s3_file_name", "s3_folder_name", "bucket_name"]


class ListTemplatesSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    
    class Meta:
        model = Template
        fields = "__all__"