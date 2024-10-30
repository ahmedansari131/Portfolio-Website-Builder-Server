import os
from server.utils.response import BaseResponse
from server.utils.s3 import get_cloudfront_domain, s3_config, download_assets
from portfolio.dom_manipulation.element_attr import assign_asset_id
from portfolio.constants import (
    ASSET_ID_PREFIX,
    S3_ASSETS_FOLDER_NAME,
    S3_CSS_FOLDER_NAME,
    S3_JS_FOLDER_NAME,
    INDEX_FILE,
    TEMPLATE_PREVIEW_IMAGE,
)
from portfolio.exceptions.exceptions import TemplateRetrievalError, GeneralError
from portfolio.dom_manipulation.handle_dom import parse_html_content
from django.conf import settings
import mimetypes


class AWS_S3_Service:

    def __init__(self, bucket_name, template_name):
        self.s3_client = s3_config()
        self.template_cloudfront_domain = get_cloudfront_domain(
            os.environ.get("PREBUILT_TEMPLATES_CLOUDFRONT_DISTRIBUION_ID")
        )
        self.deployed_cloudfront_domain = get_cloudfront_domain(
            os.environ.get("DEPLOYED_SITE_CLOUDFRONT_DISTRIBUION_ID")
        )
        self.domain_name = os.environ.get("DOMAIN_NAME")
        self.bucket_name = bucket_name
        self.template_name = template_name

    def handle_anchor_element(self, anchor_tags):
        if anchor_tags:
            for a in anchor_tags:

                # If download attribute is present in anchor, then it is asset
                if a.get("download"):
                    href = a.get("href")
                    a = assign_asset_id(a)
                    asset_name = a.get(ASSET_ID_PREFIX)
                    old_s3_asset_key = f'{self.template_name}/{S3_ASSETS_FOLDER_NAME}/{href.split("/")[-1]}'
                    new_s3_asset_key = (
                        f"{self.template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"
                    )

                    self.s3_client.copy_object(
                        Bucket=self.bucket_name,
                        CopySource={
                            "Bucket": self.bucket_name,
                            "Key": old_s3_asset_key,  # Old key
                        },
                        Key=new_s3_asset_key,  # New key
                    )

                    if self.domain_name:
                        anchor_path = f"{S3_ASSETS_FOLDER_NAME}/{asset_name}"
                    else:
                        anchor_path = f"https://{self.template_cloudfront_domain}/{self.template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"

                    a["href"] = anchor_path
            return True
        else:
            return BaseResponse.error(message="Some error occurred")

    def handle_image_source(self, img_tags):
        if img_tags:
            for img in img_tags:
                src = img.get("src")
                asset_name = img.get(ASSET_ID_PREFIX)

                # If image is coming from some online sources -> copying to the s3
                if "https" in src:
                    download_assets(
                        assest_url=src,
                        s3_template_name=self.template_name,
                        assest_name=asset_name,
                    )

                # If image is stored in local -> copying to the s3
                elif not "https" and not "http" in src:
                    old_s3_key = f'{self.template_name}/{S3_ASSETS_FOLDER_NAME}/{src.split("/")[-1]}'
                    new_s3_key = (
                        f"{self.template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"
                    )

                    self.s3_client.copy_object(
                        Bucket=self.bucket_name,
                        CopySource={
                            "Bucket": self.bucket_name,
                            "Key": old_s3_key,  # Old key
                        },
                        Key=new_s3_key,  # New key
                    )

                if self.domain_name:
                    img_path = f"{S3_ASSETS_FOLDER_NAME}/{asset_name}"
                else:
                    img_path = f"https://{self.template_cloudfront_domain}/{self.template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"
                img["src"] = img_path

            return True
        else:
            return BaseResponse.error(
                message="Some error occurred while handling images in s3"
            )

    def get_template_from_s3(self):
        index_file_key = f"{self.template_name}/index.html"
        css_file_key = f"{self.template_name}/{S3_CSS_FOLDER_NAME}"
        js_file_key = f"{self.template_name}/{S3_JS_FOLDER_NAME}"

        try:
            index_response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=index_file_key
            )
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

        dom_tree_json, css, js, img_tags, anchor_tags = parse_html_content(
            index_response, css_response, js_response
        )

        image_response = self.handle_image_source(
            img_tags=img_tags,
        )
        if not image_response:
            return BaseResponse.error(message=image_response.get("message"))

        anchor_response = self.handle_anchor_element(
            anchor_tags=anchor_tags,
        )
        if not anchor_response:
            return BaseResponse.error(message=anchor_response.get("message"))

        return {"dom_tree": dom_tree_json, "css_path": css, "js_path": js}

    def get_dom_elements_data(self):
        s3_template_data = self.get_template_from_s3()
        dom_tree, css_path, js_path = s3_template_data.values()

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
        local_folder_path = os.path.join(
            settings.TEMPLATES_BASE_DIR, self.template_name
        )

        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_folder_key)
        except Exception as error:
            print("Error occurred while creating the template folder on s3 -> ", error)
            raise GeneralError("Error occurred while creating the template on s3")

        try:
            for root, _, files in os.walk(local_folder_path):

                # Don't upload .git folder on s3
                if ".git" in root:
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
