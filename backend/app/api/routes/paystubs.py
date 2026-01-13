import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import log_paystub_event, log_paystub_events
from app.db.models.paystub import Paystub
from app.db.models.user import User
from app.schemas.paystub import PaystubListResponse, PaystubSummary
from app.utils.pdf import render_paystub_pdf
from app.utils.s3 import S3ConfigError, download_pdf_bytes

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
    if paystub.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return paystub


@router.get("/", response_model=PaystubListResponse)
def list_paystubs(
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_query = db.query(Paystub).filter(Paystub.user_id == current_user.id)
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
