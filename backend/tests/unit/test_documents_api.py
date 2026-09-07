from unittest.mock import MagicMock, patch

import pytest

from app.api.documents import (
    delete_document,
    get_document_version,
    list_document_versions,
    list_documents,
    restore_document,
    update_document,
)
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
    create_snapshot.assert_called_once_with(
        db,
        document,
        changes={"title": "Новое название"},
    )
    query.with_for_update.assert_called_once()
    assert document.title == "Новое название"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(document)


def test_list_document_versions_returns_newest_first():
    document = MagicMock(id=7, is_deleted=False)
    versions = [MagicMock(version_number=3), MagicMock(version_number=2)]
    document_query = MagicMock()
    document_query.filter.return_value = document_query
    document_query.first.return_value = document
    versions_query = MagicMock()
    versions_query.filter.return_value = versions_query
    versions_query.order_by.return_value = versions_query
    versions_query.offset.return_value = versions_query
    versions_query.limit.return_value = versions_query
    versions_query.all.return_value = versions
    db = MagicMock()
    db.query.side_effect = [document_query, versions_query]

    result = list_document_versions(doc_id=document.id, db=db)

    assert result == versions
    versions_query.order_by.assert_called_once()


def test_get_document_version_returns_requested_snapshot():
    document = MagicMock(id=7, is_deleted=False)
    version = MagicMock(document_id=7, version_number=2)
    document_query = MagicMock()
    document_query.filter.return_value = document_query
    document_query.first.return_value = document
    version_query = MagicMock()
    version_query.filter.return_value = version_query
    version_query.first.return_value = version
    db = MagicMock()
    db.query.side_effect = [document_query, version_query]

    result = get_document_version(
        doc_id=document.id,
        version_number=version.version_number,
        db=db,
    )

    assert result is version
