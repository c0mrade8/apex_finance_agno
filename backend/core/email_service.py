import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")


def send_email(subject, content, to_email="niharikarampathi2704@gmail.com"):
    try:
        message = Mail(
            from_email="rampathiniharika8@gmail.com",
            to_emails=to_email,
            subject=subject,
            html_content=content
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)

        print("Email sent")

    except Exception as e:
        print(f"Email error: {e}")