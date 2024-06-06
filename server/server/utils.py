from django.core.mail import send_mail
from django.template.loader import get_template
from django.template import Context


class BaseEmail:
    def __init__(self, sender, recipient, subject, content):
        self.sender = sender
        self.recepient = recipient
        self.subject = subject
        self.content = content

    def send_email(self):
        print("Sender email ->", self.sender)
        print("Recepient email ->", self.recepient)
        body = self.load_template(self.content)
        try:
            send_mail(
                subject=self.subject,
                message="This is email verification message",
                html_message=body,
                from_email=self.sender,
                recipient_list=[self.recepient],
                fail_silently=False,
            )
        except Exception as error:
            return error

    def load_template(self, content):
        try:
            html_email_template = get_template("email_templates/verify_email.html")
            html_content = html_email_template.render(content)
            return html_content
        except Exception as error:
            print("Error occurred while loading html tempalte ->", error)
            return error
