from rest_framework.permissions import IsAuthenticated, IsAdminUser
from server.response.api_response import ApiResponse
from rest_framework.views import APIView
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from bs4 import BeautifulSoup
from server.utils.s3 import s3_config, get_cloudfront_domain
import json
from .serializers import (
    CreateProjectSerializer,
    ListTemplatesSerializer,
    TemplateDataSerializer,
)
from .models import PortfolioProject, CustomizedTemplate, Template
from django.shortcuts import get_object_or_404
from server.utils.response import BaseResponse
from django.db import transaction
import os
from django.conf import settings
import mimetypes
from django.http import Http404
from .utils import generate_random_number, download_assests


class Project(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        try:
            serializer = CreateProjectSerializer(data=data)
            if serializer.is_valid(raise_exception=True):
                project_name = serializer.validated_data.get("project_name")
                template_key = serializer.validated_data.get("template_name")

                if not isinstance(project_name, str) and project_name.get("error"):
                    return ApiResponse.response_failed(
                        message=project_name.get("message"), status=400
                    )

                template = get_object_or_404(
                    Template,
                    template_name=template_key,
                )

                template_serializer = ListTemplatesSerializer(template)
                template_data = template_serializer.data.get("template_dom_tree")

                if template_data:
                    try:
                        with transaction.atomic():
                            project_instance = PortfolioProject.objects.create(
                                project_name=serializer.validated_data.get(
                                    "project_name"
                                ),
                                created_by=request.user,
                                pre_built_template = template
                            )
                            # project_instance.pre_built_template.add(template)

                            customized_template_instance = (
                                CustomizedTemplate.objects.create(
                                    template=template,
                                    portfolio_project=project_instance,
                                    title=template_data.get("title"),
                                    meta=template_data.get("meta"),
                                    links=template_data.get("links"),
                                    scripts=template_data.get("scripts"),
                                    body=template_data.get("body"),
                                    style=template_data.get("style"),
                                    css=template_data.get("css"),
                                    js=template_data.get("js"),
                                )
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
                    data={"customized_template_id": customized_template_instance.id},
                )

        except Exception as error:
            return ApiResponse.response_failed(
                message=f"Error occurred while creating project! Please try again {str(error)}",
                status=500,
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

    def build_dom_tree(self, elem):
        if not elem:
            return None

        if elem.name == "img":
            elem = self.assign_unique_id(elem)

        dom_tree = {
            "tag": elem.name,
            "attributes": elem.attrs,
            "text": elem.string.strip() if elem.string else "",
            "children": [],
        }

        for child in elem.contents:
            if isinstance(child, str):
                if dom_tree["text"] == "":
                    dom_tree["text"] += child.strip()
            elif child.name is not None:
                dom_tree["children"].append(self.build_dom_tree(child))
        return dom_tree

    def assign_unique_id(self, elem):
        if elem:
            elem["data-assest-id"] = generate_random_number(digits=8)
            return elem

    def extract_element(self, dom, tag_name):
        tag = dom.find_all(tag_name)
        if tag:
            return tag
        else:
            return ""

    def handle_anchor(self, anchor_tags, s3_folder_name, bucket_name, s3_client):
        if anchor_tags:
            if isinstance(s3_client, str):
                return BaseResponse.error(message=s3_client.get("message"))

            cloudfront_domain = get_cloudfront_domain(
                os.environ.get("PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID")
            )

            for a in anchor_tags:
                if a.get("download"):
                    href = a.get("href")
                    a = self.assign_unique_id(a)
                    s3_client.copy_object(
                        Bucket=bucket_name,
                        CopySource={
                            "Bucket": bucket_name,
                            "Key": f'{s3_folder_name}/assests/{href.split("/")[-1]}',  # Old key
                        },
                        Key=f'{s3_folder_name}/assests/{a.get("data-assest-id")}',  # New key
                    )
                    a["href"] = (
                        f'https://{cloudfront_domain}/{s3_folder_name}/assests/{a.get("data-assest-id")}'
                    )
            return True
        else:
            return BaseResponse.error(message="Some error occurred")

    def handle_image_source(self, img_tags, s3_folder_name, bucket_name, s3_client):
        if img_tags:
            if isinstance(s3_client, str):
                return BaseResponse.error(message=s3_client.get("message"))

            cloudfront_domain = get_cloudfront_domain(
                os.environ.get("PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID")
            )

            for img in img_tags:
                src = img.get("src")
                if "https" in src:
                    download_assests(
                        assest_url=src,
                        s3_template_name=s3_folder_name,
                        assest_name=img.get("data-assest-id"),
                    )
                    img["src"] = (
                        f'https://{cloudfront_domain}/{s3_folder_name}/assests/{img.get("data-assest-id")}'
                    )

                if not "https" in src:
                    s3_client.copy_object(
                        Bucket=bucket_name,
                        CopySource={
                            "Bucket": bucket_name,
                            "Key": f'{s3_folder_name}/assests/{src.split("/")[-1]}',  # Old key
                        },
                        Key=f'{s3_folder_name}/assests/{img.get("data-assest-id")}',  # New key
                    )
                    img["src"] = (
                        f'https://{cloudfront_domain}/{s3_folder_name}/assests/{img.get("data-assest-id")}'
                    )
            return True
        else:
            return BaseResponse.error(message="Some error occurred")

    def get_template_from_s3(self, folder_name, file_name, bucket_name):
        bucket_name = bucket_name
        file_key = folder_name + "/" + file_name
        css_file_key = f"{folder_name}/css"
        js_file_key = f"{folder_name}/js"

        try:
            s3_client = s3_config()
            index_response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            css_response = s3_client.list_objects_v2(
                Bucket=bucket_name, Prefix=css_file_key
            )
            js_response = s3_client.list_objects_v2(
                Bucket=bucket_name, Prefix=js_file_key
            )
        except NoCredentialsError:
            return BaseResponse.error(message="Credentials not available")
        except PartialCredentialsError:
            return BaseResponse.error(message="Incomplete credentials")
        except s3_client.exceptions.NoSuchKey:
            return BaseResponse.error(message="File not found")
        except Exception as error:
            return BaseResponse.error(message=str(error))

        html_content = index_response["Body"].read().decode("utf-8")
        css = [obj["Key"] for obj in css_response.get("Contents", [])]
        js = [obj["Key"] for obj in js_response.get("Contents", [])]

        soup = BeautifulSoup(html_content, "html.parser")
        tags = ["meta", "link", "title", "style", "body", "script"]
        dom_tree_json = {}

        for tag in tags:
            elements = self.extract_element(soup, tag)
            if elements:
                if tag not in dom_tree_json:
                    dom_tree_json[tag] = []
                for element in elements:
                    dom_tree_json[tag].append(self.build_dom_tree(element))

        img_tags = soup.find_all("img")
        image_response = self.handle_image_source(
            img_tags=img_tags,
            s3_folder_name=folder_name,
            bucket_name=bucket_name,
            s3_client=s3_client,
        )
        if not image_response:
            return BaseResponse.error(message=image_response.get("message"))

        anchor_tags = soup.find_all("a")
        anchor_response = self.handle_anchor(
            anchor_tags=anchor_tags,
            s3_folder_name=folder_name,
            bucket_name=bucket_name,
            s3_client=s3_client,
        )
        if not anchor_response:
            return BaseResponse.error(message=anchor_response.get("message"))

        return {"dom_tree": dom_tree_json, "css": css, "js": js}

    def get_dom_elements_data(self, s3_folder_name, s3_file_name, bucket_name):
        s3_template_data = self.get_template_from_s3(
            s3_folder_name, s3_file_name, bucket_name
        )

        dom_tree = s3_template_data.get("dom_tree")
        css_path = s3_template_data.get("css")
        js_path = s3_template_data.get("js")
        if dom_tree:
            title = dom_tree.get("title") or {}
            meta = dom_tree.get("meta") or {}
            links = dom_tree.get("link") or {}
            scripts = dom_tree.get("script") or {}
            style = dom_tree.get("style") or {}
            body = dom_tree.get("body") or {}
            return {
                "title": title,
                "meta": meta,
                "links": links,
                "scripts": scripts,
                "style": style,
                "css": css_path,
                "js": js_path,
                "body": body,
            }
        return {}

    def post(self, request, template_name):
        if template_name:
            local_folder_path = os.path.join(settings.TEMPLATES_BASE_DIR, template_name)
            s3_client = s3_config()
            bucket_name = settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME
            s3_folder_key = f"{template_name}/"

            try:
                s3_client.put_object(Bucket=bucket_name, Key=s3_folder_key)

                for root, _, files in os.walk(local_folder_path):
                    for file_name in files:
                        local_file_path = os.path.join(root, file_name)
                        s3_key = s3_folder_key + os.path.relpath(
                            local_file_path, local_folder_path
                        )
                        s3_key = s3_key.replace(
                            "\\", "/"
                        )  # Ensure forward slashes in S3 key

                        content_type, _ = mimetypes.guess_type(local_file_path)
                        if not content_type:
                            content_type = "application/octet-stream"

                        with open(local_file_path, "rb") as file_data:
                            s3_client.upload_fileobj(
                                file_data,
                                bucket_name,
                                s3_key,
                                ExtraArgs={"ContentType": content_type},
                            )

                dom_elements_data = self.get_dom_elements_data(
                    s3_folder_name=template_name,
                    s3_file_name="index.html",
                    bucket_name=bucket_name,
                )

                if not dom_elements_data:
                    return ApiResponse.response_failed(
                        message="Error occurred while generating the template data",
                        status=500,
                    )

                cloudfront_domain = get_cloudfront_domain(
                    os.environ.get("PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID")
                )

                template_cloudfront_url = (
                    f"https://{cloudfront_domain}/{s3_folder_key}index.html"
                )
                template_preview_cloudfront_url = (
                    f"https://{cloudfront_domain}/{s3_folder_key}assests/preview.png"
                )

                Template.objects.create(
                    template_name=template_name,
                    template_url=template_cloudfront_url,
                    template_preview=template_preview_cloudfront_url,
                    template_dom_tree=dom_elements_data,
                    bucket_name=bucket_name,
                    cloudfront_domain=cloudfront_domain,
                    created_by=request.user,
                )

                return ApiResponse.response_succeed(
                    message="Template uploaded successfully",
                    status=201,
                )
            except Exception as error:
                return ApiResponse.response_failed(message=str(error), status=400)
        return ApiResponse.response_failed(
            message="Error occurred on server while uploading template", status=500
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
