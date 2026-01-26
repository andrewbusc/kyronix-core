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
    margin = 72
    content_right = page_width - margin
    footer_height = 72
    section_color = (0.12, 0.55, 0.6)
    light_gray = (0.85, 0.85, 0.85)

    def as_amount(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def format_currency(value):
        return f"${as_amount(value):,.2f}"

    def format_number(value):
        return f"{value:.2f}" if isinstance(value, (int, float)) else "-"

    gross_pay = float(paystub.gross_pay or 0)
    if gross_pay == 0:
        gross_pay = sum(as_amount(item.get("amount")) for item in earnings)

    total_deductions = float(paystub.total_deductions or 0)
    if total_deductions == 0:
        total_deductions = sum(as_amount(item.get("amount")) for item in deductions)

    net_pay = float(paystub.net_pay or 0)
    if net_pay == 0:
        net_pay = gross_pay - total_deductions

    def draw_footer():
        draw_paystub_style_footer(
            c,
            margin=margin,
            footer_height=footer_height,
            generated_at=now,
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

        company_lines = [settings.employer_legal_name]
        employee_lines = [
            f"{paystub.employee_first_name} {paystub.employee_last_name}",
            f"Pay period: {paystub.pay_period_start} - {paystub.pay_period_end}",
            f"Pay date: {paystub.pay_date}",
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
        c.setLineWidth(1)
        return y_top - box_height - 16

    def draw_header(full: bool) -> float:
        y = page_height - margin
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, y, settings.employer_legal_name)
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(content_right, y, "EARNINGS STATEMENT")
        y -= 16
        c.setFont("Helvetica", 9)
        c.drawRightString(
            content_right,
            y,
            f"Pay period: {paystub.pay_period_start} - {paystub.pay_period_end}",
        )
        y -= 12
        c.drawRightString(content_right, y, f"Pay date: {paystub.pay_date}")
        y -= 10
        c.setStrokeColorRGB(*light_gray)
        c.setLineWidth(0.7)
        c.line(margin, y, content_right, y)
        y -= 16
        if full:
            y = draw_info_boxes(y)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)
        return y

    def ensure_space(current_y: float, required_height: float, on_new_page=None) -> float:
        if current_y - required_height < footer_height + 20:
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
        c.drawRightString(margin + 300, current_y, "Hours")
        c.drawRightString(margin + 380, current_y, "Rate")
        c.drawRightString(content_right, current_y, "Amount")
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
        c.drawRightString(content_right, current_y, "Amount")
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
        c.drawRightString(content_right, current_y, "Amount")
        current_y -= 6
        c.setStrokeColorRGB(*light_gray)
        c.setLineWidth(0.7)
        c.line(margin, current_y, content_right, current_y)
        c.setStrokeColorRGB(0, 0, 0)
        return current_y - 10

    y = draw_header(full=True)

    y = ensure_space(y, 70)
    y = draw_earnings_header(y)
    c.setFont("Helvetica", 9)
    for item in earnings:
        y = ensure_space(y, 16, on_new_page=lambda new_y: draw_earnings_header(new_y, True))
        line = item or {}
        description = str(line.get("label") or "Earnings")
        hours = line.get("hours")
        rate = line.get("rate")
        amount = line.get("amount")
        c.drawString(margin, y, description)
        c.drawRightString(margin + 300, y, format_number(hours))
        c.drawRightString(margin + 380, y, format_currency(rate) if isinstance(rate, (int, float)) else "-")
        c.drawRightString(content_right, y, format_currency(amount))
        y -= 12

    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, "Gross Pay")
    c.drawRightString(content_right, y, format_currency(gross_pay))
    y -= 18

    if deductions:
        y = ensure_space(y, 60)
        y = draw_deductions_header(y)
        c.setFont("Helvetica", 9)
        for item in deductions:
            y = ensure_space(y, 16, on_new_page=lambda new_y: draw_deductions_header(new_y, True))
            line = item or {}
            label = str(line.get("label") or "Deduction")
            amount = line.get("amount")
            c.drawString(margin, y, label)
            c.drawRightString(content_right, y, format_currency(amount))
            y -= 12
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "Total Deductions")
        c.drawRightString(content_right, y, format_currency(total_deductions))
        y -= 18
    else:
        y -= 8

    y = ensure_space(y, 50)
    y = draw_summary_header(y)
    summary_rows = [
        ("Gross Earnings", gross_pay),
        ("Total Deductions", total_deductions),
        ("Net Pay", net_pay),
    ]
    for label, amount in summary_rows:
        y = ensure_space(y, 16, on_new_page=lambda new_y: draw_summary_header(new_y, True))
        if label == "Net Pay":
            c.setFont("Helvetica-Bold", 9)
        else:
            c.setFont("Helvetica", 9)
        c.drawString(margin, y, label)
        c.drawRightString(content_right, y, format_currency(amount))
        y -= 12

    draw_footer()
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
