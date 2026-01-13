from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.roles import EmploymentStatus, RoleEnum


class UserBase(BaseModel):
    email: EmailStr
    legal_first_name: str
    legal_last_name: str
    preferred_name: str | None = None
    job_title: str
    department: str
    hire_date: date
    phone: str | None = None
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_contact_relationship: str


class UserCreate(UserBase):
    password: str
    role: RoleEnum = RoleEnum.EMPLOYEE
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE


class UserRead(UserBase):
    id: int
    role: RoleEnum
    employment_status: EmploymentStatus
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
