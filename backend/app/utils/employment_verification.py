import io
import math
import textwrap
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.core.config import settings

_REGISTERED_FONTS: set[str] = set()


def build_employment_verification_filename(employee_last_name: str, generated_on: datetime) -> str:
    safe_last = "".join(ch for ch in employee_last_name.upper() if ch.isalnum() or ch == "_")
    if not safe_last:
        safe_last = "EMPLOYEE"
    date_part = generated_on.strftime("%Y%m%d")
    return f"KYRONIX_EMPLOYMENT_VERIFICATION_{safe_last}_{date_part}.pdf"


def _format_date(value: date | datetime | None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%B %d, %Y")
    if isinstance(value, date):
        return value.strftime("%B %d, %Y")
    return str(value) if value is not None else "N/A"


def _format_phone_for_sentence(phone: str | None) -> str:
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def _resolve_logo_path() -> Path | None:
    if settings.verification_logo_path:
        candidate = Path(settings.verification_logo_path)
        if candidate.is_file():
            return candidate
    candidate = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "kyronix_logo_dark_on_light.png"
    )
    return candidate if candidate.is_file() else None


def _register_font(font_name: str, font_path: str | None) -> str | None:
    if not font_path:
        return None
    candidate = Path(font_path)
    if not candidate.is_file():
        return None
    if font_name in _REGISTERED_FONTS:
        return font_name
    try:
        pdfmetrics.registerFont(TTFont(font_name, str(candidate)))
        _REGISTERED_FONTS.add(font_name)
        return font_name
    except Exception:
        return None


def _draw_star(c: canvas.Canvas, center_x: float, center_y: float, size: float) -> None:
    outer = size / 2
    inner = outer * 0.5
    path = c.beginPath()
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        radius = outer if i % 2 == 0 else inner
        x = center_x + math.cos(angle) * radius
        y = center_y + math.sin(angle) * radius
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.close()
    c.saveState()
    c.drawPath(path, fill=1, stroke=0)
    c.restoreState()


def _draw_centered_star_line(
    c: canvas.Canvas,
    center_x: float,
    y: float,
    line: str,
    font_name: str,
    font_size: float,
) -> None:
    if "*" not in line:
        c.drawCentredString(center_x, y, line.strip())
        return
    segments = [seg.strip() for seg in line.split("*") if seg.strip()]
    if len(segments) <= 1:
        c.drawCentredString(center_x, y, line.replace("*", "").strip())
        return
    star_size = font_size * 0.6
    star_padding = font_size * 0.25
    widths = [pdfmetrics.stringWidth(seg, font_name, font_size) for seg in segments]
    total = sum(widths) + (len(segments) - 1) * (star_size + 2 * star_padding)
    x = center_x - total / 2
    for index, segment in enumerate(segments):
        c.drawString(x, y, segment)
        x += widths[index]
        if index < len(segments) - 1:
            x += star_padding
            _draw_star(c, x + star_size / 2, y + font_size * 0.3, star_size)
            x += star_size + star_padding


def render_employment_verification_pdf(
    *,
    employee_name: str,
    job_title: str,
    department: str,
    employment_status: str,
    hire_date,
    verifier_name: str,
    verifier_company: str | None,
    verifier_email: str | None,
    purpose: str,
    include_salary: bool,
    salary_amount: float | None,
    generated_at: datetime,
    request_id: int,
    employee_id: int,
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle("Employment Verification Letter")
    c.setAuthor(settings.employer_legal_name)
    c.setSubject(f"Employment Verification Request {request_id}")
    c.setKeywords(f"employee_id:{employee_id}")

    page_width, page_height = letter
    x_left = 72
    y = page_height - 72

    body_font = _register_font("VerificationBody", settings.verification_body_font_path) or "Helvetica"
    signature_font = (
        _register_font("VerificationSignature", settings.verification_signature_font_path)
        or body_font
    )
    footer_font = body_font
    c.setFont(body_font, 11)
    line_height = 14

    logo_path = _resolve_logo_path()
    if logo_path:
        try:
            image = ImageReader(str(logo_path))
            img_width, img_height = image.getSize()
            max_width = 140
            max_height = 45
            scale = min(max_width / img_width, max_height / img_height, 1.0)
            logo_width = img_width * scale
            logo_height = img_height * scale
            c.drawImage(
                image,
                x_left,
                y - logo_height,
                width=logo_width,
                height=logo_height,
                mask="auto",
            )
            y -= logo_height + (line_height * 2.8)
        except Exception:
            pass

    c.drawString(x_left, y, generated_at.strftime("%B %d, %Y"))
    y -= line_height * 2

    c.drawString(x_left, y, "To Whom It May Concern,")
    y -= line_height * 2

    status_key = employment_status.upper()
    employment_phrase = "full-time employment" if status_key == "ACTIVE" else "prior employment"
    paragraph = (
        f"Please accept this letter as verification of {employment_phrase} with "
        f"{settings.employer_legal_name} for the employee listed below."
    )
    for line in textwrap.wrap(paragraph, width=90):
        c.drawString(x_left, y, line)
        y -= line_height
    y -= 6

    hire_date_str = _format_date(hire_date)
    title_label = "Current Job Title" if status_key == "ACTIVE" else "Last Job Title"
    detail_indent = 36
    info_lines = [
        f"Employee Name: {employee_name}",
        f"Hire Date: {hire_date_str}",
        f"{title_label}: {job_title}",
    ]
    if include_salary and salary_amount is not None:
        info_lines.append(f"Annual Base Salary: ${salary_amount:,.2f}")
    for line in info_lines:
        c.drawString(x_left + detail_indent, y, line)
        y -= line_height + 4
    y -= 2

    contact_phone = _format_phone_for_sentence(settings.verification_phone)
    contact_email = settings.payroll_contact_email
    if contact_phone:
        contact_paragraph = (
            "If you have any questions or need any additional information, please feel free to "
            f"contact me at {contact_phone} or you can reach me by email at {contact_email}."
        )
    else:
        contact_paragraph = (
            "If you have any questions or need any additional information, please feel free to "
            f"contact me by email at {contact_email}."
        )
    for line in textwrap.wrap(contact_paragraph, width=90):
        c.drawString(x_left, y, line)
        y -= line_height

    y -= line_height
    c.drawString(x_left, y, "Sincerely,")
    y -= line_height * 2

    signer_name = settings.verification_signer_name
    signer_credentials = settings.verification_signer_credentials.strip()
    c.setFont(signature_font, 18)
    c.drawString(x_left, y, signer_name)
    y -= line_height * 2.3

    c.setFont(body_font, 11)
    if signer_credentials:
        c.drawString(x_left, y, f"{signer_name}, {signer_credentials}")
    else:
        c.drawString(x_left, y, signer_name)
    y -= line_height

    if settings.verification_signer_title:
        c.drawString(x_left, y, settings.verification_signer_title)

    footer_y = 36
    host = settings.base_url.replace("https://", "").replace("http://", "")
    footer_time = generated_at
    if footer_time.tzinfo is None:
        footer_time = footer_time.replace(tzinfo=ZoneInfo(settings.time_zone))
    footer_text = (
        f"{settings.employer_legal_name} | Generated via {settings.project_name} ({host}) | "
        f"Generated on: {footer_time.strftime('%Y-%m-%d %H:%M:%S')} PT"
    )
    footer_notice = "This document was generated electronically via Kyronix Core."

    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(x_left, footer_y, footer_text)
    c.drawString(x_left, footer_y - 12, footer_notice)
    c.setFillColorRGB(0, 0, 0)

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
