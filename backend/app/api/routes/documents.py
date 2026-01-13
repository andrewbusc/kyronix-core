from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.audit import log_document_event, log_document_events
from app.core.roles import EmploymentStatus, RoleEnum
from app.db.models.document import Document
from app.db.models.user import User
from app.schemas.document import DocumentCreate, DocumentRead
from app.utils.pdf import render_document_pdf

router = APIRouter()


def get_document_or_404(db: Session, doc_id: int, current_user: User) -> Document:
    document = db.get(Document, doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if current_user.role != RoleEnum.ADMIN and document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return document


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
