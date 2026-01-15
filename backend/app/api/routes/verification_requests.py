from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles, require_write_access
from app.core.audit import log_verification_event, log_verification_events
from app.core.config import settings
from app.core.roles import EmploymentStatus, RoleEnum
from app.core.verification import VerificationRequestStatus
from app.db.models.employment_verification_request import EmploymentVerificationRequest
from app.db.models.user import User
from app.schemas.employment_verification import (
    EmploymentVerificationDecline,
    EmploymentVerificationGenerate,
    EmploymentVerificationMarkSent,
    EmploymentVerificationRequestCreate,
    EmploymentVerificationRequestRead,
)
from app.utils.employment_verification import (
    build_employment_verification_filename,
    render_employment_verification_pdf,
)
from app.utils.s3 import S3ConfigError, download_pdf_bytes, upload_pdf_bytes

router = APIRouter()


def build_employee_summary(user: User) -> dict:
    return {
        "id": user.id,
        "legal_first_name": user.legal_first_name,
        "legal_last_name": user.legal_last_name,
        "job_title": user.job_title,
        "department": user.department,
        "hire_date": user.hire_date,
        "employment_status": user.employment_status,
    }


def serialize_request(
    request: EmploymentVerificationRequest, employee: User | None = None
) -> EmploymentVerificationRequestRead:
    data = EmploymentVerificationRequestRead.model_validate(request)
    if employee:
        data.employee = build_employee_summary(employee)
    elif hasattr(request, "employee"):
        data.employee = build_employee_summary(request.employee)
    return data


def get_request_or_404(
    db: Session, request_id: int, current_user: User
) -> EmploymentVerificationRequest:
    request = db.get(EmploymentVerificationRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if current_user.role != RoleEnum.ADMIN and request.employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return request


@router.post("/", response_model=EmploymentVerificationRequestRead, status_code=status.HTTP_201_CREATED)
def create_verification_request(
    payload: EmploymentVerificationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.EMPLOYEE)),
    _write_access: User = Depends(require_write_access),
):
    if not payload.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Consent is required"
        )

    request = EmploymentVerificationRequest(
        employee_id=current_user.id,
        verifier_name=payload.verifier_name,
        verifier_company=payload.verifier_company,
        verifier_email=payload.verifier_email,
        purpose=payload.purpose,
        include_salary=payload.include_salary,
        consent=payload.consent,
        status=VerificationRequestStatus.PENDING,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    log_verification_event(
        db,
        user_id=current_user.id,
        request_id=request.id,
        event_type="verification_request_created",
        metadata={
            "include_salary": payload.include_salary,
            "verifier_email": payload.verifier_email,
        },
    )

    return serialize_request(request, current_user)


@router.get("/", response_model=list[EmploymentVerificationRequestRead])
def list_verification_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(EmploymentVerificationRequest)
    if current_user.role != RoleEnum.ADMIN:
        query = query.filter(EmploymentVerificationRequest.employee_id == current_user.id)
    requests = query.order_by(EmploymentVerificationRequest.created_at.desc()).all()

    if requests:
        log_verification_events(
            db,
            user_id=current_user.id,
            request_ids=[item.id for item in requests],
            event_type="verification_request_access",
            metadata={"via": "list"},
        )

    if current_user.role == RoleEnum.ADMIN:
        employee_ids = {item.employee_id for item in requests}
        employees = (
            db.query(User).filter(User.id.in_(employee_ids)).all() if employee_ids else []
        )
        employee_map = {employee.id: employee for employee in employees}
        return [
            serialize_request(item, employee_map.get(item.employee_id)) for item in requests
        ]

    return [serialize_request(item, current_user) for item in requests]


@router.post("/{request_id}/generate")
def generate_verification_letter(
    request_id: int,
    payload: EmploymentVerificationGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    request = get_request_or_404(db, request_id, current_user)
    if request.status == VerificationRequestStatus.SENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification letter has already been sent",
        )
    if request.status == VerificationRequestStatus.DECLINED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification request has been declined",
        )

    if request.include_salary:
        if payload.salary_amount is None or payload.salary_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salary amount is required for this request",
            )
    elif payload.salary_amount is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salary amount not permitted without employee request",
        )

    employee = db.get(User, request.employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    now = datetime.now(timezone.utc)
    generated_at_local = now.astimezone(ZoneInfo(settings.time_zone))
    filename = build_employment_verification_filename(
        employee.legal_last_name, generated_at_local
    )
    s3_key = (
        f"verification-requests/{employee.id}/"
        f"{generated_at_local.strftime('%Y%m%d')}_{request.id}.pdf"
    )

    pdf_bytes = render_employment_verification_pdf(
        employee_name=f"{employee.legal_first_name} {employee.legal_last_name}",
        job_title=employee.job_title,
        department=employee.department,
        employment_status=employee.employment_status.value,
        hire_date=employee.hire_date,
        verifier_name=request.verifier_name,
        verifier_company=request.verifier_company,
        verifier_email=request.verifier_email,
        purpose=request.purpose,
        include_salary=request.include_salary,
        salary_amount=payload.salary_amount,
        generated_at=generated_at_local,
        request_id=request.id,
        employee_id=employee.id,
    )

    try:
        upload_pdf_bytes(
            s3_key,
            pdf_bytes,
            metadata={
                "request_id": str(request.id),
                "employee_id": str(employee.id),
                "verifier_email": request.verifier_email,
                "generated_at": generated_at_local.isoformat(),
            },
        )
    except S3ConfigError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    request.status = VerificationRequestStatus.GENERATED
    request.generated_at = now
    request.generated_by_user_id = current_user.id
    request.salary_amount = payload.salary_amount if request.include_salary else None
    request.file_name = filename
    request.s3_key = s3_key
    db.commit()
    db.refresh(request)

    log_verification_event(
        db,
        user_id=current_user.id,
        request_id=request.id,
        event_type="verification_generation",
        metadata={
            "include_salary": request.include_salary,
            "generated_at": generated_at_local.isoformat(),
        },
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{request_id}/mark-sent", response_model=EmploymentVerificationRequestRead)
def mark_verification_sent(
    request_id: int,
    payload: EmploymentVerificationMarkSent,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    request = get_request_or_404(db, request_id, current_user)
    if request.status != VerificationRequestStatus.GENERATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only generated requests can be marked as sent",
        )

    request.status = VerificationRequestStatus.SENT
    request.sent_at = datetime.now(timezone.utc)
    request.sent_by_user_id = current_user.id
    request.sent_note = payload.sent_note.strip() if payload.sent_note else None
    db.commit()
    db.refresh(request)

    log_verification_event(
        db,
        user_id=current_user.id,
        request_id=request.id,
        event_type="verification_sent",
        metadata={"verifier_email": request.verifier_email, "sent_note": request.sent_note},
    )

    employee = db.get(User, request.employee_id)
    return serialize_request(request, employee)


@router.post("/{request_id}/decline", response_model=EmploymentVerificationRequestRead)
def decline_verification_request(
    request_id: int,
    payload: EmploymentVerificationDecline,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    request = get_request_or_404(db, request_id, current_user)
    if request.status == VerificationRequestStatus.SENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sent requests cannot be declined",
        )
    if request.status == VerificationRequestStatus.DECLINED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request has already been declined",
        )

    request.status = VerificationRequestStatus.DECLINED
    request.declined_at = datetime.now(timezone.utc)
    request.declined_by_user_id = current_user.id
    request.decline_reason = payload.decline_reason.strip() if payload.decline_reason else None
    db.commit()
    db.refresh(request)

    log_verification_event(
        db,
        user_id=current_user.id,
        request_id=request.id,
        event_type="verification_declined",
        metadata={"decline_reason": request.decline_reason},
    )

    employee = db.get(User, request.employee_id)
    return serialize_request(request, employee)


@router.get("/{request_id}/pdf")
def download_verification_letter(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = get_request_or_404(db, request_id, current_user)
    if request.status in {VerificationRequestStatus.PENDING, VerificationRequestStatus.DECLINED}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not available")
    if not request.s3_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not available")

    try:
        pdf_bytes = download_pdf_bytes(request.s3_key)
    except S3ConfigError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    log_verification_event(
        db,
        user_id=current_user.id,
        request_id=request.id,
        event_type="verification_download",
        metadata={"status": request.status.value},
    )

    filename = request.file_name or "employment_verification.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
