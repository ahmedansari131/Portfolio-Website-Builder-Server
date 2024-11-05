from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .permissions import IsOwner
from server.response.api_response import ApiResponse
from rest_framework.views import APIView
from bs4 import BeautifulSoup
from server.utils.s3 import (
    s3_config,
    s3_name_format,
)
import json
from .serializers import (
    CreateProjectSerializer,
    ListTemplatesSerializer,
    TemplateDataSerializer,
    ListPortfolioProjectSerializer,
    CustomizedTemplateSerializer,
    PortfolioContactEmailSerializer,
)
from .models import PortfolioProject, CustomizedTemplate, Template
from django.shortcuts import get_object_or_404
from django.db import transaction
import os
from django.conf import settings
from django.http import Http404
from .utils import (
    upload_project_file_on_s3_project,
    get_object_or_404_with_permission,
)
import boto3
from server.email import BaseEmail
from portfolio.cloud_functions.s3 import S3_Template, S3_Project
from portfolio.exceptions.exceptions import GeneralError, DataNotPresent
from portfolio.dom_manipulation.handle_dom import parse_dom_tree
from server.renderers import CustomJSONRenderer


class Project(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [CustomJSONRenderer]

    def get_section(self, template_data):
        sections = []
        for elem in template_data["body"][0]["children"]:
            if elem["tag"] == "section":
                sections.append({elem["tag"]: elem["attributes"]["id"]})
        return sections

    def post(self, request):
        data = request.data
        serializer = CreateProjectSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            project_name = serializer.validated_data.get("project_name")
            template_name = serializer.validated_data.get("template_name")

            template_instance = get_object_or_404(
                Template,
                template_name=template_name,
            )

            template_data = template_instance.template_dom_tree
            html_body = template_data.get("body")[0]
            parsed_html_body_children = parse_dom_tree(html_body).get("children")[0]

            if template_data and parsed_html_body_children:
                sections = self.get_section(template_data)

                try:
                    with transaction.atomic():
                        project_instance = PortfolioProject.objects.create(
                            project_name=serializer.validated_data.get("project_name"),
                            created_by=request.user,
                            pre_built_template=template_instance,
                            portfolio_contact_configured_email=request.user.email,
                        )
                        customized_template_instance = (
                            CustomizedTemplate.objects.create(
                                template=template_instance,
                                portfolio_project=project_instance,
                                meta=template_data.get("meta"),
                                links=template_data.get("link"),
                                scripts=template_data.get("script"),
                                body=parsed_html_body_children,
                                style=template_data.get("style"),
                                css=template_data.get("css"),
                                js=template_data.get("js"),
                                sections=sections,
                            )
                        )

                    bucket_name = settings.AWS_DEPLOYED_PORTFOLIO_BUCKET_NAME
                    project_name = project_instance.project_name
                    s3_project_instance = S3_Project(
                        bucket_name=bucket_name, project_name=project_name
                    )
                    s3_project_instance.create_assests_on_s3()
                    s3_project_instance.configure_user_contact_form(
                        user_email=request.user.email,
                        template_name=customized_template_instance.template.template_name,
                    )
                except GeneralError as error:
                    return ApiResponse.response_failed(
                        message=str(error), status=500, success=False
                    )
                except Exception as error:
                    print(
                        "This transaction cannot occurred due to an error -> ",
                        error,
                    )
                    return ApiResponse.response_failed(
                        message=f"Error occurred while creating project! Please try again or contact at support@portify.com {str(error)}",
                        status=500,
                    )
            return ApiResponse.response_succeed(
                message="Project created",
                status=201,
                data={
                    "customized_template_id": customized_template_instance.id,
                    "project_name": customized_template_instance.portfolio_project.project_name,
                },
            )

        return ApiResponse.response_failed(
            message="Error occurred on server", status=500
        )

    def get(self, request, custom_template_id, portfolio_project_id):
        if not custom_template_id:
            return ApiResponse.response_failed(
                message="Template id is not provided", status=400
            )

        try:
            custom_template = get_object_or_404(
                CustomizedTemplate, id=custom_template_id
            )
            serializer = TemplateDataSerializer(custom_template)

            return ApiResponse.response_succeed(
                message="Template found", data=serializer.data, status=200
            )
        except Http404:
            return ApiResponse.response_failed(
                message=f"Template with this id {custom_template_id} does not exsit. Please try again!",
                status=404,
            )
        except Exception as error:
            return ApiResponse.response_failed(
                message=f"Error occurred while getting templates data -> {str(error)}",
                status=400,
            )


# TODO: If template is not found then it should give error, now it is saving
class UploadTemplate(APIView):
    permission_classes = [IsAdminUser]

    def check_template_presence(self, template_name):
        try:
            template_instance = Template.objects.get(template_name=template_name)
            return template_instance
        except Template.DoesNotExist:
            raise DataNotPresent(f"{template_name} is not present in db")
        except Exception as error:
            print(
                "Error occurred while checking the template availablility in db -> ",
                error,
            )
            raise GeneralError(
                f"Error occurred while processing the template {template_name}"
            )

    def post(self, request, template_name):
        if template_name:
            try:
                if self.check_template_presence(template_name=template_name):
                    return ApiResponse.response_failed(
                        message=f"Template with the name '{template_name}' is already exist.",
                        success=False,
                        status=400,
                    )
            except DataNotPresent:
                pass
            except Exception as error:
                return ApiResponse.response_failed(
                    message=str(error), success=False, status=500
                )

            template_name = s3_name_format(template_name)
            bucket_name = settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME

            try:
                aws_s3_object = S3_Template(
                    bucket_name=bucket_name, template_name=template_name
                )
                aws_s3_object.upload_template_on_s3()
                dom_elements_data = aws_s3_object.get_dom_elements_data()

                if not dom_elements_data:
                    return ApiResponse.response_failed(
                        message="Error occurred while generating the template data",
                        status=500,
                    )

                template_url, template_preview_url = (
                    aws_s3_object.create_template_url().values()
                )

                Template.objects.create(
                    template_name=template_name,
                    template_url=template_url,
                    template_preview=template_preview_url,
                    template_dom_tree=dom_elements_data,
                    bucket_name=bucket_name,
                    cloudfront_domain=aws_s3_object.template_cloudfront_domain,
                    created_by=request.user,
                )

                return ApiResponse.response_succeed(
                    message="Template uploaded successfully",
                    status=201,
                )
            except DataNotPresent as error:
                return ApiResponse.response_failed(
                    message=str(error), status=400, success=False
                )
            except GeneralError as error:
                aws_s3_object.delete_template_from_s3()
                return ApiResponse.response_failed(
                    message=str(error), status=500, success=False
                )
            except Exception as error:
                aws_s3_object.delete_template_from_s3()
                print(
                    "Error occurred on server while uploading the template -> ", error
                )
                return ApiResponse.response_failed(
                    message="Error occurred on server while uploading the template",
                    status=500,
                    success=False,
                )
        return ApiResponse.response_failed(
            message="Error occurred on server while uploading template",
            status=500,
            success=False,
        )


class ListTemplates(APIView):
    def get(self, request):
        try:
            templates = Template.objects.all()
            serializer = ListTemplatesSerializer(templates, many=True)
            return ApiResponse.response_succeed(data=serializer.data, status=200)
        except Exception as error:
            print("Error occur while getting the template", error)
            return ApiResponse.response_failed(
                message="Error occurred on the server! Please try again or contact at support@portfiy.com",
                status=500,
            )


class ListPortfolioProject(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            projects = PortfolioProject.objects.filter(created_by=request.user)
            if not projects:
                return ApiResponse.response_failed(
                    message="No project found", status=404, success=False
                )
            serializer = ListPortfolioProjectSerializer(projects, many=True)
            return ApiResponse.response_succeed(
                message="Project found", data=serializer.data, status=200
            )

        except Exception as error:
            return ApiResponse.response_failed(
                message=f"Error occurred while getting the projects {str(error)}",
                status=500,
            )


class UpdateCustomizeTemplate(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, pk):
        try:
            customized_template_instance = CustomizedTemplate.objects.get(id=pk)
            self.check_object_permissions(
                self.request, customized_template_instance.portfolio_project
            )
            return customized_template_instance
        except CustomizedTemplate.DoesNotExist:
            return None

    def post(self, request):
        data = request.data
        customized_template_id = data.get("customized_template_id", None)
        customized_template_body = data.get("body", None)
        customized_template_style = data.get("style", None)

        if not customized_template_id:
            return ApiResponse.response_failed(
                message="Custom template id is not found", success=False, status=404
            )

        try:
            customized_template = self.get_object(pk=customized_template_id)

            if not customized_template:
                return ApiResponse.response_failed(
                    status=404, message="Project not found", success=False
                )

            if customized_template_style:
                customized_template.style = customized_template_style

            if customized_template_body:
                customized_template.body = customized_template_body

            customized_template.save()

        except Exception as error:
            print("Error occurred -> ", error)
            return ApiResponse.response_failed(
                success=False, message=str(error), status=404
            )

        return ApiResponse.response_succeed(
            status=200, message="Success saving", success=True
        )


class UpdateProjectImageOrDocument(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request):
        data = request.data
        file = request.FILES.get("file_path", None)
        project_name = data.get("project_name", None)
        new_file_name = data.get("new_file_name", None)
        project_id = data.get("project_id", None)

        if not file and not project_name and not new_file_name:
            return ApiResponse.response_failed(
                message="Data related to image is not provided",
                status=404,
                success=False,
            )

        try:
            project_instance = get_object_or_404_with_permission(
                self, PortfolioProject.objects, project_id
            )
        except PortfolioProject.DoesNotExist:
            return ApiResponse.response_failed(
                message="No project found. Please refresh and create one to proceed further!",
                success=False,
                status=404,
            )
        except Exception as error:
            return ApiResponse.response_failed(
                message=str(error),
                success=False,
                status=500,
            )

        uploaded = upload_project_file_on_s3_project(
            file=file,
            project_folder_name=s3_name_format(project_name),
            new_file_name=new_file_name,
        )

        if uploaded.get("error"):
            return ApiResponse.response_failed(
                message=uploaded.get("message"), status=500, success=False
            )

        return ApiResponse.response_succeed(
            message="Image uploaded successfully",
            status=200,
            success=True,
            data=uploaded,
        )


class Deployment(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def parse_element(self, elements, soup, parent=None):
        top_level_elements = []
        for element in elements:
            tag_name = element.get("tag").lower()
            new_tag = soup.new_tag(tag_name)

            if "attributes" in element and len(element.get("attributes")):
                for attr, value in element.get("attributes").items():
                    if isinstance(value, list):
                        new_tag[attr] = " ".join(value)  # Join classes with space
                    else:
                        new_tag[attr] = value
            if "text" in element and element.get("text"):
                new_tag.string = element.get("text")

            if "children" in element and element.get("children"):
                self.parse_element(element.get("children"), soup, new_tag)

            if parent:
                parent.append(new_tag)
            else:
                top_level_elements.append(new_tag)

        if parent is None:
            return top_level_elements

        return parent

    def parse_meta(self, meta_data, soup, description):
        for element in meta_data:
            tag_name = element.get("tag")
            attributes = element.get("attributes", {})

            # Extract the "name" attribute separately to avoid conflicts
            name_attr = attributes.pop("name", None)

            # Create a new tag
            new_tag = soup.new_tag(tag_name, **attributes)

            # If there was a "name" attribute, set it manually
            if name_attr:
                new_tag["name"] = name_attr

            # Add text if present
            if element.get("text"):
                new_tag.string = element["text"]

            # Append the tag to the soup
            soup.append(new_tag)

        new_tag = soup.new_tag(
            "meta", attrs={"name": "description", "content": description}
        )
        soup.append(new_tag)
        return soup

    def build_html(self, meta, body, links, script, title, description):
        soup = BeautifulSoup("", "html.parser")
        html = soup.new_tag("html")
        head = soup.new_tag("head")
        document_title = soup.new_tag("title")
        document_title.string = title

        html.append(self.parse_meta(meta, soup, description))
        head.append(document_title)
        html_links = self.parse_element(links, soup)
        for link in html_links:
            head.append(link)
        html.append(head)
        html.append(self.parse_element(body, soup)[0])
        return html

    def convert_json_to_css(self, css_json):
        css_rules = []
        print("json", css_json)
        # Iterate over the JSON object to convert it to CSS format
        for class_name, properties in css_json.items():
            css_rule = f".{class_name} {{\n"
            for prop in properties:
                if prop.get("value"):
                    property_name = prop.get("property")
                    property_value = f"{prop.get('value')}"
                    css_rule += (
                        f"  {property_name}: {property_value.lower()} !important;\n"
                    )
            css_rule += "}"
            css_rules.append(css_rule)

        return "\n".join(css_rules)

    def extract_template_css(self, s3_client, template_name):
        try:
            css_response = {}
            cssData = [
                {"file": "style.css"},
                {"file": "responsive.css"},
                {"file": "body-styles.css"},
            ]

            for data in cssData:
                response = s3_client.get_object(
                    Bucket=settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME,
                    Key=f'{template_name}/css/{data["file"]}',
                )
                css = response["Body"].read().decode("utf-8")
                if data["file"] == "style.css":
                    css_response["template_css"] = css
                elif data["file"] == "responsive.css":
                    css_response["template_responsive_css"] = css
                elif data["file"] == "body-styles.css":
                    css_response["template_body_css"] = css

            return css_response

        except Exception as error:
            print("Error occurred while getting the css from the template ->", error)
            return False

    def extract_template_js(self, s3_client, template_name):
        try:
            js_response = {}
            js_data = [{"file": "script.js"}]

            for data in js_data:
                response = s3_client.get_object(
                    Bucket=settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME,
                    Key=f'{template_name}/js/{data["file"]}',
                )
                js = response["Body"].read().decode("utf-8")
                js_response["template_js"] = js

            return js_response

        except Exception as error:
            print("Error occurred while getting the js from the template ->", error)
            return False

    def post(self, request):
        data = request.data
        custom_template_id = data.get("customized_template_id")
        project_name = str(data.get("project_name"))
        title = request.data.get("title")
        description = request.data.get("description")

        try:
            portfolio_project_instance = get_object_or_404_with_permission(
                view=self, queryset=PortfolioProject.objects, pk=custom_template_id
            )
            if portfolio_project_instance:
                customized_template_instance = CustomizedTemplate.objects.get(
                    id=custom_template_id
                )
            serializer = CustomizedTemplateSerializer(customized_template_instance)
        except CustomizedTemplate.DoesNotExist:
            print("Custom template with the given id does not exist.")
            return ApiResponse.response_failed(
                message="Your customized portfolio template not found.",
                status=500,
                success=False,
            )
        except Exception as error:
            print("Error occurred on server", error)
            return ApiResponse.response_failed(
                message="Error occurred on server", status=500, success=False
            )

        meta_data = serializer.data.get("meta")
        body = serializer.data.get("body")
        links = serializer.data.get("links")
        style = serializer.data.get("style")
        script = serializer.data.get("scripts")
        template_name = customized_template_instance.template.template_name

        if not title and not description:
            title = customized_template_instance.portfolio_project.portfolio_title
            description = (
                customized_template_instance.portfolio_project.portfolio_description
            )

        html = self.build_html(
            meta=meta_data,
            body=body,
            links=links,
            script=script,
            title=title,
            description=description,
        )

        if isinstance(style, dict):
            custom_css = ""
        else:
            custom_css = self.convert_json_to_css(style[0])

        s3_client = s3_config()

        css_response = self.extract_template_css(
            s3_client=s3_client, template_name=template_name
        )

        js_response = self.extract_template_js(
            s3_client=s3_client, template_name=template_name
        )
        merged_css = css_response["template_css"] + "\n" + custom_css

        bucket_name = settings.AWS_DEPLOYED_PORTFOLIO_BUCKET_NAME
        project_name = s3_name_format(project_name)
        content_to_upload = [
            {
                "file_name": "index.html",
                "content_type": "text/html",
                "file_content": str(html),
            },
            {
                "file_name": "css/style.css",
                "content_type": "text/css",
                "file_content": str(merged_css),
            },
            {
                "file_name": "css/responsive.css",
                "content_type": "text/css",
                "file_content": str(css_response["template_responsive_css"]),
            },
            {
                "file_name": "css/body-styles.css",
                "content_type": "text/css",
                "file_content": str(css_response["template_body_css"]),
            },
            {
                "file_name": "js/script.js",
                "content_type": "application/javascript",
                "file_content": str(js_response["template_js"]),
            },
        ]

        try:
            for content in content_to_upload:
                s3_client.put_object(
                    Body=str(content["file_content"]),
                    Bucket=bucket_name,
                    Key=f'{project_name}/{content["file_name"]}',
                    ContentType=content["content_type"],
                )
        except Exception as error:
            print("Error occurred on server while deploying project to s3 -> ", error)
            return ApiResponse.response_failed(
                success=False, message="Error occurred on server", status=500
            )

        try:
            domain_name = os.environ.get("DOMAIN_NAME")
            deployed_url = f"{portfolio_project_instance.project_slug}.{domain_name}"
        except Exception as error:
            print("Error occurred while building cloudfront url -> ", error)
            return ApiResponse.response_failed(
                message="Error occurred on server while deploying the site",
                status=500,
                success=False,
            )

        try:
            customized_template_instance.portfolio_project.deployed_url = deployed_url
            customized_template_instance.portfolio_project.is_deployed = True
            customized_template_instance.portfolio_project.portfolio_title = title
            customized_template_instance.portfolio_project.portfolio_description = title
            customized_template_instance.portfolio_project.portfolio_description = (
                description
            )
            customized_template_instance.portfolio_project.save()
        except Exception as error:
            print(
                "Error occurred while updating portfolio project for deployment -> ",
                error,
            )
            return ApiResponse.response_failed(
                message="Error occurred on server", success=False, status=500
            )

        return ApiResponse.response_succeed(
            status=200,
            message="Portfolio deployed",
            success=True,
            data={"deployed_url": deployed_url},
        )

    def get(self, request):
        user = request.user

        try:
            deployed_project_instance = PortfolioProject.objects.filter(
                created_by=user, is_deployed=True
            )

            if not deployed_project_instance:
                return ApiResponse.response_failed(
                    message="No deployed project found.", success=False, status=404
                )

            serializer = ListPortfolioProjectSerializer(
                deployed_project_instance, many=True
            )
        except Exception as error:
            print("Error occurred while getting the deployed projects -> ", error)
            return ApiResponse.response_failed(
                message="Error occurred on server while getting the deployed projects",
                status=500,
                success=False,
            )

        return ApiResponse.response_succeed(
            message="Deployed projects found.",
            success=True,
            status=200,
            data=serializer.data,
        )


class DeletePortfolioProject(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request, project_id):
        delete = request.GET.get("delete", "false").lower()
        delete_flag = delete == "true"

        if not project_id:
            return ApiResponse.response_failed(
                message="Project id is not found. Please try again!",
                success=False,
                status=404,
            )

        if delete is None:
            return ApiResponse.response_failed(
                message="Delete value is not provided. Please try again!",
                success=False,
                status=404,
            )

        try:
            project_instance = get_object_or_404_with_permission(
                view=self, queryset=PortfolioProject.objects, pk=project_id
            )
            if not project_instance:
                return ApiResponse.response_failed(
                    message="Project not found. Please check you have created one.",
                    success=False,
                    status=404,
                )

            if delete_flag:
                project_instance.is_deleted = True
            elif not delete_flag:
                project_instance.is_deleted = False

            project_instance.save()

        except PortfolioProject.DoesNotExist:
            print("Project does not exist")
            return ApiResponse.response_failed(
                message="Project not found. Please check you have created one.",
                success=False,
                status=404,
            )
        except Exception as error:
            print("Error occurred while deleting the project", error)
            return ApiResponse.response_failed(
                message=str(error), status=500, success=False
            )

        return ApiResponse.response_succeed(
            success=True, message="Project deleted successfully", status=200
        )


class PortfolioDomain(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        domain_name = request.data.get("domain_name") + "." + request.data.get("tld")
        print(domain_name)
        route53_client = boto3.client(
            "route53domains",
            aws_access_key_id=os.environ.get("53_SECRET_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("53_ACCESS_KEY"),
            region_name="us-east-1",
        )

        try:
            response = route53_client.check_domain_availability(DomainName=domain_name)
            is_available = response.get("Availability")
            print(response)
        except Exception as error:
            print("Error occurred while checking domain availability", error)
            return ApiResponse.response_failed(
                message="Error occurred on server while checking domain availability",
                status=500,
                success=False,
            )

        return ApiResponse.response_succeed(
            message="Domain is " + is_available,
            status=200,
            success=True,
        )


class PortfolioEmailSend(APIView):
    # TODO: NEED TO CONFIGURE JS IN TEMPLATE FOR STORING THE PROJECT ID AND UPDATING AN EMAIL
    def is_email_verified(self, email, project_id):
        try:
            portfolio_instance = PortfolioProject.objects.filter(
                id=project_id,
                portfolio_contact_configured_email=email,
                is_verified_portfolio_contact_email=True,
            )
            print(portfolio_instance, project_id, email)
            if portfolio_instance:
                return True
            else:
                return False
        except Exception as error:
            print("Error occurred on server", error)
            return False

    def post(self, request):
        user_email = request.data.get("user")
        contact_name = request.data.get("contact_name")
        contact_message = request.data.get("contact_message")
        contact_email = request.data.get("contact_email")
        project_id = request.data.get("project_id")

        if (
            not user_email
            and not contact_name
            and not contact_message
            and not contact_email
            and not project_id
        ):
            return ApiResponse.response_failed(
                message="Data is not provided", status=404, success=False
            )

        if not self.is_email_verified(email=user_email, project_id=project_id):
            return ApiResponse.response_failed(
                message="Email could not be sent.", success=False, status=401
            )

        try:
            user_contact_email = BaseEmail(
                sender=os.environ.get("PORTFOLIO_SENDER_EMAIL"),
                recipient=user_email,
                subject=f"New message from {contact_name}",
                message="New message",
                template_path="email_templates/portfolio_contact_email.html",
                content={
                    "message": contact_message,
                    "email": contact_email,
                    "name": contact_name,
                },
            )
            user_contact_email.send_email()
        except Exception as error:
            print("Error occurred while sending an email", error)
            return ApiResponse.response_failed(
                message="Error occurred while sending email", success=False, status=500
            )
        return ApiResponse.response_succeed(
            message="Email sent successfully", status=200, success=True
        )


class SendPortfolioContactEmailVerificationEmail(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request):
        project_id = request.data.get("project_id")

        try:
            project_instance = get_object_or_404_with_permission(
                self, PortfolioProject.objects, project_id
            )
        except PortfolioProject.DoesNotExist:
            return ApiResponse.response_failed(
                message="Project does not exist", status=404, success=False
            )

        serializer = PortfolioContactEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse.response_failed(
                message=serializer.errors, success=False, status=400
            )

        project_instance.portfolio_contact_configured_email = (
            serializer.validated_data.get("portfolio_contact_configured_email")
        )
        project_instance.save(update_fields=["portfolio_contact_configured_email"])
        return ApiResponse.response_succeed(
            message="A verification email is sent to your email address",
            status=200,
            success=True,
        )
