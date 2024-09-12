from rest_framework import serializers
from .models import PortfolioProject, Template, CustomizedTemplate
from authentication.serializers import UserSerializer
from server.utils.response import BaseResponse
from server.utils.s3 import get_cloudfront_domain
import os


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


class TemplateDataSerializer(serializers.ModelSerializer):
    cloudfront_domain = serializers.SerializerMethodField()

    class Meta:
        model = CustomizedTemplate
        fields = "__all__"

    def get_cloudfront_domain(self, obj):
        return get_cloudfront_domain(
            os.environ.get("PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID")
        )
    

class CustomizedTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomizedTemplate
        fields = ['id']


class ListPortfolioProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    customized_template_id = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioProject
        fields = "__all__"

    def get_customized_template_id(self, obj):
        try:
            customized_template = CustomizedTemplate.objects.get(portfolio_project=obj)
            return customized_template.id
        except CustomizedTemplate.DoesNotExist:
            return None

    def get_template_name(self, obj):
        try:
            template_name = CustomizedTemplate.objects.get(portfolio_project=obj)
            return template_name.template.template_name
        except CustomizedTemplate.DoesNotExist:
            return None