import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import settings


def draw_paystub_style_footer(
    c: canvas.Canvas,
    *,
    margin: float,
    footer_height: float,
    generated_at: datetime,
    tz: ZoneInfo | None = None,
    tz_label: str = "UTC",
) -> None:
    footer_time = generated_at
    if footer_time.tzinfo is None:
        footer_time = footer_time.replace(tzinfo=tz or timezone.utc)
    if tz is not None:
        footer_time = footer_time.astimezone(tz)
    stamp = f"{footer_time.strftime('%Y-%m-%d %H:%M:%S')} {tz_label}"

    page_width = c._pagesize[0]
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0, 0, 0)
    c.line(margin, footer_height, page_width - margin, footer_height)
    c.drawString(
        margin,
        footer_height - 14,
        "This document was generated electronically via Kyronix Core.",
    )
    c.drawString(margin, footer_height - 28, f"Generated on: {stamp}")


def render_document_pdf(document) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(f"{settings.project_name} Document")

    now = datetime.now(ZoneInfo(settings.time_zone))
    y = 760

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, settings.project_name)
    y -= 24

    c.setFont("Helvetica", 11)
    c.drawString(72, y, f"Employer: {settings.employer_legal_name}")
    y -= 18
    c.drawString(72, y, f"Document ID: {document.id}")
    y -= 18
    c.drawString(72, y, f"Title: {document.title}")
    y -= 18
    c.drawString(72, y, f"Generated: {now.isoformat()}")
    y -= 24

    c.setFont("Helvetica", 10)
    text = c.beginText(72, y)
    for line in (document.body or "").splitlines():
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()


def render_paystub_pdf(paystub) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(f"{settings.project_name} Paystub")
    c.setAuthor(settings.employer_legal_name)
    c.setSubject(f"Paystub ID: {paystub.id}")
    c.setKeywords(f"user_id:{paystub.user_id}, pay_date:{paystub.pay_date.isoformat()}")

    page_width, page_height = letter
    now = datetime.now(ZoneInfo(settings.time_zone))
    earnings = paystub.earnings or []
    deductions = paystub.deductions or []

    def as_amount(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    gross_pay = float(paystub.gross_pay or 0)
    if gross_pay == 0:
        gross_pay = sum(as_amount(item.get("amount")) for item in earnings)

    total_deductions = float(paystub.total_deductions or 0)
    if total_deductions == 0:
        total_deductions = sum(as_amount(item.get("amount")) for item in deductions)

    net_pay = float(paystub.net_pay or 0)
    if net_pay == 0:
        net_pay = gross_pay - total_deductions

    x_left = 72
    y = page_height - 72

    def draw_footer():
        draw_paystub_style_footer(
            c,
            margin=x_left,
            footer_height=72,
            generated_at=now,
            tz=ZoneInfo(settings.time_zone),
            tz_label="PT",
        )

    def draw_header(title_suffix=""):
        nonlocal y
        y = page_height - 72
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x_left, y, f"{settings.project_name} Paystub{title_suffix}")
        y -= 24
        c.setFont("Helvetica", 11)
        c.drawString(x_left, y, f"Employer: {settings.employer_legal_name}")
        y -= 18
        employee_name = f"{paystub.employee_first_name} {paystub.employee_last_name}"
        c.drawString(x_left, y, f"Employee: {employee_name}")
        y -= 18
        c.drawString(
            x_left,
            y,
            f"Pay period: {paystub.pay_period_start} to {paystub.pay_period_end}",
        )
        y -= 18
        c.drawString(x_left, y, f"Pay date: {paystub.pay_date}")
        y -= 24

    def draw_earnings_header():
        nonlocal y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_left, y, "Earnings Statement")
        y -= 16
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, "Description")
        c.drawString(x_left + 250, y, "Hours")
        c.drawString(x_left + 320, y, "Rate")
        c.drawString(x_left + 400, y, "Amount")
        y -= 8
        c.line(x_left, y, page_width - x_left, y)
        y -= 14

    def draw_deductions_header():
        nonlocal y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_left, y, "Deductions")
        y -= 14

    def ensure_space(lines=1, title_suffix="", on_new_page=None):
        nonlocal y
        if y < 80 + (lines * 14):
            draw_footer()
            c.showPage()
            draw_header(title_suffix=title_suffix)
            if on_new_page:
                on_new_page()
            return True
        return False

    draw_header()
    draw_earnings_header()

    c.setFont("Helvetica", 10)
    for item in earnings:
        ensure_space(on_new_page=draw_earnings_header, title_suffix=" (continued)")
        line = item or {}
        description = str(line.get("label") or "Earnings")
        hours = line.get("hours")
        rate = line.get("rate")
        amount = line.get("amount")

        c.drawString(x_left, y, description)
        c.drawRightString(x_left + 300, y, f"{hours:.2f}" if isinstance(hours, (int, float)) else "-")
        c.drawRightString(x_left + 370, y, f"${rate:,.2f}" if isinstance(rate, (int, float)) else "-")
        c.drawRightString(page_width - x_left, y, f"${as_amount(amount):,.2f}")
        y -= 16

    ensure_space(lines=3, on_new_page=draw_earnings_header, title_suffix=" (continued)")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_left, y, "Gross Pay")
    c.drawRightString(page_width - x_left, y, f"${gross_pay:,.2f}")
    y -= 16

    if deductions:
        did_break = ensure_space(lines=2, on_new_page=draw_deductions_header, title_suffix=" (continued)")
        if not did_break:
            draw_deductions_header()
        c.setFont("Helvetica", 10)
        for item in deductions:
            ensure_space(on_new_page=draw_deductions_header, title_suffix=" (continued)")
            line = item or {}
            label = str(line.get("label") or "Deduction")
            amount = as_amount(line.get("amount"))
            c.drawString(x_left, y, label)
            c.drawRightString(page_width - x_left, y, f"${amount:,.2f}")
            y -= 14
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, "Total Deductions")
        c.drawRightString(page_width - x_left, y, f"${total_deductions:,.2f}")
        y -= 18
    else:
        y -= 8

    ensure_space(lines=2)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_left, y, "Net Pay")
    c.drawRightString(page_width - x_left, y, f"${net_pay:,.2f}")

    draw_footer()
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
