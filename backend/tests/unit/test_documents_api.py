from unittest.mock import MagicMock, patch

import pytest

from app.api.documents import delete_document, list_documents, restore_document, update_document
from app.schemas.document import DocumentUpdate


@pytest.mark.parametrize(
    ("archived", "expected_operator"),
    [(False, "ne"), (True, "eq")],
)
def test_list_documents_applies_archive_scope(archived, expected_operator):
    query = MagicMock()
    query.filter.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    db = MagicMock()
    db.query.return_value = query

    with patch("app.api.documents.minio_service.file_exists"):
        result = list_documents(archived=archived, db=db)

    assert result == []
    archive_expression = query.filter.call_args_list[1].args[0]
    assert archive_expression.operator.__name__ == expected_operator
    assert archive_expression.right.value == "archived"


def test_delete_document_keeps_source_file_for_recovery():
    document = MagicMock(id=7, file_path="documents/source.pdf", is_deleted=False)
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = document
    db = MagicMock()
    db.query.return_value = query

    with patch("app.api.documents.minio_service.delete_file") as delete_file:
        result = delete_document(doc_id=document.id, db=db)

    assert result == {"status": "deleted", "id": document.id}
    assert document.is_deleted is True
    delete_file.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize("deleted", [False, True])
def test_list_documents_applies_deleted_scope(deleted):
    query = MagicMock()
    query.filter.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    db = MagicMock()
    db.query.return_value = query

    list_documents(deleted=deleted, db=db)

    deleted_expression = query.filter.call_args_list[0].args[0]
    assert deleted_expression.operator.__name__ == "eq"
    assert deleted_expression.right.value is deleted


def test_restore_document_preserves_previous_status():
    document = MagicMock(
        id=7,
        file_path="documents/source.pdf",
        is_deleted=True,
        status="archived",
    )
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = document
    db = MagicMock()
    db.query.return_value = query

    with patch("app.api.documents.minio_service.file_exists", return_value=True):
        result = restore_document(doc_id=document.id, db=db)

    assert result is document
    assert document.is_deleted is False
    assert document.status == "archived"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(document)


def test_update_document_snapshots_previous_state_before_changes():
    document = MagicMock(id=7, title="Старое название", is_deleted=False)
    query = MagicMock()
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = document
    db = MagicMock()
    db.query.return_value = query
    payload = DocumentUpdate(title="Новое название")

    with (
        patch("app.api.documents.document_has_changes", return_value=True),
        patch("app.api.documents.create_document_snapshot") as create_snapshot,
    ):
        result = update_document(doc_id=document.id, payload=payload, db=db)

    assert result is document
    create_snapshot.assert_called_once_with(db, document)
    query.with_for_update.assert_called_once()
    assert document.title == "Новое название"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(document)
