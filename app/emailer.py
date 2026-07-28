"""
Gmail SMTP email delivery for invoices.
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def send_invoice_email(config, recipient, subject, body, pdf_path):
    """
    Send an invoice PDF via Gmail SMTP.
    """
    smtp = config["smtp"]
    username = smtp["username"]
    password = smtp["password"]
    if not username or not password:
        raise ValueError("SMTP username and password are required in config.")
    if not recipient:
        raise ValueError("Recipient email is required.")

    from_email = smtp.get("from_email") or username
    from_name = smtp.get("from_name") or from_email
    host = smtp.get("host", "smtp.gmail.com")
    port = int(smtp.get("port", 587))

    message = MIMEMultipart()
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    pdf_path = Path(pdf_path)
    with pdf_path.open("rb") as handle:
        attachment = MIMEApplication(handle.read(), _subtype="pdf")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=pdf_path.name,
    )
    message.attach(attachment)

    with smtplib.SMTP(host, port, timeout=60) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.sendmail(from_email, [recipient], message.as_string())
