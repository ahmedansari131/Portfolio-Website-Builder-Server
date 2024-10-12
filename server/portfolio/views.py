from rest_framework.permissions import IsAuthenticated, IsAdminUser
from server.response.api_response import ApiResponse
from rest_framework.views import APIView
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from bs4 import BeautifulSoup
from server.utils.s3 import (
    s3_config,
    get_cloudfront_domain,
    download_assests,
    s3_name_format,
)
import json
from .serializers import (
    CreateProjectSerializer,
    ListTemplatesSerializer,
    TemplateDataSerializer,
    ListPortfolioProjectSerializer,
    CustomizedTemplateSerializer,
)
from .models import PortfolioProject, CustomizedTemplate, Template
from django.shortcuts import get_object_or_404
from server.utils.response import BaseResponse
from django.db import transaction
import os
from django.conf import settings
import mimetypes
from django.http import Http404
from .utils import generate_random_number, upload_image_on_s3_project
import boto3
import re


class Project(APIView):
    permission_classes = [IsAuthenticated]

    def get_section(self, template_data):
        sections = []
        for elem in template_data["body"][0]["children"]:
            if elem["tag"] == "section":
                sections.append({elem["tag"]: elem["attributes"]["id"]})
        return sections

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
                    sections = self.get_section(template_data)

                    try:
                        with transaction.atomic():

                            project_instance = PortfolioProject.objects.create(
                                project_name=serializer.validated_data.get(
                                    "project_name"
                                ),
                                created_by=request.user,
                                pre_built_template=template,
                            )

                            customized_template_instance = (
                                CustomizedTemplate.objects.create(
                                    template=template,
                                    portfolio_project=project_instance,
                                    meta=template_data.get("meta"),
                                    links=template_data.get("links"),
                                    scripts=template_data.get("scripts"),
                                    body=template_data.get("body"),
                                    style=template_data.get("style"),
                                    css=template_data.get("css"),
                                    js=template_data.get("js"),
                                    sections=sections,
                                )
                            )

                            s3_client = s3_config()
                            bucket_name = settings.AWS_DEPLOYED_PORTFOLIO_BUCKET_NAME
                            s3_formatted_project_name = s3_name_format(
                                project_instance.project_name
                            )
                            project_folder_name = (
                                s3_formatted_project_name + "/assests/"
                            )
                            s3_client.put_object(
                                Bucket=bucket_name, Key=project_folder_name
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

        if (
            not elem.name == "meta"
            and not elem.name == "link"
            and not elem.name == "title"
            and not elem.name == "style"
            and not elem.name == "script"
        ):
            elem = self.assign_class_name(elem)

        if elem.name == "img":
            elem = self.assign_unique_id(elem)

        dom_tree = {
            "tag": elem.name,
            "attributes": elem.attrs if elem.attrs else {},
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

    def assign_class_name(self, elem):
        if elem:
            # Check if the element has a "class" attribute
            if elem.has_attr("class"):
                # Append the new class to the list of existing classes
                elem["class"].append(
                    "portify-class-" + generate_random_number(digits=8)
                )
            else:
                # Set a new class if none exists
                elem["class"] = ["portify-class-" + generate_random_number(digits=8)]
            return elem

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

                # If image is coming from some online sources -> copying to the s3
                if "https" in src:
                    download_assests(
                        assest_url=src,
                        s3_template_name=s3_folder_name,
                        assest_name=img.get("data-assest-id"),
                    )
                    img["src"] = (
                        f'https://{cloudfront_domain}/{s3_folder_name}/assests/{img.get("data-assest-id")}'
                    )

                # If image is stored in local -> copying to the s3
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

    def create_separate_universal_style(self, template_path):
        # Read the existing CSS file
        template_style_path = os.path.join(template_path, "css", "style.css")
        with open(template_style_path, "r") as file:
            css_content = file.read()

        # Extract body styles using regex
        universal_styles = re.findall(r"\*\s*{(.*?)\}", css_content, re.DOTALL)
        body_styles = re.findall(r"body\s*{(.*?)\}", css_content, re.DOTALL)

        # Create a new CSS file for body styles
        output_body_file_name = "body-styles.css"
        output_body_style_path = os.path.join(
            template_path, "css", output_body_file_name
        )
        if body_styles:
            with open(output_body_style_path, "w") as body_file:
                # Write universal styles if found
                if universal_styles:
                    body_file.write(f"* {{\n{universal_styles[0].strip()}\n}}\n\n")

                # Write body styles if found
                if body_styles:
                    body_file.write(f"body {{\n{body_styles[0].strip()}\n}}")

        # Remove the extracted styles from the original CSS content
        updated_css_content = css_content
        if universal_styles:
            updated_css_content = re.sub(
                r"\*\s*{.*?}\s*", "", updated_css_content, flags=re.DOTALL
            )

        if body_styles:
            updated_css_content = re.sub(
                r"body\s*{.*?}\s*", "", updated_css_content, flags=re.DOTALL
            )

        # Write the updated CSS back to style.css
        with open(template_style_path, "w") as file:
            file.write(updated_css_content)

        index_file_path = os.path.join(template_path, "index.html")
        style_path = f"css/{output_body_file_name}"
        self.append_universal_style_link(index_file_path, style_path)

    def append_universal_style_link(self, index_file_path, style_path):
        try:
            # Read the index file content
            with open(index_file_path, "r") as index_file:
                html_content = index_file.read()

            # Parse the HTML content
            soup = BeautifulSoup(html_content, "html.parser")
            print(soup.prettify())

            # Create a new <link> tag for the stylesheet
            new_tag = soup.new_tag("link", rel="stylesheet", href=style_path)

            # Append the new tag to the <head> section
            head = soup.head
            if head is not None:
                head.append(new_tag)
            else:
                print("No <head> tag found in the HTML document.")

            # Write the modified content back to the index file
            with open(index_file_path, "w") as index_file:
                index_file.write(str(soup))

        except Exception as error:
            print("Error occurred while writing the index file:", error)

    def post(self, request, template_name):
        if template_name:
            template_name = s3_name_format(template_name)
            local_folder_path = os.path.join(settings.TEMPLATES_BASE_DIR, template_name)
            s3_client = s3_config()
            bucket_name = settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME
            s3_folder_key = f"{template_name}/"

            self.create_separate_universal_style(local_folder_path)

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


class ListPortfolioProject(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user:
            return ApiResponse.response_failed(
                message="You are not authenticated. Please signin first!", status=401
            )

        try:
            projects = PortfolioProject.objects.filter(
                created_by=user, is_deleted=False
            )
            if not projects:
                return ApiResponse.response_failed(
                    message="No project found", status=404
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        customized_template_id = data.get("customized_template_id", None)
        customized_template_body = data.get("body", None)
        customized_template_style = data.get("style", None)

        try:
            customized_template = CustomizedTemplate.objects.get(
                id=customized_template_id
            )

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
                success=False, message="No project found", status=404
            )

        return ApiResponse.response_succeed(
            status=200, message="Success saving", success=True
        )


class UpdateProjectImage(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        image = request.FILES.get("image_path", None)
        project_name = data.get("project_name", None)
        new_image_name = data.get("new_image_name", None)
        content_type = data.get("type", None)

        if not image and not project_name and not new_image_name:
            return ApiResponse.response_failed(
                message="Data related to image is not provided",
                status=404,
                success=False,
            )

        uploaded = upload_image_on_s3_project(
            image=image,
            project_folder_name=s3_name_format(project_name),
            new_image_name=new_image_name,
            content_type=content_type,
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
    permission_classes = [IsAuthenticated]

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
            cloudfront_domain = get_cloudfront_domain(
                distribution_id=os.environ.get(
                    "DEPLOYED_SITE_CLOUDFRONT_DISTRIBUION_ID"
                )
            )
            print(project_name)
            deployed_url = f"{cloudfront_domain}/{project_name}/index.html"
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
    permission_classes = [IsAuthenticated]

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
            project_instance = PortfolioProject.objects.get(id=project_id)

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
                message="Error occurred on server", status=500, success=False
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
