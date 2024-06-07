from django.core.mail import send_mail
from django.template.loader import get_template


class BaseEmail:
    def __init__(self, sender, recipient, subject, content, message, template_path):
        self.sender = sender
        self.recipient = recipient
        self.subject = subject
        self.content = content
        self.message = message
        self.template_path = template_path

    def send_email(self):
        body = self.load_template(self.content, self.template_path)
        try:
            email_sent = send_mail(
                subject=self.subject,
                message=self.message,
                html_message=body,
                from_email=self.sender,
                recipient_list=[self.recipient],
                fail_silently=False,
            )
            if str(email_sent) == "1":
                return True
            else:
                return False
        except Exception as error:
            print(error)
            return False

    def load_template(self, content, template_path):
        try:
            html_email_template = get_template(template_path)
            html_content = html_email_template.render(content)
            return html_content
        except Exception as error:
            print("Error occurred while loading html tempalte ->", error)
            return error
