import io
import textwrap
from datetime import date, datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import settings


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


def render_employment_verification_pdf(
    *,
    employee_name: str,
    job_title: str,
    department: str,
    employment_status: str,
    hire_date,
    verifier_name: str,
    verifier_company: str | None,
    verifier_email: str,
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

    c.setFont("Helvetica", 11)
    line_height = 14

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
    info_lines = [
        f"Employee Name: {employee_name}",
        f"Hire Date: {hire_date_str}",
        f"{title_label}: {job_title}",
    ]
    if include_salary and salary_amount is not None:
        info_lines.append(f"Annual Base Salary: ${salary_amount:,.2f}")
    for line in info_lines:
        c.drawString(x_left, y, line)
        y -= line_height + 4
    y -= 2

    contact_intro = (
        "If you have any questions or need any additional information, "
        "please feel free to contact me at"
    )
    for line in textwrap.wrap(contact_intro, width=90):
        c.drawString(x_left, y, line)
        y -= line_height

    contact_phone = _format_phone_for_sentence(settings.verification_phone)
    contact_email = settings.verification_signer_email or settings.payroll_contact_email
    if contact_phone:
        contact_line = f"{contact_phone} or you can reach me by email at {contact_email}."
    else:
        contact_line = f"You can reach me by email at {contact_email}."
    for line in textwrap.wrap(contact_line, width=90):
        c.drawString(x_left, y, line)
        y -= line_height

    y -= line_height
    c.drawString(x_left, y, "Sincerely,")
    y -= line_height * 2

    signer_name = settings.verification_signer_name
    signer_credentials = settings.verification_signer_credentials.strip()
    c.drawString(x_left, y, signer_name)
    y -= line_height * 2

    if signer_credentials:
        c.drawString(x_left, y, f"{signer_name}, {signer_credentials}")
    else:
        c.drawString(x_left, y, signer_name)
    y -= line_height

    if settings.verification_signer_title:
        c.drawString(x_left, y, settings.verification_signer_title)

    footer_address = settings.verification_footer_address or settings.company_address
    footer_phone = settings.verification_phone
    footer_fax = settings.verification_fax
    footer_email = contact_email

    footer_y = 72
    c.setFont("Helvetica", 9)
    if footer_address:
        c.drawCentredString(page_width / 2, footer_y + 24, f"* {footer_address}")
    if footer_phone:
        phone_fax = f"Phone {footer_phone}"
        if footer_fax:
            phone_fax = f"{phone_fax} * Fax {footer_fax}"
        c.drawCentredString(page_width / 2, footer_y + 12, phone_fax)
    if footer_email:
        c.drawCentredString(page_width / 2, footer_y, footer_email)

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
