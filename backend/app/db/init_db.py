from sqlalchemy.orm import Session

from app.core.config import settings
from datetime import date

from app.core.roles import EmploymentStatus, RoleEnum
from app.core.security import get_password_hash
from app.db import models
from app.db.base import Base
from app.db.models.user import User
from app.db.session import engine, SessionLocal


def create_admin(db: Session) -> None:
    existing = db.query(User).filter(User.email == settings.default_admin_email).first()
    if existing:
        return

    admin = User(
        email=settings.default_admin_email,
        hashed_password=get_password_hash(settings.default_admin_password),
        legal_first_name="Admin",
        legal_last_name="User",
        preferred_name=None,
        job_title="Administrator",
        department="HR",
        hire_date=date.today(),
        phone=None,
        address_line1="Not provided",
        address_line2=None,
        city="Not provided",
        state="Not provided",
        postal_code="Not provided",
        country="Not provided",
        emergency_contact_name="Not provided",
        emergency_contact_phone="Not provided",
        emergency_contact_relationship="Not provided",
        role=RoleEnum.ADMIN,
        employment_status=EmploymentStatus.ACTIVE,
        is_active=True,
    )
    db.add(admin)
    db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_admin(db)
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
