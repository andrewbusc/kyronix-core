from typing import Any

from sqlalchemy.orm import Session

from app.db.models.audit_log import DocumentAuditLog
from app.db.models.paystub_audit_log import PaystubAuditLog
from app.db.models.paystub_generation_log import PaystubGenerationLog


def log_document_event(
    db: Session,
    *,
    user_id: int,
    document_id: int,
    event_type: str,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> None:
    record = DocumentAuditLog(
        user_id=user_id,
        document_id=document_id,
        event_type=event_type,
        event_metadata=metadata or {},
    )
    db.add(record)
    if commit:
        db.commit()


def log_document_events(
    db: Session,
    *,
    user_id: int,
    document_ids: list[int],
    event_type: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    records = [
        DocumentAuditLog(
            user_id=user_id,
            document_id=document_id,
            event_type=event_type,
            event_metadata=metadata or {},
        )
        for document_id in document_ids
    ]
    db.add_all(records)
    db.commit()


def log_paystub_event(
    db: Session,
    *,
    user_id: int,
    paystub_id: int,
    event_type: str,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> None:
    record = PaystubAuditLog(
        user_id=user_id,
        paystub_id=paystub_id,
        event_type=event_type,
        event_metadata=metadata or {},
    )
    db.add(record)
    if commit:
        db.commit()


def log_paystub_events(
    db: Session,
    *,
    user_id: int,
    paystub_ids: list[int],
    event_type: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    records = [
        PaystubAuditLog(
            user_id=user_id,
            paystub_id=paystub_id,
            event_type=event_type,
            event_metadata=metadata or {},
        )
        for paystub_id in paystub_ids
    ]
    db.add_all(records)
    db.commit()


def log_paystub_generation_event(
    db: Session,
    *,
    user_id: int,
    event_type: str,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> None:
    record = PaystubGenerationLog(
        user_id=user_id,
        event_type=event_type,
        event_metadata=metadata or {},
    )
    db.add(record)
    if commit:
        db.commit()
