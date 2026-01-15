from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.sql import func

from app.db.base import Base


class EmploymentVerificationAuditLog(Base):
    __tablename__ = "employment_verification_audit_logs"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    event_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    request_id = Column(
        Integer, ForeignKey("employment_verification_requests.id", ondelete="CASCADE"), nullable=False
    )
