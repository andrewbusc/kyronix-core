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


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    legal_first_name: str | None = None
    legal_last_name: str | None = None
    preferred_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    hire_date: date | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None
    role: RoleEnum | None = None
    employment_status: EmploymentStatus | None = None
    is_active: bool | None = None


class AdminPasswordReset(BaseModel):
    new_password: str


class UserRead(UserBase):
    id: int
    role: RoleEnum
    employment_status: EmploymentStatus
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
