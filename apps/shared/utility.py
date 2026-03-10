import re
import threading

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError

email_regex = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")
username_regex = re.compile(r"^[a-zA-Z0-9_.-]+$")



def check_email(value):
    value = str(value).strip().lower()
    if re.fullmatch(email_regex, value):
        return True
    raise ValidationError({
        'success' : False,
        'message' : "Email noto'g'ri formatda kiritildi!",
    })


def check_user_type(user_input):
    if re.fullmatch(username_regex, user_input):
        return "username"
    elif re.fullmatch(email_regex, user_input):
        return "email"
    raise ValidationError({
        'success' : False,
        'message' : "Username yoki email noto'g'ri formatda kiritildi!",
    })

class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)
    def run(self):
        self.email.send()


class Email:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data['subject'],
            body=data['body'],
            to=[data['to_email']],
        )
        if data.get('content_type') == "html":
            email.content_subtype = 'html'
        EmailThread(email).start()

def send_email(email, code):
    html_content = render_to_string(
        'email/authentication/activate_account.html',
        {"code": code}
    )
    Email.send_email(
        {
            "subject": "Ro'yxatdan o'tish",
            "to_email": email,
            "body": html_content,
            "content_type": "html"
        }
    )