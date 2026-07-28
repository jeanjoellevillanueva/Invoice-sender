"""
PDF invoice generation matching the sample layout.
"""

from calendar import month_name
from calendar import monthrange
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from storage import GENERATED_DIR
from storage import ensure_dirs


def build_description(config, dt=None):
    """
    Build payroll description for the invoice month.
    """
    dt = dt or datetime.now()
    last_day = monthrange(dt.year, dt.month)[1]
    template = config["invoice"].get(
        "description_template",
        "Payroll run for the period 1 - {last_day} {month_name}, {year}",
    )
    return template.format(
        last_day=last_day,
        month_name=month_name[dt.month],
        year=dt.year,
    )


def format_amount(amount, currency="Php"):
    """
    Format money with thousands separators.
    """
    return f"{currency} {amount:,.2f}"


def generate_invoice_pdf(config, invoice_number, dt=None, output_path=None):
    """
    Generate a single-page invoice PDF and return its path.
    """
    ensure_dirs()
    dt = dt or datetime.now()
    invoice = config["invoice"]
    issued_by = invoice["issued_by"]
    issued_to = invoice["issued_to"]
    pay_to = invoice["pay_to"]
    description = build_description(config, dt)
    amount = float(invoice["amount"])
    currency = invoice.get("currency", "Php")
    amount_text = format_amount(amount, currency)

    if output_path is None:
        filename = f"Invoice_{dt.strftime('%m-%Y')}_{invoice_number}.pdf"
        output_path = GENERATED_DIR / filename
    else:
        output_path = Path(output_path)

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    left = 25 * mm
    right = width - 25 * mm
    y = height - 30 * mm

    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawRightString(right, y, "INVOICE")
    y -= 10 * mm

    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(right, y, f"Invoice Number: {invoice_number}")
    y -= 5 * mm
    pdf.drawRightString(right, y, f"Date: {dt.strftime('%d.%m.%Y')}")
    y -= 12 * mm

    pdf.setStrokeColorRGB(0.2, 0.2, 0.2)
    pdf.setLineWidth(0.5)
    pdf.line(left, y, right, y)
    y -= 8 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, "ISSUED BY")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    for line in [
        issued_by["name"],
        issued_by["address"],
        issued_by["phone"],
        issued_by["email"],
    ]:
        pdf.drawString(left, y, line)
        y -= 5 * mm

    y -= 4 * mm
    pdf.line(left, y, right, y)
    y -= 8 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, "ISSUED TO")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    for line in [
        issued_to["name"],
        issued_to["address"],
        f"ABN: {issued_to['abn']}",
    ]:
        pdf.drawString(left, y, line)
        y -= 5 * mm

    y -= 4 * mm
    pdf.line(left, y, right, y)
    y -= 10 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, "DESCRIPTION")
    pdf.drawRightString(right, y, "SUBTOTAL")
    y -= 7 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, description)
    pdf.drawRightString(right, y, amount_text)

    y -= 10 * mm
    pdf.line(left, y, right, y)
    y -= 10 * mm

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(left, y, "TOTAL")
    pdf.drawRightString(right, y, amount_text)

    y -= 10 * mm
    pdf.line(left, y, right, y)
    y -= 10 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, "PAY TO")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    for label, value in [
        ("Bank Name", pay_to["bank_name"]),
        ("Account Name", pay_to["account_name"]),
        ("Account Number", pay_to["account_number"]),
        ("Swift Code", pay_to["swift_code"]),
    ]:
        pdf.drawString(left, y, f"{label}: {value}")
        y -= 5 * mm

    pdf.save()
    return output_path
