from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.sql import func

from app.db.base import Base


class Paystub(Base):
    __tablename__ = "paystubs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_first_name = Column(String, nullable=False)
    employee_last_name = Column(String, nullable=False)
    pay_period_start = Column(Date, nullable=False)
    pay_period_end = Column(Date, nullable=False)
    pay_date = Column(Date, nullable=False, index=True)
    earnings = Column(JSON, nullable=False, default=list)
    deductions = Column(JSON, nullable=False, default=list)
    gross_pay = Column(Numeric(12, 2), nullable=False, default=0)
    total_deductions = Column(Numeric(12, 2), nullable=False, default=0)
    net_pay = Column(Numeric(12, 2), nullable=False, default=0)
    file_name = Column(String, nullable=True)
    s3_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
