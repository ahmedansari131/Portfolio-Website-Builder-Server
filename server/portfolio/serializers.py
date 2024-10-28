from rest_framework import serializers
from .models import PortfolioProject, Template, CustomizedTemplate
from authentication.serializers import UserSerializer
from server.utils.response import BaseResponse
from server.utils.s3 import get_cloudfront_domain
import os
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class CreateProjectSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(max_length=50)
    template_name = serializers.CharField(max_length=100)

    class Meta:
        model = PortfolioProject
        fields = ["project_name", "template_name"]

    def validate_project_name(self, value):
        if PortfolioProject.all_objects.filter(project_name=value).exists():
            print(PortfolioProject.all_objects.filter(project_name=value))
            return BaseResponse.error(message="Project with this name already exists")
        return value


class ListTemplatesSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()

    class Meta:
        model = Template
        fields = "__all__"


class ListPortfolioProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    customized_template_id = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioProject
        fields = "__all__"

    def get_customized_template_id(self, obj):
        try:
            print(obj)
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


class CustomizedTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomizedTemplate
        fields = "__all__"


class TemplateDataSerializer(serializers.ModelSerializer):
    cloudfront_domain = serializers.SerializerMethodField()
    portfolio_project = ListPortfolioProjectSerializer()
    is_deployed = serializers.SerializerMethodField()

    class Meta:
        model = CustomizedTemplate
        fields = "__all__"

    def get_cloudfront_domain(self, obj):
        return get_cloudfront_domain(
            os.environ.get("PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID")
        )

    def get_is_deployed(self, obj):
        return obj.portfolio_project.is_deployed


class PortfolioContactEmailSerializer(serializers.Serializer):
    portfolio_contact_configured_email = serializers.EmailField(required=True)
    is_verified_portfolio_contact_email = serializers.BooleanField(default=False)

    def validate_portfolio_contact_configured_email(self, value):
        if not value:
            raise serializers.ValidationError("Please provide email address.")
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Invalid email address.")
        return value  # Return the valid email if no exception
