from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.verification import VerificationDeliveryMethod, VerificationRequestStatus
from app.db.base import Base


class EmploymentVerificationRequest(Base):
    __tablename__ = "employment_verification_requests"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    verifier_name = Column(String, nullable=False)
    verifier_company = Column(String, nullable=True)
    verifier_email = Column(String, nullable=True)
    purpose = Column(String, nullable=False)
    include_salary = Column(Boolean, nullable=False, default=False)
    consent = Column(Boolean, nullable=False, default=False)
    status = Column(
        Enum(VerificationRequestStatus, name="verification_request_status_enum"),
        nullable=False,
        default=VerificationRequestStatus.PENDING,
    )
    delivery_method = Column(
        Enum(VerificationDeliveryMethod, name="verification_delivery_method_enum"),
        nullable=False,
        default=VerificationDeliveryMethod.VERIFIER,
    )
    salary_amount = Column(Numeric(12, 2), nullable=True)
    generated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    sent_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sent_note = Column(Text, nullable=True)
    declined_at = Column(DateTime(timezone=True), nullable=True)
    declined_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decline_reason = Column(Text, nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String, nullable=True)
    s3_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
