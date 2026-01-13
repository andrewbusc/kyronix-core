import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import log_paystub_generation_event
from app.core.config import settings
from app.core.roles import EmploymentStatus, RoleEnum
from app.db.models.paystub import Paystub
from app.db.models.user import User
from app.schemas.paystub_generate import PaystubGenerateRequest
from app.utils.paystub_v1 import build_paystub_filename, render_paystub_v1_pdf
from app.utils.s3 import S3ConfigError, upload_pdf_bytes

router = APIRouter()


def resolve_user_for_paystub(db: Session, payload: PaystubGenerateRequest) -> User:
    digits = re.sub(r"\D", "", payload.employee.employee_id)
    if digits:
        numeric = int(digits)
        if numeric >= 800:
            candidate_id = numeric - 800
            user = db.get(User, candidate_id)
            if user:
                return user
        user = db.get(User, numeric)
        if user:
            return user

    parts = payload.employee.employee_name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = parts[-1]
        user = (
            db.query(User)
            .filter(User.legal_first_name == first_name, User.legal_last_name == last_name)
            .one_or_none()
        )
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to match employee_id to an existing user",
    )


def serialize_items(items: list) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]


@router.post("/generate")
def generate_paystub(
    payload: PaystubGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access"
        )

    if payload.company.company_name != settings.employer_legal_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"company_name must be {settings.employer_legal_name}",
        )

    employee_user = resolve_user_for_paystub(db, payload)
    pdf_bytes = render_paystub_v1_pdf(payload)
    filename = build_paystub_filename(payload)
    s3_key = (
        f"paystubs/{employee_user.id}/"
        f"{payload.pay_period.pay_date.strftime('%Y%m%d')}_{payload.metadata.paystub_id}.pdf"
    )

    try:
        upload_pdf_bytes(
            s3_key,
            pdf_bytes,
            metadata={
                "paystub_id": payload.metadata.paystub_id,
                "employee_id": payload.employee.employee_id,
                "employee_name": payload.employee.employee_name,
                "pay_date": payload.pay_period.pay_date.isoformat(),
            },
        )
    except S3ConfigError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    paystub = Paystub(
        user_id=employee_user.id,
        employee_first_name=employee_user.legal_first_name,
        employee_last_name=employee_user.legal_last_name,
        pay_period_start=payload.pay_period.pay_period_start,
        pay_period_end=payload.pay_period.pay_period_end,
        pay_date=payload.pay_period.pay_date,
        earnings=serialize_items(payload.earnings),
        deductions=serialize_items(payload.deductions),
        gross_pay=payload.totals.gross_pay_current,
        total_deductions=payload.totals.total_deductions_current,
        net_pay=payload.totals.net_pay_current,
        file_name=filename,
        s3_key=s3_key,
    )
    db.add(paystub)
    db.commit()
    db.refresh(paystub)

    log_paystub_generation_event(
        db,
        user_id=current_user.id,
        event_type="paystub_generation",
        metadata={
            "paystub_id": payload.metadata.paystub_id,
            "paystub_record_id": paystub.id,
            "employee_id": payload.employee.employee_id,
            "employee_name": payload.employee.employee_name,
            "pay_date": payload.pay_period.pay_date.isoformat(),
        },
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
