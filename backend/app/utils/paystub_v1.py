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


def _format_optional_currency(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return _format_currency(value)


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


def _wrap_text(
    c: canvas.Canvas,
    text: str,
    max_width: float,
    font_name: str,
    font_size: float,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or c.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


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
    margin = 54
    content_right = page_width - margin
    footer_height = 54
    section_color = (0.12, 0.55, 0.6)
    light_gray = (0.85, 0.85, 0.85)

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

    def draw_info_boxes(y_top: float) -> float:
        gap = 18
        box_width = (content_right - margin - gap)
        box_width /= 2
        padding = 8
        title_height = 12
        line_height = 11

        company_lines: list[str] = [payload.company.company_name]
        for line in payload.company.company_address.splitlines():
            company_lines.extend(
                _wrap_text(c, line, box_width - (padding * 2), "Helvetica", 9)
            )
        company_lines.append(f"Payroll: {payload.company.payroll_contact_email}")

        employee_lines = [
            payload.employee.employee_name,
            f"ID: {payload.employee.employee_id}",
            f"{payload.employee.job_title} - {payload.employee.department}",
            f"{payload.employee.employment_type} | {payload.employee.pay_type}",
            f"Pay rate: {_format_rate(payload.employee.pay_rate, payload.employee.pay_type)}",
        ]

        def calc_height(line_count: int) -> float:
            return (padding * 2) + title_height + (line_count * line_height)

        box_height = max(calc_height(len(company_lines)), calc_height(len(employee_lines)))

        def draw_box(x: float, title: str, lines: list[str]) -> None:
            c.setStrokeColorRGB(*light_gray)
            c.setLineWidth(0.7)
            c.rect(x, y_top - box_height, box_width, box_height, stroke=1, fill=0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 9)
            title_y = y_top - padding
            c.drawString(x + padding, title_y, title)
            text_y = title_y - title_height
            c.setFont("Helvetica", 9)
            for line in lines:
                c.drawString(x + padding, text_y, line)
                text_y -= line_height

        draw_box(margin, "Company", company_lines)
        draw_box(margin + box_width + gap, "Employee", employee_lines)
        c.setStrokeColorRGB(0, 0, 0)
        return y_top - box_height - 16

    def draw_header(full: bool) -> float:
        y = page_height - margin
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, y, payload.company.company_name)
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(content_right, y, "EARNINGS STATEMENT")
        y -= 16
        c.setFont("Helvetica", 9)
        c.drawRightString(
            content_right,
            y,
            f"Pay period: {payload.pay_period.pay_period_start} - {payload.pay_period.pay_period_end}",
        )
        y -= 12
        c.drawRightString(
            content_right,
            y,
            f"Pay date: {payload.pay_period.pay_date.isoformat()}",
        )
        y -= 10
        c.setStrokeColorRGB(*light_gray)
        c.setLineWidth(0.7)
        c.line(margin, y, content_right, y)
        y -= 16
        if full:
            y = draw_info_boxes(y)
            c.setFont("Helvetica", 9)
            c.drawString(
                margin,
                y,
                f"Payment: {payload.payment.payment_method} ({payload.payment.bank_name_masked})",
            )
            c.drawRightString(
                content_right,
                y,
                f"Status: {payload.payment.payment_status}",
            )
            y -= 18
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)
        return y

    def ensure_space(
        current_y: float,
        required_height: float,
        on_new_page=None,
    ) -> float:
        minimum_y = footer_height + 20
        if current_y - required_height < minimum_y:
            draw_footer()
            c.showPage()
            current_y = draw_header(full=False)
            if on_new_page:
                current_y = on_new_page(current_y)
            return current_y
        return current_y

    def draw_section_title(title: str, current_y: float) -> float:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, current_y, title)
        current_y -= 6
        c.setStrokeColorRGB(*section_color)
        c.setLineWidth(1)
        c.line(margin, current_y, content_right, current_y)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)
        return current_y - 10

    def draw_earnings_header(current_y: float, continued: bool = False) -> float:
        title = "Employee Earnings"
        if continued:
            title += " (continued)"
        current_y = draw_section_title(title, current_y)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(margin, current_y, "Description")
        c.drawRightString(margin + 260, current_y, "Rate")
        c.drawRightString(margin + 330, current_y, "Hours")
        c.drawRightString(margin + 430, current_y, "Current")
        c.drawRightString(content_right, current_y, "Year to Date")
        current_y -= 6
        c.setStrokeColorRGB(*light_gray)
        c.setLineWidth(0.7)
        c.line(margin, current_y, content_right, current_y)
        c.setStrokeColorRGB(0, 0, 0)
        return current_y - 10

    def draw_deductions_header(current_y: float, continued: bool = False) -> float:
        title = "Employee Deductions"
        if continued:
            title += " (continued)"
        current_y = draw_section_title(title, current_y)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(margin, current_y, "Description")
        c.drawRightString(margin + 430, current_y, "Current")
        c.drawRightString(content_right, current_y, "Year to Date")
        current_y -= 6
        c.setStrokeColorRGB(*light_gray)
        c.setLineWidth(0.7)
        c.line(margin, current_y, content_right, current_y)
        c.setStrokeColorRGB(0, 0, 0)
        return current_y - 10

    def draw_summary_header(current_y: float, continued: bool = False) -> float:
        title = "Summary"
        if continued:
            title += " (continued)"
        current_y = draw_section_title(title, current_y)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(margin, current_y, "Description")
        c.drawRightString(margin + 430, current_y, "Current")
        c.drawRightString(content_right, current_y, "Year to Date")
        current_y -= 6
        c.setStrokeColorRGB(*light_gray)
        c.setLineWidth(0.7)
        c.line(margin, current_y, content_right, current_y)
        c.setStrokeColorRGB(0, 0, 0)
        return current_y - 10

    def draw_leave_box(
        x: float,
        y_top: float,
        width: float,
        title: str,
        rows: list[tuple[str, str]],
    ) -> float:
        padding = 8
        line_height = 11
        header_height = 12
        box_height = (padding * 2) + header_height + ((len(rows) + 1) * line_height) + 8
        c.setStrokeColorRGB(*light_gray)
        c.setLineWidth(0.7)
        c.rect(x, y_top - box_height, width, box_height, stroke=1, fill=0)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 9)
        title_y = y_top - padding
        c.drawString(x + padding, title_y, title)
        header_y = title_y - header_height
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(x + padding, header_y, "Description")
        c.drawRightString(x + width - padding, header_y, "Hours")
        header_y -= 6
        c.setStrokeColorRGB(*section_color)
        c.setLineWidth(1)
        c.line(x + padding, header_y, x + width - padding, header_y)
        row_y = header_y - 10
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 8.5)
        for label, value in rows:
            c.drawString(x + padding, row_y, label)
            c.drawRightString(x + width - padding, row_y, value)
            row_y -= line_height
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)
        return box_height

    y = draw_header(full=True)

    c.setFont("Helvetica", 9)
    y = ensure_space(y, 70)
    y = draw_earnings_header(y)
    for item in payload.earnings:
        y = ensure_space(y, 16, on_new_page=lambda new_y: draw_earnings_header(new_y, True))
        c.drawString(margin, y, item.description)
        c.drawRightString(margin + 260, y, _format_optional_currency(item.rate))
        c.drawRightString(margin + 330, y, _format_optional_decimal(item.hours))
        c.drawRightString(margin + 430, y, _format_currency(item.current_amount))
        c.drawRightString(content_right, y, _format_currency(item.ytd_amount))
        y -= 12

    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "Gross Pay")
    c.drawRightString(margin + 430, y, _format_currency(payload.totals.gross_pay_current))
    c.drawRightString(content_right, y, _format_currency(payload.totals.gross_pay_ytd))
    y -= 18

    y = ensure_space(y, 70)
    y = draw_deductions_header(y)
    c.setFont("Helvetica", 9)
    for item in payload.deductions:
        y = ensure_space(y, 16, on_new_page=lambda new_y: draw_deductions_header(new_y, True))
        c.drawString(margin, y, item.deduction_name)
        c.drawRightString(margin + 430, y, _format_currency(item.current_amount))
        c.drawRightString(content_right, y, _format_currency(item.ytd_amount))
        y -= 12

    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "Total Deductions")
    c.drawRightString(margin + 430, y, _format_currency(payload.totals.total_deductions_current))
    c.drawRightString(content_right, y, _format_currency(payload.totals.total_deductions_ytd))
    y -= 24

    y = ensure_space(y, 60)
    y = draw_summary_header(y)
    c.setFont("Helvetica", 9)
    summary_rows = [
        ("Gross Earnings", payload.totals.gross_pay_current, payload.totals.gross_pay_ytd),
        ("Total Deductions", payload.totals.total_deductions_current, payload.totals.total_deductions_ytd),
        ("Net Pay", payload.totals.net_pay_current, payload.totals.net_pay_ytd),
    ]
    for label, current_value, ytd_value in summary_rows:
        y = ensure_space(y, 16, on_new_page=lambda new_y: draw_summary_header(new_y, True))
        if label == "Net Pay":
            c.setFont("Helvetica-Bold", 9)
        else:
            c.setFont("Helvetica", 9)
        c.drawString(margin, y, label)
        c.drawRightString(margin + 430, y, _format_currency(current_value))
        c.drawRightString(content_right, y, _format_currency(ytd_value))
        y -= 12

    if payload.leave_balances is not None:
        box_gap = 18
        box_width = (content_right - margin - box_gap)
        box_width /= 2
        required_height = 110
        y = ensure_space(y, required_height)
        box_top = y
        vacation_rows = [
            ("Hours used this period", _format_hours(payload.leave_balances.vacation_used)),
            ("Hours accrued this period", _format_hours(payload.leave_balances.vacation_accrued)),
            ("Remaining balance", _format_hours(payload.leave_balances.vacation_balance)),
        ]
        sick_rows = [
            ("Hours used this period", _format_hours(payload.leave_balances.sick_used)),
            ("Hours accrued this period", _format_hours(payload.leave_balances.sick_accrued)),
            ("Remaining balance", _format_hours(payload.leave_balances.sick_balance)),
        ]
        vacation_height = draw_leave_box(
            margin,
            box_top,
            box_width,
            "Paid Time Off Policy",
            vacation_rows,
        )
        sick_height = draw_leave_box(
            margin + box_width + box_gap,
            box_top,
            box_width,
            "Sick Policy",
            sick_rows,
        )
        y = box_top - max(vacation_height, sick_height) - 16

    draw_footer()
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
