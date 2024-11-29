import os
from server.utils.s3 import get_cloudfront_domain, S3CLientSingleton, s3_name_format
from portfolio.constants import (
    S3_ASSETS_FOLDER_NAME,
    S3_CSS_FOLDER_NAME,
    S3_JS_FOLDER_NAME,
    INDEX_FILE,
    TEMPLATE_PREVIEW_IMAGE,
    EMAIL_JS_FILE,
)
from portfolio.exceptions.exceptions import TemplateRetrievalError, GeneralError
from django.conf import settings
import mimetypes
from portfolio.dom_manipulation.handle_dom import build_html_using_json


class S3_Template:

    def __init__(self, bucket_name, template_name):
        self.s3_client = S3CLientSingleton.get_instance()
        self.template_cloudfront_domain = get_cloudfront_domain(
            os.environ.get("PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID")
        )
        self.deployed_cloudfront_domain = get_cloudfront_domain(
            os.environ.get("DEPLOYED_SITE_CLOUDFRONT_DISTRIBUION_ID")
        )
        self.domain_name = os.environ.get("DOMAIN_NAME")
        self.bucket_name = bucket_name
        self.template_name = template_name
        self.local_template_path = settings.TEMPLATES_BASE_DIR
        self.dom_tree = []

    def get_static_content_from_s3(self):
        css_file_key = f"{self.template_name}/{S3_CSS_FOLDER_NAME}"
        js_file_key = f"{self.template_name}/{S3_JS_FOLDER_NAME}"

        try:
            css_response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=css_file_key
            )
            js_response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=js_file_key
            )
        except Exception as error:
            print(
                "Error occurred on s3 while retrieving the tempalate content from s3 bucket -> ",
                error,
            )
            raise TemplateRetrievalError(
                f"Some files are missing",
            )

        # Retrieving the static content from the s3 response
        css = [obj["Key"] for obj in css_response.get("Contents", [])]
        js = [obj["Key"] for obj in js_response.get("Contents", [])]

        return {"css_path": css, "js_path": js}

    def get_dom_elements_data(self):
        dom_tree = self.dom_tree
        s3_template_static_data = self.get_static_content_from_s3()
        css_path, js_path = s3_template_static_data.values()

        if dom_tree:
            keys = ["title", "meta", "link", "script", "style", "body"]
            elements = {key: dom_tree.get(key) or {} for key in keys}

            return {
                **elements,  # Unpack the elements dictionary
                "css": css_path,
                "js": js_path,
            }

        return {}

    def upload_template_on_s3(self):
        s3_folder_key = f"{self.template_name}/"

        try:
            # Creating folder on s3 named as per the template
            self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_folder_key)
        except Exception as error:
            print("Error occurred while creating the template folder on s3 -> ", error)
            raise GeneralError("Error occurred while creating the template on s3")

        local_folder_path = os.path.join(self.local_template_path, self.template_name)

        try:
            for root, _, files in os.walk(local_folder_path):
                # Don't upload .git folder and index file on s3
                if ".git" in root or INDEX_FILE in files:
                    continue

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

                    try:
                        with open(local_file_path, "rb") as file_data:
                            self.s3_client.upload_fileobj(
                                file_data,
                                self.bucket_name,
                                s3_key,
                                ExtraArgs={"ContentType": content_type},
                            )
                    except Exception as error:
                        print(
                            "Error occurred while reading or uploading the object -> ",
                            error,
                        )
                        raise GeneralError(
                            "Error occurred while uploading the content to storage"
                        )

        except Exception as error:
            print("Template is not present in the local directory -> ", error)
            raise GeneralError("Template is not present in the local directory")

        try:
            self.upload_index_file_to_s3()
        except Exception as error:
            print("Error occurred while uploading the html file on s3 -> ", error)
            raise GeneralError("Error occurred while uploading the html file")
        return

    def create_template_url(self):
        domain_name = os.environ.get("DOMAIN_NAME")

        if domain_name:
            template_url = f"https://{self.template_name}.templates.{domain_name}"
            template_preview_url = f"https://{self.template_name}.templates.{domain_name}/{S3_ASSETS_FOLDER_NAME}/{TEMPLATE_PREVIEW_IMAGE}"
        else:
            template_url = f"https://{self.template_cloudfront_domain}/{self.template_name}/{INDEX_FILE}"
            template_preview_url = f"https://{self.template_cloudfront_domain}/{self.template_name}/{S3_ASSETS_FOLDER_NAME}/{TEMPLATE_PREVIEW_IMAGE}"

        return {
            "template_url": template_url,
            "template_preview_url": template_preview_url,
        }

    def delete_template_from_s3(self):
        s3_folder_key = f"{self.template_name}/"

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=s3_folder_key
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name, Key=obj["Key"]
                    )
        except Exception as error:
            print("Error occurred while deleting from S3:", error)
            raise GeneralError("Error occurred while roll back")

    def upload_index_file_to_s3(self):
        s3_key = f"{self.template_name}/{INDEX_FILE}"
        html_data = build_html_using_json(template_name=self.template_name)
        html_content = html_data.get("html")
        self.dom_tree = html_data.get("html_json")

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=html_content.encode(
                    "utf-8"
                ),  # String encoding is mandatory for uploading
                ContentType="text/html",
            )
        except Exception as error:
            print("Error occurred while putting the index file on s3 -> ", error)
            raise GeneralError("Error occurred while uploading the html file on cloud")


class S3_Project:
    def __init__(self, bucket_name, project_name):
        self.s3_client = S3CLientSingleton.get_instance()
        self.bucket_name = bucket_name
        self.project_name = project_name

    def create_assests_on_s3(self):
        s3_formatted_project_name = s3_name_format(self.project_name)
        project_folder_name = s3_formatted_project_name + f"/{S3_ASSETS_FOLDER_NAME}/"
        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=project_folder_name)
        except Exception as error:
            print(
                f"Error occurred while creating the asset folder on s3 for project -> {self.project_name}",
                error,
            )
            raise GeneralError("Error occurred while creating the project assets")

    def configure_user_contact_form(self, user_email, template_name):
        s3_formatted_template_name = s3_name_format(template_name)
        s3_formatted_project_name = s3_name_format(self.project_name)
        
        TEMPLATE_JS_OBJECT_KEY = (
            f"{s3_formatted_template_name}/{S3_JS_FOLDER_NAME}/{EMAIL_JS_FILE}"
        )
        PROJECT_JS_OBJECT_KEY = (
            f"{s3_formatted_project_name}/{S3_JS_FOLDER_NAME}/{EMAIL_JS_FILE}"
        )

        response = self.s3_client.get_object(
            Bucket=settings.AWS_STORAGE_TEMPLATE_BUCKET_NAME, Key=TEMPLATE_JS_OBJECT_KEY
        )
        js_code = (
            response["Body"].read().decode("utf-8")
        )  # Read and decode the JS content

        # Step 2: Replace the placeholder with the actual email
        modified_js_code = js_code.replace("{{USER_EMAIL}}", user_email, 1)

        # Step 3: Upload the modified JS file back to S3
        self.s3_client.put_object(
            Bucket=settings.AWS_DEPLOYED_PORTFOLIO_BUCKET_NAME,
            Key=PROJECT_JS_OBJECT_KEY,
            Body=modified_js_code,
            ContentType="application/javascript",
        )
