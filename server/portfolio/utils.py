import random
import string
from server.utils.s3 import (
    s3_config,
    get_cloudfront_domain,
    invalidate_cloudfront_cache,
)
from django.conf import settings
from server.utils.response import BaseResponse
import os
from botocore.exceptions import ClientError
from rest_framework.exceptions import NotFound, PermissionDenied
from django.shortcuts import get_object_or_404


def get_object_or_404_with_permission(view, queryset, pk):
    obj = get_object_or_404(queryset, pk=pk)
    view.check_object_permissions(view.request, obj)

    return obj


def generate_random_number(digits=6):
    characters = string.ascii_letters + string.digits

    random_string = "".join(random.choice(characters) for _ in range(digits))
    return random_string


def upload_image_on_s3_project(
    image, project_folder_name, new_image_name, content_type
):
    s3_client = s3_config()
    bucket_name = settings.AWS_DEPLOYED_PORTFOLIO_BUCKET_NAME

    file_extension = os.path.splitext(image.name)[1]  # Extracts .png, .jpg, etc.
    if not file_extension:
        file_extension = "." + image.content_type.split("/")[1]
    image_s3_path = f"{project_folder_name.replace(' ', '-').lower()}/assests/{new_image_name}{file_extension}"

    try:
        # Check if the object exists in S3
        s3_client.head_object(Bucket=bucket_name, Key=image_s3_path)
        # If it exists, delete it
        print(f"{image_s3_path} already exists. Deleting it.")
        s3_client.delete_object(Bucket=bucket_name, Key=image_s3_path)
    except ClientError as error:
        # Check if the error is because the object does not exist
        if error.response["Error"]["Code"] == "404":
            print(f"{image_s3_path} does not exist in S3. No need to delete.")
        else:
            print("Error occurred while checking if image already exists:", error)
            return BaseResponse.error(
                message="Error occurred while checking if image already exists"
            )
    except Exception as error:
        print("An unexpected error occurred:", error)
        return BaseResponse.error(
            message="An unexpected error occurred while checking the image."
        )

    try:
        s3_client.upload_fileobj(
            image,
            bucket_name,
            image_s3_path,
            ExtraArgs={"ContentType": image.content_type},
        )
        invalidate_cloudfront_cache(
            project_name=project_folder_name, file_name=new_image_name + file_extension
        )
        distribution_id = os.environ.get("DEPLOYED_SITE_CLOUDFRONT_DISTRIBUION_ID")
        url = f"https://{get_cloudfront_domain(distribution_id=distribution_id)}/{image_s3_path}"
        return {"image_s3_url": url}
    except Exception as error:
        print("Error occurred while uploading the project image on s3 -> ", error)
        return BaseResponse.error(
            message="Error occurred while uploading the project image on s3"
        )
