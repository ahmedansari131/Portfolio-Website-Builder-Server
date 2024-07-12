from rest_framework.permissions import IsAuthenticated
from server.response.api_response import ApiResponse
from rest_framework.views import APIView
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from bs4 import BeautifulSoup
from server.utils.s3 import s3_config
import json
from .serializers import CreateProjectSerializer
from .models import PortfolioProject, CustomizedTemplate, Template
from django.shortcuts import get_object_or_404
from server.utils.response import BaseResponse
from django.db import transaction



class Project(APIView):
    permission_classes = [IsAuthenticated]

    def extract_element(self, dom, tag_name):
        tag = dom.find_all(tag_name)
        if tag:
            return tag
        else:
            return ""

    def build_dom_tree(self, elem):
        if not elem:
            return None

        dom_tree = {
            "tag": elem.name,
            "attributes": elem.attrs,
            "text": elem.string.strip() if elem.string else "",
            "children": [],
        }

        for child in elem.children:
            if child.name is not None:
                dom_tree["children"].append(self.build_dom_tree(child))
        return dom_tree

    def get_template_from_s3(self, folder_name, file_name, bucket_name):
        bucket_name = bucket_name
        file_key = folder_name + "/" + file_name

        try:
            s3_client = s3_config()
            response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            html_content = response["Body"].read().decode("utf-8")

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
            return dom_tree_json

        except NoCredentialsError:
            return BaseResponse.error(message="Credentials not available")
        except PartialCredentialsError:
            return BaseResponse.error(message="Incomplete credentials")
        except s3_client.exceptions.NoSuchKey:
            return BaseResponse.error(message="File not found")
        except Exception as error:
            return BaseResponse.error(message=str(error))

    def get_dom_elements_data(self, s3_folder_name, s3_file_name, bucket_name):
        dom_tree = self.get_template_from_s3(s3_folder_name, s3_file_name, bucket_name)
        if dom_tree:
            title = dom_tree.get("title") or {}
            meta = dom_tree.get("meta") or {}
            links = dom_tree.get("link") or {}
            scripts = dom_tree.get("script") or {}
            style = dom_tree.get("style") or {}
            css = dom_tree.get("css") or {}
            js = dom_tree.get("js") or {}
            body = dom_tree.get("body") or {}
            return {
                "title": title,
                "meta": meta,
                "links": links,
                "scripts": scripts,
                "style": style,
                "css": css,
                "js": js,
                "body": body,
            }
        return {}

    def post(self, request):
        data = request.data

        try:
            serializer = CreateProjectSerializer(data=data)
            if serializer.is_valid(raise_exception=True):
                s3_file_name = serializer.validated_data.get("s3_file_name")
                s3_folder_name = serializer.validated_data.get("s3_folder_name")
                bucket_name = serializer.validated_data.get("bucket_name")

                template = get_object_or_404(
                    Template, id=serializer.validated_data.get("template_id")
                )

                elements_data = self.get_dom_elements_data(
                    s3_folder_name, s3_file_name, bucket_name
                )

                if elements_data:
                    try:
                        with transaction.atomic():
                            project_instance = PortfolioProject.objects.create(
                                project_name=serializer.validated_data.get(
                                    "project_name"
                                ),
                                created_by=request.user,
                            )

                            CustomizedTemplate.objects.create(
                                template=template,
                                portfolio_project=project_instance,
                                title=elements_data.get("title"),
                                meta=elements_data.get("meta"),
                                links=elements_data.get("links"),
                                scripts=elements_data.get("scripts"),
                                body=elements_data.get("body"),
                                style=elements_data.get("style"),
                                css=elements_data.get("css"),
                                js=elements_data.get("js"),
                            )
                    except Exception as error:
                        print(
                            "Error occurred while creating the portfolio objects -> ",
                            error,
                        )
                        return ApiResponse.response_failed(
                            message="Error occurred while creating project! Please try again or contact at support@portify.com",
                            status=500,
                        )
                return ApiResponse.response_succeed(
                    message="Project created",
                    status=201,
                    data={"project_id": project_instance.id},
                )

        except Exception as error:
            print("Error occurred while creating project -> ", error)
            return ApiResponse.response_failed(
                message="Error occurred while creating project! Please try again",
                status=500,
            )

        return ApiResponse.response_failed(
            message="Error occurred on server", status=500
        )
