import io
from decimal import Decimal, ROUND_HALF_UP

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.schemas.paystub_generate import PaystubGenerateRequest


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_amount(
    value: Decimal | None,
    *,
    currency: bool = False,
    force_negative: bool = False,
) -> str:
    if value is None:
        return ""
    normalized = _quantize(value)
    if force_negative:
        normalized = -abs(normalized)
    prefix = "$" if currency else ""
    if normalized < 0:
        return f"{prefix}-{abs(normalized):,.2f}"
    return f"{prefix}{normalized:,.2f}"


def _draw_line(c: canvas.Canvas, x1: float, y: float, x2: float) -> None:
    c.setLineWidth(0.5)
    c.line(x1, y, x2, y)


def render_paystub_adp_classic_pdf(payload: PaystubGenerateRequest) -> bytes:
    adp_data = payload.template_data.adp_classic if payload.template_data else None
    tax_profile = adp_data.tax_profile if adp_data else None
    other_benefits = adp_data.other_benefits if adp_data else []
    deposits = adp_data.deposits if adp_data else []
    net_adjustments = adp_data.net_pay_adjustments if adp_data else []

    statutory = [
        item
        for item in payload.deductions
        if item.category in (None, "Statutory Deductions")
    ]
    voluntary = [item for item in payload.deductions if item.category == "Voluntary Deductions"]

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(f"{payload.company.company_name} Earnings Statement")
    c.setAuthor(payload.company.company_name)
    c.setSubject(f"Paystub ID: {payload.metadata.paystub_id}")

    page_width, page_height = letter
    margin = 34
    content_right = page_width - margin

    y = page_height - 30
    c.setFont("Helvetica-Bold", 7)
    c.drawString(margin, y, "Company Code")
    c.drawString(margin + 92, y, "Loc/Dept")
    c.drawString(margin + 176, y, "Number")
    c.drawString(margin + 228, y, "Page")

    y -= 10
    c.setFont("Helvetica", 7)
    c.drawString(margin, y, (tax_profile.company_code if tax_profile else None) or "N/A")
    c.drawString(
        margin + 92,
        y,
        (tax_profile.location_department if tax_profile else None) or payload.employee.department,
    )
    c.drawString(margin + 176, y, (tax_profile.check_number if tax_profile else None) or "N/A")
    c.drawString(margin + 228, y, "1 of 1")

    c.setFont("Helvetica-Bold", 19)
    c.drawRightString(content_right - 6, page_height - 42, "ADP")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(page_width / 2 + 46, page_height - 34, "Earnings Statement")

    c.setFont("Helvetica", 7)
    c.drawString(page_width / 2 + 20, page_height - 52, f"Period Starting: {payload.pay_period.pay_period_start:%m/%d/%Y}")
    c.drawString(page_width / 2 + 20, page_height - 61, f"Period Ending:   {payload.pay_period.pay_period_end:%m/%d/%Y}")
    c.drawString(page_width / 2 + 20, page_height - 70, f"Pay Date:        {payload.pay_period.pay_date:%m/%d/%Y}")

    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(margin, page_height - 56, payload.company.company_name)
    c.setFont("Helvetica", 8)
    address_lines = [line.strip() for line in payload.company.company_address.splitlines() if line.strip()]
    company_y = page_height - 66
    for line in address_lines[:3]:
        c.drawString(margin, company_y, line)
        company_y -= 9

    y = page_height - 126
    c.setFont("Helvetica", 7)
    c.drawString(margin - 4, y, f"Taxable Marital Status:    {(tax_profile.marital_status if tax_profile else 'Not provided')}")
    y -= 10
    c.drawString(margin - 4, y, "Exemptions/Allowances:")
    c.drawString(margin + 84, y, "Tax Override:")
    y -= 9
    c.drawString(
        margin + 10,
        y,
        f"Federal:  {tax_profile.federal_allowances if tax_profile and tax_profile.federal_allowances is not None else 0}",
    )
    c.drawString(
        margin + 92,
        y,
        f"Federal:  {(tax_profile.federal_tax_override if tax_profile else None) or '-'}",
    )
    y -= 9
    c.drawString(
        margin + 10,
        y,
        f"State:    {tax_profile.state_allowances if tax_profile and tax_profile.state_allowances is not None else 0}",
    )
    c.drawString(
        margin + 92,
        y,
        f"State:    {(tax_profile.state_tax_override if tax_profile else None) or '-'}",
    )
    y -= 9
    c.drawString(
        margin + 10,
        y,
        f"Local:    {tax_profile.local_allowances if tax_profile and tax_profile.local_allowances is not None else 0}",
    )
    c.drawString(
        margin + 92,
        y,
        f"Local:    {(tax_profile.local_tax_override if tax_profile else None) or '-'}",
    )
    y -= 9
    c.drawString(
        margin - 4,
        y,
        f"Social Security Number:    {(tax_profile.social_security_number_masked if tax_profile else None) or 'XXX-XX-0000'}",
    )

    employee_address = (
        [line for line in (tax_profile.employee_address_lines if tax_profile else []) if line.strip()]
        or [
            payload.employee.employee_name,
        ]
    )
    employee_block_x = page_width / 2 + 20
    employee_block_y = page_height - 128
    c.setFont("Helvetica-Bold", 10)
    c.drawString(employee_block_x, employee_block_y, payload.employee.employee_name)
    c.setFont("Helvetica-Bold", 9)
    line_y = employee_block_y - 14
    for line in employee_address[:3]:
        c.drawString(employee_block_x, line_y, line)
        line_y -= 12

    main_top = page_height - 202
    left_col = margin - 2
    right_col = page_width / 2 + 14
    c.setFont("Helvetica-Bold", 7)
    c.drawString(left_col, main_top, "Earnings")
    c.drawRightString(left_col + 132, main_top, "rate")
    c.drawRightString(left_col + 190, main_top, "hours/units")
    c.drawRightString(left_col + 266, main_top, "this period")
    c.drawRightString(left_col + 352, main_top, "year to date")

    c.drawString(right_col, main_top, "Other Benefits and")
    c.drawString(right_col, main_top - 9, "Information")
    c.drawRightString(content_right - 54, main_top, "this period")
    c.drawRightString(content_right, main_top, "year to date")
    _draw_line(c, margin - 2, main_top - 4, page_width / 2 + 6)
    _draw_line(c, right_col, main_top - 4, content_right)

    y_left = main_top - 16
    c.setFont("Helvetica", 7)
    for earning in payload.earnings[:8]:
        c.drawString(left_col, y_left, earning.description)
        c.drawRightString(left_col + 132, y_left, _format_amount(earning.rate))
        c.drawRightString(left_col + 190, y_left, _format_amount(earning.hours))
        c.drawRightString(left_col + 266, y_left, _format_amount(earning.current_amount))
        c.drawRightString(left_col + 352, y_left, _format_amount(earning.ytd_amount))
        y_left -= 10

    y_right = main_top - 16
    for benefit in other_benefits[:8]:
        c.drawString(right_col, y_right, benefit.description)
        c.drawRightString(content_right - 54, y_right, _format_amount(benefit.current_amount))
        c.drawRightString(content_right, y_right, _format_amount(benefit.ytd_amount))
        y_right -= 10

    gross_y = min(y_left, y_right) - 2
    _draw_line(c, margin - 2, gross_y + 8, content_right)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left_col + 52, gross_y, "Gross Pay")
    c.drawRightString(left_col + 266, gross_y, _format_amount(payload.totals.gross_pay_current, currency=True))
    c.drawRightString(left_col + 352, gross_y, _format_amount(payload.totals.gross_pay_ytd, currency=True))

    if deposits:
        c.setFont("Helvetica-Bold", 7)
        c.drawString(right_col, gross_y + 2, "Deposits")
        c.drawString(right_col, gross_y - 6, "account number")
        c.drawString(right_col + 104, gross_y - 6, "transit/ABA")
        c.drawRightString(content_right, gross_y - 6, "amount")
        _draw_line(c, right_col, gross_y - 9, content_right)

        deposit_y = gross_y - 18
        c.setFont("Helvetica", 7)
        for deposit in deposits[:4]:
            c.drawString(right_col, deposit_y, deposit.account_number_masked)
            c.drawString(right_col + 104, deposit_y, deposit.transit_aba_masked or "")
            c.drawRightString(content_right, deposit_y, _format_amount(deposit.amount))
            deposit_y -= 9

    y = gross_y - 18

    def draw_deduction_group(title: str, rows: list, start_y: float) -> float:
        c.setFont("Helvetica-Bold", 7)
        c.drawString(left_col + 24, start_y, title)
        c.drawRightString(left_col + 266, start_y, "this period")
        c.drawRightString(left_col + 352, start_y, "year to date")
        _draw_line(c, left_col + 20, start_y - 2, left_col + 356)
        row_y = start_y - 11
        c.setFont("Helvetica", 7)
        for row in rows[:6]:
            c.drawString(left_col + 24, row_y, row.deduction_name)
            c.drawRightString(
                left_col + 266,
                row_y,
                _format_amount(row.current_amount, force_negative=True),
            )
            c.drawRightString(
                left_col + 352,
                row_y,
                _format_amount(row.ytd_amount, force_negative=True),
            )
            row_y -= 9
        return row_y

    if statutory:
        y = draw_deduction_group("Statutory Deductions", statutory, y)
    if voluntary:
        y = draw_deduction_group("Voluntary Deductions", voluntary, y - 4)
    if net_adjustments:
        c.setFont("Helvetica-Bold", 7)
        c.drawString(left_col + 24, y - 4, "Net Pay Adjustments")
        c.drawRightString(left_col + 266, y - 4, "this period")
        c.drawRightString(left_col + 352, y - 4, "year to date")
        _draw_line(c, left_col + 20, y - 6, left_col + 356)
        row_y = y - 15
        c.setFont("Helvetica", 7)
        for row in net_adjustments[:4]:
            c.drawString(left_col + 24, row_y, row.description)
            c.drawRightString(left_col + 266, row_y, _format_amount(row.current_amount))
            c.drawRightString(left_col + 352, row_y, _format_amount(row.ytd_amount))
            row_y -= 9
        y = row_y

    y -= 2
    _draw_line(c, left_col + 20, y + 6, left_col + 356)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_col + 24, y - 2, "Net Pay")
    c.drawRightString(left_col + 266, y - 2, _format_amount(payload.totals.net_pay_current, currency=True))

    note_y = y - 14
    if adp_data and adp_data.federal_taxable_wages_current is not None:
        c.setFont("Helvetica", 7)
        c.drawString(
            right_col,
            note_y,
            f"Your federal taxable wages this period are {_format_amount(adp_data.federal_taxable_wages_current, currency=True)}",
        )
        if adp_data.exclusion_note:
            c.drawString(right_col, note_y - 9, adp_data.exclusion_note)

    bottom_top = 205
    _draw_line(c, margin - 6, bottom_top, content_right)
    c.setFont("Helvetica", 7)
    footer_company_y = bottom_top - 10
    c.drawString(margin - 4, footer_company_y, payload.company.company_name)
    footer_company_y -= 9
    for line in address_lines[:3]:
        c.drawString(margin - 4, footer_company_y, line)
        footer_company_y -= 8

    c.setFont("Helvetica-Bold", 11)
    c.saveState()
    c.translate(page_width / 2 + 26, 120)
    c.rotate(12)
    c.setFillGray(0.7)
    c.drawCentredString(0, 0, "THIS IS NOT A CHECK")
    c.restoreState()
    c.setFillGray(0.0)

    c.setFont("Helvetica-Bold", 8)
    c.drawString(page_width / 2 + 20, bottom_top - 16, "Pay Date:")
    c.setFont("Helvetica", 8)
    c.drawString(page_width / 2 + 104, bottom_top - 16, f"{payload.pay_period.pay_date:%m/%d/%Y}")

    c.setFont("Helvetica-Bold", 7)
    c.drawString(margin - 4, bottom_top - 52, "Deposited to the account")
    c.drawString(page_width / 2 + 20, bottom_top - 52, "account number")
    c.drawString(page_width / 2 + 125, bottom_top - 52, "transit/ABA")
    c.drawRightString(content_right, bottom_top - 52, "amount")
    _draw_line(c, page_width / 2 + 18, bottom_top - 54, content_right)

    dep_y = bottom_top - 64
    c.setFont("Helvetica", 7)
    display_deposits = deposits[:4] or []
    for deposit in display_deposits:
        c.drawString(margin - 4, dep_y, deposit.account_type or "Checking DirectDeposit")
        c.drawString(page_width / 2 + 20, dep_y, deposit.account_number_masked)
        c.drawString(page_width / 2 + 125, dep_y, deposit.transit_aba_masked or "")
        c.drawRightString(content_right, dep_y, _format_amount(deposit.amount))
        dep_y -= 9

    address_y = 56
    c.setFont("Helvetica", 10)
    c.drawString(margin + 46, address_y + 28, payload.employee.employee_name)
    c.setFont("Helvetica", 9)
    for line in employee_address[:3]:
        c.drawString(margin + 46, address_y + 16, line)
        address_y -= 12

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
