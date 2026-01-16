import io
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, ROUND_HALF_UP

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.schemas.paystub_generate import PaystubGenerateRequest
from app.utils.pdf import draw_paystub_style_footer


def _format_currency(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${quantized:,.2f}"


def _format_rate(value: Decimal, pay_type: str) -> str:
    unit = "/hr" if pay_type == "Hourly" else "/yr"
    return f"{_format_currency(value)}{unit}"


def _format_optional_decimal(value: Decimal | None) -> str:
    if value is None:
        return "-"
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def _format_hours(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def _format_last_name(employee_name: str) -> str:
    parts = employee_name.strip().split()
    last_name = parts[-1] if parts else "EMPLOYEE"
    cleaned = re.sub(r"[^A-Za-z0-9]", "", last_name).upper()
    return cleaned or "EMPLOYEE"


def build_paystub_filename(payload: PaystubGenerateRequest) -> str:
    last_name = _format_last_name(payload.employee.employee_name)
    pay_date = payload.pay_period.pay_date.strftime("%Y%m%d")
    return f"KYRONIX_PAYSTUB_{last_name}_{pay_date}.pdf"


def render_paystub_v1_pdf(payload: PaystubGenerateRequest) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(f"{settings.project_name} Paystub")
    c.setAuthor(settings.employer_legal_name)
    c.setSubject(f"Paystub ID: {payload.metadata.paystub_id}")
    c.setKeywords(
        f"employee_id:{payload.employee.employee_id}, pay_date:{payload.pay_period.pay_date.isoformat()}"
    )

    page_width, page_height = letter
    margin = 72
    content_right = page_width - margin
    footer_height = 72

    def draw_footer():
        generated_at = payload.metadata.generated_timestamp
        draw_paystub_style_footer(
            c,
            margin=margin,
            footer_height=footer_height,
            generated_at=generated_at,
            tz=ZoneInfo(settings.time_zone),
            tz_label="PT",
        )

    def draw_header():
        y = page_height - margin
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, settings.employer_legal_name)
        y -= 16
        c.setFont("Helvetica", 9)
        c.drawString(margin, y, payload.company.company_address)
        y -= 12
        c.drawString(margin, y, f"Payroll contact: {payload.company.payroll_contact_email}")

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(content_right, page_height - margin, "EARNINGS STATEMENT")
        c.setFont("Helvetica", 9)
        c.drawRightString(
            content_right,
            page_height - margin - 14,
            f"Pay date: {payload.pay_period.pay_date.isoformat()}",
        )
        c.drawRightString(
            content_right,
            page_height - margin - 26,
            f"Pay period: {payload.pay_period.pay_period_start} to {payload.pay_period.pay_period_end}",
        )
        y = page_height - margin - 44
        c.line(margin, y, content_right, y)
        y -= 18
        return y

    def ensure_space(current_y: float, required_lines: int) -> float:
        minimum_y = footer_height + 20
        if current_y - (required_lines * 14) < minimum_y:
            draw_footer()
            c.showPage()
            return draw_header()
        return current_y

    y = draw_header()

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Employee")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, payload.employee.employee_name)
    y -= 12
    c.setFont("Helvetica", 9)
    c.drawString(
        margin,
        y,
        f"{payload.employee.job_title} - {payload.employee.department}",
    )
    y -= 12
    c.drawString(
        margin,
        y,
        f"{payload.employee.employment_type} - {payload.employee.pay_type}",
    )
    y -= 12
    c.drawString(
        margin,
        y,
        f"Pay rate: {_format_rate(payload.employee.pay_rate, payload.employee.pay_type)}",
    )
    y -= 18

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Payment")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Pay frequency: {payload.pay_period.pay_frequency}")
    y -= 12
    c.drawString(margin, y, f"Payment method: {payload.payment.payment_method}")
    y -= 12
    c.drawString(margin, y, f"Payment status: {payload.payment.payment_status}")
    y -= 12
    c.drawString(margin, y, f"Bank: {payload.payment.bank_name_masked}")
    y -= 18

    y = ensure_space(y, 4)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Earnings")
    y -= 12
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "Description")
    c.drawRightString(margin + 250, y, "Hours")
    c.drawRightString(margin + 320, y, "Rate")
    c.drawRightString(margin + 400, y, "Current")
    c.drawRightString(content_right, y, "YTD")
    y -= 6
    c.line(margin, y, content_right, y)
    y -= 12

    c.setFont("Helvetica", 9)
    for item in payload.earnings:
        y = ensure_space(y, 2)
        c.drawString(margin, y, item.description)
        c.drawRightString(margin + 250, y, _format_optional_decimal(item.hours))
        c.drawRightString(margin + 320, y, _format_optional_decimal(item.rate))
        c.drawRightString(margin + 400, y, _format_currency(item.current_amount))
        c.drawRightString(content_right, y, _format_currency(item.ytd_amount))
        y -= 12

    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "Gross Pay")
    c.drawRightString(margin + 400, y, _format_currency(payload.totals.gross_pay_current))
    c.drawRightString(content_right, y, _format_currency(payload.totals.gross_pay_ytd))
    y -= 18

    y = ensure_space(y, 4)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Deductions")
    y -= 12
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "Deduction")
    c.drawRightString(margin + 400, y, "Current")
    c.drawRightString(content_right, y, "YTD")
    y -= 6
    c.line(margin, y, content_right, y)
    y -= 12

    c.setFont("Helvetica", 9)
    for item in payload.deductions:
        y = ensure_space(y, 2)
        c.drawString(margin, y, item.deduction_name)
        c.drawRightString(margin + 400, y, _format_currency(item.current_amount))
        c.drawRightString(content_right, y, _format_currency(item.ytd_amount))
        y -= 12

    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "Total Deductions")
    c.drawRightString(margin + 400, y, _format_currency(payload.totals.total_deductions_current))
    c.drawRightString(content_right, y, _format_currency(payload.totals.total_deductions_ytd))
    y -= 24

    y = ensure_space(y, 4)
    box_height = 32
    box_top = y
    box_bottom = box_top - box_height
    text_y = box_bottom + 18
    c.rect(margin, box_bottom, content_right - margin, box_height, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin + 8, text_y, "Net Pay")
    c.drawRightString(
        content_right - 8, text_y, _format_currency(payload.totals.net_pay_current)
    )
    y = box_bottom - 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Year-to-Date Summary")
    y -= 12
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Gross: {_format_currency(payload.totals.gross_pay_ytd)}")
    c.drawString(margin + 180, y, f"Deductions: {_format_currency(payload.totals.total_deductions_ytd)}")
    c.drawString(margin + 360, y, f"Net: {_format_currency(payload.totals.net_pay_ytd)}")
    y -= 18

    if payload.leave_balances is not None:
        y = ensure_space(y, 6)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "Leave Balances (Hours)")
        y -= 12
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "Type")
        c.drawRightString(margin + 260, y, "Accrued")
        c.drawRightString(margin + 360, y, "Used")
        c.drawRightString(content_right, y, "Balance")
        y -= 6
        c.line(margin, y, content_right, y)
        y -= 12

        c.setFont("Helvetica", 9)
        c.drawString(margin, y, "Vacation")
        c.drawRightString(margin + 260, y, _format_hours(payload.leave_balances.vacation_accrued))
        c.drawRightString(margin + 360, y, _format_hours(payload.leave_balances.vacation_used))
        c.drawRightString(content_right, y, _format_hours(payload.leave_balances.vacation_balance))
        y -= 12
        c.drawString(margin, y, "Sick")
        c.drawRightString(margin + 260, y, _format_hours(payload.leave_balances.sick_accrued))
        c.drawRightString(margin + 360, y, _format_hours(payload.leave_balances.sick_used))
        c.drawRightString(content_right, y, _format_hours(payload.leave_balances.sick_balance))

    draw_footer()
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
