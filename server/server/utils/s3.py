import boto3
import os
from django.conf import settings
import time
from portfolio.constants import S3_ASSETS_FOLDER_NAME
from portfolio.exceptions.exceptions import GeneralError
import requests


def s3_config():
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("S3_SECRET_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("S3_KEY_ID"),
            region_name=os.environ.get("S3_REGION_NAME"),
        )
        return s3
    except Exception as error:
        print("Error occurred on s3 -> ", error)
        return None


class S3CLientSingleton:
    _instance = None  # Private class-level variable to hold the S3 client instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = s3_config()
        return cls._instance


class AWS_S3_Operations:
    s3_client = S3CLientSingleton.get_instance()

    @classmethod
    def copy_object_in_s3(cls, old_s3_asset_key, new_s3_asset_key, bucket_name):
        try:
            cls.s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={
                    "Bucket": bucket_name,
                    "Key": old_s3_asset_key,  # Old key
                },
                Key=new_s3_asset_key,  # New key
            )
            return
        except Exception as error:
            print("Error occurred while copying the object -> ", error)
            raise GeneralError("Error occurred while processing the images")

    @classmethod
    def delete_object_in_s3(cls, bucket_name, old_s3_asset_key):
        try:
            cls.s3_client.delete_object(Bucket=bucket_name, Key=old_s3_asset_key)
            return
        except Exception as error:
            print("Error occurred while deleting the object -> ", error)
            raise GeneralError("Error occurred while processing the images")


def s3_name_format(name):
    return name.replace(" ", "-").lower()


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
                "Items": [f"/{project_name}/{S3_ASSETS_FOLDER_NAME}/{file_name}"],
            },
            "CallerReference": str(time.time()).replace(".", ""),
        },
    )
    return invalidation_response


def download_assets(asset_url, s3_template_name, asset_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
    }

    try:
        response = requests.get(asset_url, headers=headers)
        response.raise_for_status()
    except Exception as error:
        return str(error)

    content = response.content
    content_type = response.headers.get("Content-Type")

    bucket_name = os.environ.get("S3_TEMPLATE_BUCKET_NAME")
    s3_file_path = f"{s3_template_name}/{S3_ASSETS_FOLDER_NAME}/{asset_name}"

    try:
        s3_client = S3CLientSingleton.get_instance()
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_file_path,
            Body=content,
            ContentType=content_type,
        )
        return True
    except Exception as error:
        return str(error)
