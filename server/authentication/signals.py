from django.db.models.signals import post_save
from django.dispatch import receiver
from portfolio.models import PortfolioProject
from .utils import generate_email_verification_link
from .email import UserVerificationEmail
import os
from .constants import EMAIL_VERIFICATION_TOKEN_TYPE


@receiver(post_save, sender=PortfolioProject)
def send_verification_email(sender, instance, created, update_fields, **kwargs):
    if update_fields and "portfolio_contact_configured_email" in update_fields:
        # Only send the email if the email field is set
        if instance.portfolio_contact_configured_email:
            verification_link = generate_email_verification_link(
                user_id=instance.created_by.id,
                token_type=EMAIL_VERIFICATION_TOKEN_TYPE,
                project_id=instance.id,
            )

            UserVerificationEmail(
                sender=os.environ.get("NO_REPLY_EMAIL"),
                recipient=instance.portfolio_contact_configured_email,
                content={
                    "username": instance.created_by.username,
                    "verification_link": verification_link,
                },
            ).send_verification_email()
