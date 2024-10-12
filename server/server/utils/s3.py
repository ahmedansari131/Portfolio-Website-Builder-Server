import boto3
import os
from server.utils.response import BaseResponse
import requests
from django.conf import settings
import time


def s3_name_format(name):
    return name.replace(" ", "-").lower()


def s3_config():
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("S3_SECRET_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("S3_KEY_ID"),
            region_name=os.environ.get("S3_REGION_NAME"),
        )
    except Exception as error:
        return BaseResponse.error(
            message=f"Error occurred while connecting to S3 -> {str(error)}"
        )

    return s3


def get_cloudfront_domain(distribution_id):
    try:
        cloudfront_client = boto3.client(
            "cloudfront",
            aws_access_key_id=os.environ.get("S3_SECRET_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("S3_KEY_ID"),
            region_name=os.environ.get("S3_REGION_NAME"),
        )
        response = cloudfront_client.get_distribution(Id=distribution_id)
        domain_name = response["Distribution"]["DomainName"]
        return domain_name
    except Exception as e:
        print("Error occurred -> ", e)
        return None


def invalidate_cloudfront_cache(project_name, file_name):
    client = boto3.client(
        "cloudfront",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    distribution_id = os.environ.get("DEPLOYED_SITE_CLOUDFRONT_DISTRIBUION_ID")
    # Create invalidation for paths related to this version
    invalidation_response = client.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {
                "Quantity": 1,
                "Items": [f"/{project_name}/assets/{file_name}"],
            },
            "CallerReference": str(time.time()).replace(".", ""),
        },
    )
    return invalidation_response


def download_assests(assest_url, s3_template_name, assest_name):
    try:
        response = requests.get(assest_url)
        response.raise_for_status()
    except Exception as error:
        return str(error)

    content = response.content
    content_type = response.headers.get("Content-Type")

    bucket_name = os.environ.get("S3_TEMPLATE_BUCKET_NAME")
    s3_file_path = f"{s3_template_name}/assests/{assest_name}"

    try:
        s3_client = s3_config()
        response = s3_client.put_object(
            Bucket=bucket_name, Key=s3_file_path, Body=content, ContentType=content_type
        )
        return True
    except Exception as error:
        return str(error)
