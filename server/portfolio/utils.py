import random
import string
from server.utils.s3 import s3_config, get_cloudfront_domain
from django.conf import settings
from server.utils.response import BaseResponse
import mimetypes
import os


def generate_random_number(digits=6):
    characters = string.ascii_letters + string.digits

    random_string = "".join(random.choice(characters) for _ in range(digits))
    return random_string


def upload_image_on_s3_project(image, project_folder_name, new_image_name):
    s3_client = s3_config()
    bucket_name = settings.AWS_DEPLOYED_PORTFOLIO_BUCKET_NAME

    # Assign new image name with the correct extension
    _, extension = mimetypes.guess_type(image)

    new_image_name_with_extension = f"{new_image_name}{extension or ''}"
    image_s3_path = f"{project_folder_name}/assests/{new_image_name_with_extension}"

    content_type, _ = mimetypes.guess_type(image)
    if not content_type:
        content_type = "application/octet-stream"
    try:
        with open(image, "rb") as image_file:
            # Upload the image to S3
            s3_client.put_object(
                Bucket=bucket_name,
                Key=image_s3_path,
                Body=image_file,  # Add the file body
                ContentType=content_type,  # Pass ContentType here
            )
        distribution_id = os.environ.get("DEPLOYED_SITE_CLOUDFRONT_DISTRIBUION_ID")
        url = (
            f"{get_cloudfront_domain(distribution_id=distribution_id)}/{image_s3_path}"
        )
        return {"image_s3_url": url}
    except Exception as error:
        print("Error occurred while uploading the project image on s3 -> ", error)
        return BaseResponse.error(
            message="Error occurred while uploading the project image on s3"
        )
