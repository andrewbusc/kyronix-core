import io
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import settings


def build_employment_verification_filename(employee_last_name: str, generated_on: datetime) -> str:
    safe_last = "".join(ch for ch in employee_last_name.upper() if ch.isalnum() or ch == "_")
    if not safe_last:
        safe_last = "EMPLOYEE"
    date_part = generated_on.strftime("%Y%m%d")
    return f"KYRONIX_EMPLOYMENT_VERIFICATION_{safe_last}_{date_part}.pdf"


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

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_left, y, "Employment Verification Letter")
    y -= 24

    c.setFont("Helvetica", 11)
    c.drawString(x_left, y, settings.employer_legal_name)
    y -= 16
    c.drawString(x_left, y, settings.company_address)
    y -= 16
    c.drawString(x_left, y, f"Contact: {settings.payroll_contact_email}")
    y -= 20

    c.drawString(x_left, y, f"Date: {generated_at.strftime('%B %d, %Y')}")
    y -= 24

    c.drawString(x_left, y, f"To: {verifier_name}")
    y -= 16
    if verifier_company:
        c.drawString(x_left, y, verifier_company)
        y -= 16
    c.drawString(x_left, y, f"Email: {verifier_email}")
    y -= 24

    status_key = employment_status.upper()
    status_phrase = "is employed" if status_key == "ACTIVE" else "was employed"
    status_label = "Former Employee" if status_key == "FORMER_EMPLOYEE" else "Active"
    paragraph_1 = (
        f"This letter confirms that {employee_name} {status_phrase} by "
        f"{settings.employer_legal_name} as {job_title} in the {department} department."
    )
    paragraph_2 = f"Employment status: {status_label}. Hire date: {hire_date}."
    paragraph_3 = f"Purpose of verification: {purpose}."
    paragraph_4 = "This verification is provided at the employee's request."

    lines = []
    for paragraph in (paragraph_1, paragraph_2, paragraph_3, paragraph_4):
        lines.extend(textwrap.wrap(paragraph, width=88))
        lines.append("")

    if include_salary and salary_amount is not None:
        salary_line = f"Annual base salary: ${salary_amount:,.2f}."
        lines.extend(textwrap.wrap(salary_line, width=88))
        lines.append("")

    lines.append(f"For questions, contact {settings.payroll_contact_email}.")

    c.setFont("Helvetica", 11)
    text = c.beginText(x_left, y)
    for line in lines:
        text.textLine(line)
    c.drawText(text)

    c.setFont("Helvetica", 9)
    c.drawString(x_left, 24, "This document was generated electronically via Kyronix Core.")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
