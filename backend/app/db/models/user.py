from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from app.core.roles import EmploymentStatus, RoleEnum
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    legal_first_name = Column(String, nullable=False)
    legal_last_name = Column(String, nullable=False)
    preferred_name = Column(String, nullable=True)
    job_title = Column(String, nullable=False)
    department = Column(String, nullable=False)
    hire_date = Column(Date, nullable=False)
    phone = Column(String, nullable=True)
    address_line1 = Column(String, nullable=False)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    country = Column(String, nullable=False)
    emergency_contact_name = Column(String, nullable=False)
    emergency_contact_phone = Column(String, nullable=False)
    emergency_contact_relationship = Column(String, nullable=False)
    role = Column(Enum(RoleEnum, name="role_enum"), nullable=False, default=RoleEnum.EMPLOYEE)
    employment_status = Column(
        Enum(EmploymentStatus, name="employment_status_enum"),
        nullable=False,
        default=EmploymentStatus.ACTIVE,
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
