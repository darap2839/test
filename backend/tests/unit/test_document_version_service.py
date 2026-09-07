from unittest.mock import MagicMock

from app.services.document_version_service import (
    create_document_snapshot,
    document_has_changes,
    get_changed_fields,
)


def make_document():
    document = MagicMock()
    document.id = 7
    document.title = "Регламент"
    document.description = "Исходное описание"
    document.doc_type = "guide"
    document.department = "HR"
    document.role = None
    document.tags = "интервью"
    document.access_level = "public"
    document.content_text = "Исходный текст"
    document.status = "draft"
    return document


def test_document_has_changes_ignores_identical_values():
    document = make_document()

    assert document_has_changes(document, {"title": "Регламент"}) is False
    assert document_has_changes(document, {"title": "Новый регламент"}) is True
    assert get_changed_fields(
        document,
        {"content_text": "Новый текст", "title": "Новый регламент"},
    ) == ["title", "content_text"]


def test_create_document_snapshot_increments_version_and_copies_fields():
    document = make_document()
    query = MagicMock()
    query.filter.return_value = query
    query.scalar.return_value = 2
    db = MagicMock()
    db.query.return_value = query

    snapshot = create_document_snapshot(
        db,
        document,
        changes={"title": "Новый регламент", "department": "HR"},
        changed_by_id=15,
    )

    assert snapshot.document_id == document.id
    assert snapshot.version_number == 3
    assert snapshot.title == document.title
    assert snapshot.content_text == document.content_text
    assert snapshot.status == document.status
    assert snapshot.changed_fields == ["title"]
    assert snapshot.changed_by_id == 15
    db.add.assert_called_once_with(snapshot)
    db.commit.assert_not_called()
