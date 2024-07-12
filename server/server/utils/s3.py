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