import re
import secrets
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.audit import log_paystub_event, log_paystub_events
from app.core.roles import EmploymentStatus, RoleEnum
from app.db.models.paystub import Paystub
from app.db.models.user import User
from app.schemas.paystub import PaystubListResponse, PaystubSummary
from app.utils.pdf import render_paystub_pdf
from app.utils.s3 import S3ConfigError, delete_pdf_bytes, download_pdf_bytes, upload_pdf_bytes

router = APIRouter()


def normalize_filename_value(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9-]", "", value.strip())
    return cleaned or "EMPLOYEE"


def build_paystub_filename(paystub: Paystub) -> str:
    last_name = normalize_filename_value(paystub.employee_last_name).upper()
    pay_date = paystub.pay_date.strftime("%Y%m%d")
    return f"KYRONIX_PAYSTUB_{last_name}_{pay_date}.pdf"


def get_paystub_or_404(db: Session, paystub_id: int, current_user: User) -> Paystub:
    paystub = db.get(Paystub, paystub_id)
    if not paystub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paystub not found")
    if current_user.role != RoleEnum.ADMIN and paystub.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return paystub


def is_pdf_file(upload: UploadFile) -> bool:
    if upload.content_type == "application/pdf":
        return True
    if upload.filename and upload.filename.lower().endswith(".pdf"):
        return True
    return False


@router.get("/", response_model=PaystubListResponse)
def list_paystubs(
    year: int | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id is not None and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if user_id is not None:
        target_user_id = user_id
        if not db.get(User, target_user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    else:
        target_user_id = current_user.id

    base_query = db.query(Paystub).filter(Paystub.user_id == target_user_id)
    query = base_query
    if year is not None:
        query = query.filter(extract("year", Paystub.pay_date) == year)

    paystubs = query.order_by(Paystub.pay_date.desc()).all()

    year_rows = (
        base_query.with_entities(extract("year", Paystub.pay_date).label("year"))
        .distinct()
        .order_by(extract("year", Paystub.pay_date).desc())
        .all()
    )
    available_years = [int(row.year) for row in year_rows if row.year is not None]

    items = [
        PaystubSummary(
            id=paystub.id,
            pay_date=paystub.pay_date,
            pay_period_start=paystub.pay_period_start,
            pay_period_end=paystub.pay_period_end,
            file_name=paystub.file_name or build_paystub_filename(paystub),
        )
        for paystub in paystubs
    ]

    if paystubs:
        log_paystub_events(
            db,
            user_id=current_user.id,
            paystub_ids=[paystub.id for paystub in paystubs],
            event_type="paystub_access",
            metadata={"via": "list"},
        )

    return PaystubListResponse(items=items, available_years=available_years)


@router.get("/{paystub_id}/pdf")
def get_paystub_pdf(
    paystub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paystub = get_paystub_or_404(db, paystub_id, current_user)
    if paystub.s3_key:
        try:
            pdf_bytes = download_pdf_bytes(paystub.s3_key)
        except S3ConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
    else:
        pdf_bytes = render_paystub_pdf(paystub)
    log_paystub_event(
        db,
        user_id=current_user.id,
        paystub_id=paystub.id,
        event_type="paystub_generation",
        metadata={"format": "pdf"},
    )
    filename = paystub.file_name or build_paystub_filename(paystub)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/upload", response_model=PaystubSummary, status_code=status.HTTP_201_CREATED)
def upload_paystub(
    user_id: int = Form(...),
    pay_date: str = Form(...),
    pay_period_start: str = Form(...),
    pay_period_end: str = Form(...),
    file: UploadFile = File(...),
    file_name: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    if not is_pdf_file(file):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF file required")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        file_bytes = file.file.read()
    finally:
        file.file.close()

    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        pay_date_value = date.fromisoformat(pay_date)
        pay_period_start_value = date.fromisoformat(pay_period_start)
        pay_period_end_value = date.fromisoformat(pay_period_end)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD.",
        ) from exc

    s3_key = (
        f"paystubs/{user_id}/"
        f"uploaded_{pay_date_value.strftime('%Y%m%d')}_{secrets.token_hex(4)}.pdf"
    )

    try:
        upload_pdf_bytes(
            s3_key,
            file_bytes,
            metadata={"user_id": str(user_id), "uploaded_by": str(current_user.id)},
        )
    except S3ConfigError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    paystub = Paystub(
        user_id=user_id,
        employee_first_name=user.legal_first_name,
        employee_last_name=user.legal_last_name,
        pay_period_start=pay_period_start_value,
        pay_period_end=pay_period_end_value,
        pay_date=pay_date_value,
        earnings=[],
        deductions=[],
        gross_pay=0,
        total_deductions=0,
        net_pay=0,
        file_name=file_name or file.filename or None,
        s3_key=s3_key,
    )
    db.add(paystub)
    db.commit()
    db.refresh(paystub)

    log_paystub_event(
        db,
        user_id=current_user.id,
        paystub_id=paystub.id,
        event_type="paystub_upload",
        metadata={"user_id": user_id},
    )

    return PaystubSummary(
        id=paystub.id,
        pay_date=paystub.pay_date,
        pay_period_start=paystub.pay_period_start,
        pay_period_end=paystub.pay_period_end,
        file_name=paystub.file_name or build_paystub_filename(paystub),
    )


@router.delete("/{paystub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paystub(
    paystub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    paystub = db.get(Paystub, paystub_id)
    if not paystub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paystub not found")

    if paystub.s3_key:
        try:
            delete_pdf_bytes(paystub.s3_key)
        except S3ConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc

    db.delete(paystub)
    db.commit()
