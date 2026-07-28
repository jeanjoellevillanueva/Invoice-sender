"""
Invoice send orchestration for scheduled and manual runs.
"""

from calendar import month_name
from calendar import monthrange
from copy import deepcopy
from datetime import datetime
import re

from emailer import send_invoice_email
from pdf_invoice import build_description
from pdf_invoice import format_amount
from pdf_invoice import generate_invoice_pdf
from storage import bump_invoice_number
from storage import load_config
from storage import load_sent
from storage import month_key
from storage import next_invoice_number
from storage import record_sent
from storage import was_sent_for_month

MONTH_KEY_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")


def render_template(template, values):
    """
    Simple brace-template renderer.
    """
    return template.format(**values)


def parse_month_key(value):
    """
    Parse a YYYY-MM string into year and month integers.
    """
    if not value or not isinstance(value, str):
        raise ValueError("month must be a YYYY-MM string.")
    match = MONTH_KEY_PATTERN.match(value.strip())
    if not match:
        raise ValueError("month must use YYYY-MM format.")
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        raise ValueError("month must be between 01 and 12.")
    return year, month


def datetime_for_month(month_value, send_day=25):
    """
    Build an invoice date for a YYYY-MM period using the send day.
    """
    year, month = parse_month_key(month_value)
    last_day = monthrange(year, month)[1]
    day = min(int(send_day), last_day)
    return datetime(year, month, day)


def build_email_content(config, invoice_number, dt=None):
    """
    Build subject and body for the invoice email.
    """
    dt = dt or datetime.now()
    invoice = config["invoice"]
    amount = float(invoice["amount"])
    currency = invoice.get("currency", "Php")
    values = {
        "invoice_number": invoice_number,
        "month_name": month_name[dt.month],
        "year": dt.year,
        "amount": f"{amount:,.2f}",
        "currency": currency,
        "description": build_description(config, dt),
        "from_name": config["smtp"].get("from_name", ""),
    }
    subject = render_template(
        config.get(
            "email_subject_template",
            "Invoice {invoice_number} — {month_name} {year}",
        ),
        values,
    )
    body = render_template(
        config.get(
            "email_body_template",
            "Please find attached invoice {invoice_number}.",
        ),
        values,
    )
    return subject, body


def should_auto_send(config=None, now=None):
    """
    Decide whether the monthly auto-send should run now.
    """
    config = config or load_config()
    now = now or datetime.now()
    send_day = int(config.get("send_day", 25))
    if now.day < send_day:
        return False
    return not was_sent_for_month(month_key(now))


def send_invoice(force=False, dt=None, month=None):
    """
    Generate, email, and record an invoice for a chosen or current month.
    """
    config = load_config()
    if month:
        dt = datetime_for_month(month, config.get("send_day", 25))
    elif dt is None:
        dt = datetime.now()
    key = month_key(dt)

    if not force and was_sent_for_month(key):
        return {
            "ok": False,
            "skipped": True,
            "message": f"Already sent for {key}.",
            "sent": load_sent().get(key),
        }

    number, invoice_number = next_invoice_number(config)
    pdf_path = generate_invoice_pdf(config, invoice_number, dt=dt)
    recipient = config.get("recipient_email", "").strip()
    subject, body = build_email_content(config, invoice_number, dt=dt)

    send_invoice_email(config, recipient, subject, body, pdf_path)
    bump_invoice_number(config, number)
    record = record_sent(
        key,
        invoice_number,
        pdf_path,
        recipient,
        forced=force,
    )

    return {
        "ok": True,
        "skipped": False,
        "message": f"Sent {invoice_number} for {key} to {recipient}.",
        "invoice_number": invoice_number,
        "pdf_path": str(pdf_path),
        "month": key,
        "amount": format_amount(
            float(config["invoice"]["amount"]),
            config["invoice"].get("currency", "Php"),
        ),
        "sent": record.get(key),
    }


def merge_config(existing, payload):
    """
    Merge UI payload into the existing config shape.
    """
    updated = deepcopy(existing)

    if "send_day" in payload:
        day = int(payload["send_day"])
        if day < 1 or day > 28:
            raise ValueError("send_day must be between 1 and 28.")
        updated["send_day"] = day

    if "recipient_email" in payload:
        updated["recipient_email"] = str(payload["recipient_email"]).strip()

    if "smtp" in payload and isinstance(payload["smtp"], dict):
        for field in ("host", "port", "username", "password", "from_email", "from_name"):
            if field in payload["smtp"]:
                value = payload["smtp"][field]
                if field == "port":
                    updated["smtp"][field] = int(value)
                elif field == "password" and value == "":
                    continue
                else:
                    updated["smtp"][field] = value

    if "invoice" in payload and isinstance(payload["invoice"], dict):
        inv = payload["invoice"]
        for field in ("prefix", "amount", "currency", "description_template"):
            if field in inv:
                if field == "amount":
                    updated["invoice"][field] = float(inv[field])
                else:
                    updated["invoice"][field] = inv[field]
        if "last_number" in inv:
            updated["invoice"]["last_number"] = int(inv["last_number"])
        for section in ("issued_by", "issued_to", "pay_to"):
            if section in inv and isinstance(inv[section], dict):
                updated["invoice"][section].update(inv[section])

    for field in ("email_subject_template", "email_body_template"):
        if field in payload:
            updated[field] = payload[field]

    return updated
