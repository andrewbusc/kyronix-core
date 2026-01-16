import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.audit import log_document_event, log_document_events
from app.core.roles import EmploymentStatus, RoleEnum
from app.db.models.document import Document
from app.db.models.document_share import DocumentShare
from app.db.models.user import User
from app.schemas.document import DocumentCreate, DocumentRead, DocumentShareCreate, DocumentShareRead
from app.utils.pdf import render_document_pdf

router = APIRouter()


def get_document_or_404(db: Session, doc_id: int, current_user: User) -> Document:
    document = db.get(Document, doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if current_user.role != RoleEnum.ADMIN and document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return document


def normalize_datetime(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def get_share_or_404(
    db: Session, doc_id: int, share_id: int, current_user: User
) -> DocumentShare:
    get_document_or_404(db, doc_id, current_user)
    share = (
        db.query(DocumentShare)
        .filter(DocumentShare.id == share_id, DocumentShare.document_id == doc_id)
        .first()
    )
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    return share


@router.post("/", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    owner_id = payload.owner_id
    if owner_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="owner_id is required")

    owner = db.get(User, owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")

    document = Document(title=payload.title, body=payload.body or "", owner_id=owner_id)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/", response_model=list[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document)
    if current_user.role != RoleEnum.ADMIN:
        query = query.filter(Document.owner_id == current_user.id)
    documents = query.order_by(Document.id.desc()).all()

    if documents:
        log_document_events(
            db,
            user_id=current_user.id,
            document_ids=[document.id for document in documents],
            event_type="document_access",
            metadata={"via": "list"},
        )

    return documents


@router.get("/{doc_id}", response_model=DocumentRead)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id, current_user)
    log_document_event(
        db,
        user_id=current_user.id,
        document_id=document.id,
        event_type="document_access",
        metadata={"via": "detail"},
    )
    return document


@router.get("/{doc_id}/pdf")
def get_document_pdf(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id, current_user)
    pdf_bytes = render_document_pdf(document)
    log_document_event(
        db,
        user_id=current_user.id,
        document_id=document.id,
        event_type="document_generation",
        metadata={"format": "pdf"},
    )
    filename = f"document_{document.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/{doc_id}/shares", response_model=DocumentShareRead, status_code=status.HTTP_201_CREATED)
def create_document_share(
    doc_id: int,
    payload: DocumentShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    get_document_or_404(db, doc_id, current_user)
    expires_at = normalize_datetime(payload.expires_at)

    token = None
    for _ in range(5):
        candidate = secrets.token_urlsafe(32)
        existing = (
            db.query(DocumentShare).filter(DocumentShare.token == candidate).first()
        )
        if not existing:
            token = candidate
            break
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate share token",
        )

    share = DocumentShare(
        document_id=doc_id,
        token=token,
        created_by_user_id=current_user.id,
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share


@router.get("/{doc_id}/shares", response_model=list[DocumentShareRead])
def list_document_shares(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    get_document_or_404(db, doc_id, current_user)
    return (
        db.query(DocumentShare)
        .filter(DocumentShare.document_id == doc_id)
        .order_by(DocumentShare.created_at.desc())
        .all()
    )


@router.post("/{doc_id}/shares/{share_id}/revoke", response_model=DocumentShareRead)
def revoke_document_share(
    doc_id: int,
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN)),
):
    if current_user.employment_status == EmploymentStatus.FORMER_EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only access")

    share = get_share_or_404(db, doc_id, share_id, current_user)
    if not share.revoked_at:
        share.revoked_at = datetime.now(timezone.utc)
        db.add(share)
        db.commit()
        db.refresh(share)
    return share


@router.get("/shares/{token}/pdf")
def download_shared_document(token: str, db: Session = Depends(get_db)):
    share = db.query(DocumentShare).filter(DocumentShare.token == token).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")

    now = datetime.now(timezone.utc)
    expires_at = normalize_datetime(share.expires_at)
    if share.revoked_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link revoked")
    if expires_at and expires_at < now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")

    document = db.get(Document, share.document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pdf_bytes = render_document_pdf(document)
    filename = f"document_{document.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
