from server.email import BaseEmail

class UserVerificationEmail(BaseEmail):
    def __init__(self, sender, recipient, content):
        super().__init__(
            sender=sender,
            recipient=recipient,
            content=content,
            subject="Email verification",
            message="Please verify your email",
            template_path="email_templates/verify_email.html",
        )

    def send_verification_email(self):
        try:
            email_sent = super().send_email()
            return email_sent
        except Exception as error:
            print(f"Error occurred while sending verification email -> {error}")
            return "Error occurred on server while sending verification email"
