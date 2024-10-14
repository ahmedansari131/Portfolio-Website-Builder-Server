from django.db.models.signals import post_delete
from django.dispatch import receiver
from server.utils.s3 import s3_config, s3_name_format
from django.conf import settings
from .models import Template, PortfolioProject


@receiver(post_delete, sender=Template)
def delete_template_from_s3(sender, instance, **kwargs):
    s3_client = s3_config()
    bucket_name = instance.bucket_name
    template_name = instance.template_name
    folder_prefix = f"{template_name}/"  # Ensure folder prefix ends with '/'

    try:
        # List all objects in the specified folder
        objects_to_delete = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix=folder_prefix
        )

        if "Contents" in objects_to_delete:
            # Loop through and delete each object in the folder
            for obj in objects_to_delete["Contents"]:
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
        else:
            print(f"No objects found in folder {folder_prefix}")
    except Exception as error:
        print("Error occurred while deleting the object on s3", error)


@receiver(post_delete, sender=PortfolioProject)
def delete_project_from_s3(sender, instance, **kwargs):
    s3_client = s3_config()
    bucket_name = settings.AWS_DEPLOYED_PORTFOLIO_BUCKET_NAME
    project_slug = instance.project_slug
    folder_prefix = f"{project_slug}/"  # Ensure folder prefix ends with '/'

    try:
        # List all objects in the specified folder
        objects_to_delete = s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix=folder_prefix
        )

        if "Contents" in objects_to_delete:
            # Loop through and delete each object in the folder
            for obj in objects_to_delete["Contents"]:
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
        else:
            print(f"No objects found in folder {folder_prefix}")
    except Exception as error:
        print("Error occurred while deleting the object on s3", error)
