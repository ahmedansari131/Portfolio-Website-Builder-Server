import boto3
import os


def s3_config():
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("S3_SECRET_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("S3_KEY_ID"),
            region_name=os.environ.get("S3_REGION_NAME"),
        )
    except Exception as error:
        return f"Error occurred while connecting to S3 -> {error}"

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
