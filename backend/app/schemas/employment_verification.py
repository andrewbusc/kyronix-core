from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.roles import EmploymentStatus
from app.core.verification import VerificationDeliveryMethod, VerificationRequestStatus


class EmploymentVerificationRequestCreate(BaseModel):
    verifier_name: str
    verifier_company: str | None = None
    verifier_email: EmailStr
    purpose: str
    include_salary: bool = False
    consent: bool = Field(default=False, description="Employee consent required")


class EmploymentVerificationGenerate(BaseModel):
    salary_amount: float | None = None
    delivery_method: VerificationDeliveryMethod = VerificationDeliveryMethod.VERIFIER


class EmploymentVerificationMarkSent(BaseModel):
    sent_note: str | None = None


class EmploymentVerificationDecline(BaseModel):
    decline_reason: str | None = None


class EmploymentVerificationEmployee(BaseModel):
    id: int
    legal_first_name: str
    legal_last_name: str
    job_title: str
    department: str
    hire_date: date
    employment_status: EmploymentStatus


class EmploymentVerificationRequestRead(BaseModel):
    id: int
    employee_id: int
    verifier_name: str
    verifier_company: str | None
    verifier_email: EmailStr
    purpose: str
    include_salary: bool
    consent: bool
    status: VerificationRequestStatus
    delivery_method: VerificationDeliveryMethod
    salary_amount: float | None = None
    generated_by_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    generated_at: datetime | None = None
    sent_at: datetime | None = None
    sent_by_user_id: int | None = None
    sent_note: str | None = None
    declined_at: datetime | None = None
    declined_by_user_id: int | None = None
    decline_reason: str | None = None
    document_id: int | None = None
    file_name: str | None = None
    employee: EmploymentVerificationEmployee | None = None

    model_config = ConfigDict(from_attributes=True)
