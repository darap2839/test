from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db_models import DocumentModel, DocumentVersionModel


VERSIONED_FIELDS = (
    "title",
    "description",
    "doc_type",
    "department",
    "role",
    "tags",
    "access_level",
    "content_text",
    "status",
)


def document_has_changes(document: DocumentModel, changes: dict) -> bool:
    """Проверить, содержит ли запрос реальные изменения версионируемых полей."""
    return any(
        field in VERSIONED_FIELDS and getattr(document, field) != value
        for field, value in changes.items()
    )


def get_changed_fields(document: DocumentModel, changes: dict) -> list[str]:
    """Вернуть изменённые версионируемые поля в стабильном порядке."""
    return [
        field
        for field in VERSIONED_FIELDS
        if field in changes and getattr(document, field) != changes[field]
    ]


def create_document_snapshot(
    db: Session,
    document: DocumentModel,
    changes: dict,
    changed_by_id: int | None = None,
) -> DocumentVersionModel:
    """Добавить в текущую транзакцию снимок документа перед изменением."""
    latest_version = (
        db.query(func.max(DocumentVersionModel.version_number))
        .filter(DocumentVersionModel.document_id == document.id)
        .scalar()
        or 0
    )
    snapshot = DocumentVersionModel(
        document_id=document.id,
        version_number=latest_version + 1,
        changed_fields=get_changed_fields(document, changes),
        changed_by_id=changed_by_id,
        **{field: getattr(document, field) for field in VERSIONED_FIELDS},
    )
    db.add(snapshot)
    return snapshot
