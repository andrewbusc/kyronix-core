from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class CompanyInfo(BaseModel):
    company_name: str = Field(min_length=1)
    company_logo_url: HttpUrl | None = None
    company_address: str = Field(min_length=1)
    payroll_contact_email: EmailStr

    model_config = ConfigDict(extra="forbid")


class EmployeeInfo(BaseModel):
    employee_id: str = Field(min_length=1)
    employee_name: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    department: str = Field(min_length=1)
    employment_type: Literal["Full-Time", "Part-Time", "Contractor"]
    pay_type: Literal["Hourly", "Salary"]
    pay_rate: Decimal

    model_config = ConfigDict(extra="forbid")


class PayPeriodInfo(BaseModel):
    pay_period_start: date
    pay_period_end: date
    pay_date: date
    pay_frequency: Literal["Weekly", "Bi-Weekly", "Semi-Monthly", "Monthly"]

    model_config = ConfigDict(extra="forbid")


class EarningsItem(BaseModel):
    description: str = Field(min_length=1)
    hours: Decimal | None = None
    rate: Decimal | None = None
    current_amount: Decimal
    ytd_amount: Decimal

    model_config = ConfigDict(extra="forbid")


class DeductionItem(BaseModel):
    deduction_name: str = Field(min_length=1)
    current_amount: Decimal
    ytd_amount: Decimal

    model_config = ConfigDict(extra="forbid")


class TotalsInfo(BaseModel):
    gross_pay_current: Decimal
    total_deductions_current: Decimal
    net_pay_current: Decimal
    gross_pay_ytd: Decimal
    total_deductions_ytd: Decimal
    net_pay_ytd: Decimal

    model_config = ConfigDict(extra="forbid")


class LeaveBalancesInfo(BaseModel):
    vacation_accrued: Decimal
    vacation_used: Decimal
    vacation_balance: Decimal
    sick_accrued: Decimal
    sick_used: Decimal
    sick_balance: Decimal

    model_config = ConfigDict(extra="forbid")


class PaymentInfo(BaseModel):
    payment_method: Literal["Direct Deposit", "Check"]
    bank_name_masked: str = Field(min_length=1)
    payment_status: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class MetadataInfo(BaseModel):
    paystub_id: str = Field(min_length=1)
    generated_timestamp: datetime

    model_config = ConfigDict(extra="forbid")


class PaystubGenerateRequest(BaseModel):
    company: CompanyInfo
    employee: EmployeeInfo
    pay_period: PayPeriodInfo
    earnings: list[EarningsItem]
    deductions: list[DeductionItem]
    totals: TotalsInfo
    payment: PaymentInfo
    metadata: MetadataInfo
    leave_balances: LeaveBalancesInfo | None = None

    model_config = ConfigDict(extra="forbid")
