"""Documents API - База знаний"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from app.database import get_db
from app.models.db_models import DocumentModel, DocumentVersionModel
from app.schemas.document import (
    DocumentResponse,
    DocumentCreate,
    DocumentUpdate,
    DocumentType,
    DocumentStatus,
    DocumentVersionResponse,
    DocumentVersionSummary,
)
from app.services.minio_service import minio_service
from app.services.text_extraction_service import text_extraction_service
from app.services.document_version_service import create_document_snapshot, document_has_changes

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/preview")
def preview_document(file: UploadFile = File(...)):
    """Извлечь редактируемые данные из файла без создания документа."""
    try:
        filename = file.filename or ""
        extension = Path(filename).suffix.lower()
        if extension not in {".pdf", ".docx", ".txt"}:
            raise HTTPException(
                status_code=415,
                detail="Поддерживаются только файлы PDF, DOCX и TXT",
            )

        file_bytes = file.file.read()
        if not file_bytes:
            raise HTTPException(status_code=422, detail="Загруженный файл пуст")

        content_text = text_extraction_service.extract_text(file_bytes, filename)
        if not content_text or not content_text.strip():
            raise HTTPException(
                status_code=422,
                detail="Не удалось извлечь текст. Проверьте, что документ содержит распознаваемый текст",
            )

        return {
            "title": Path(filename).stem,
            "content_text": content_text.strip(),
            "file_name": filename,
            "file_size": len(file_bytes),
            "mime_type": file.content_type,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Не удалось обработать файл: {exc}") from exc


@router.post("", response_model=DocumentResponse)
def create_document(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    doc_type: str = Form("guide"),
    department: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    tags: Optional[str] = Form(""),
    access_level: str = Form("public"),
    content_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Создать документ с загрузкой файла в MinIO"""
    try:
        # Валидируем doc_type
        valid_doc_types = ["policy", "procedure", "role_profile", "template", "guide"]
        if doc_type not in valid_doc_types:
            doc_type = "guide"
        
        file_path = None
        file_name = file.filename if file else None
        file_size = file.size if file else None
        mime_type = file.content_type if file else None
        
        if file:
            file_bytes = file.file.read()
            file_size = len(file_bytes)
            
            file_path = minio_service.upload_file(
                file_bytes, 
                file_name or "unnamed",
                mime_type or "application/octet-stream"
            )
            
            if file_path:
                print(f"✅ File uploaded to MinIO: {file_path}")
                if content_text is None:
                    content_text = text_extraction_service.extract_text(file_bytes, file_name or "")
                if content_text:
                    print(f"✅ Text extracted: {len(content_text)} chars")
        
        db_doc = DocumentModel(
            title=title,
            description=description,
            doc_type=doc_type,
            department=department,
            role=role,
            tags=tags,
            access_level=access_level,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            content_text=content_text,
            status="draft"
        )
        
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        return db_doc
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    doc_type: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    archived: Optional[bool] = None,
    deleted: bool = False,
    search: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Список документов с фильтрацией"""
    query = db.query(DocumentModel).filter(
        DocumentModel.is_deleted == deleted,
        DocumentModel.file_path.isnot(None),
    )
    
    if doc_type:
        try:
            query = query.filter(DocumentModel.doc_type == DocumentType(doc_type))
        except ValueError:
            pass
    
    if department:
        query = query.filter(DocumentModel.department == department)
    
    if archived is not None:
        if archived:
            query = query.filter(DocumentModel.status == "archived")
        else:
            query = query.filter(DocumentModel.status != "archived")
    elif status:
        query = query.filter(DocumentModel.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (DocumentModel.title.ilike(search_term)) | 
            (DocumentModel.description.ilike(search_term)) |
            (DocumentModel.tags.ilike(search_term))
        )
    
    docs = query.offset(offset).limit(limit).all()
    return [doc for doc in docs if minio_service.file_exists(doc.file_path)]


@router.get("/{doc_id}/file")
def get_document_file(
    doc_id: int,
    download: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Открыть или скачать исходный файл документа."""
    doc = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.file_path:
        raise HTTPException(status_code=404, detail="У документа нет загруженного файла")

    file_bytes = minio_service.download_file(doc.file_path)
    if file_bytes is None:
        raise HTTPException(status_code=502, detail="Не удалось получить файл из хранилища")

    disposition = "attachment" if download else "inline"
    encoded_name = quote(doc.file_name or f"document-{doc.id}")
    return Response(
        content=file_bytes,
        media_type=doc.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_name}",
            "Content-Length": str(len(file_bytes)),
        },
    )


@router.put("/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
):
    """Обновить метаданные и извлечённый текст документа."""
    doc = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    ).with_for_update().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    changes = payload.model_dump(exclude_unset=True)
    if document_has_changes(doc, changes):
        create_document_snapshot(db, doc, changes=changes)
        for field, value in changes.items():
            setattr(doc, field, value)

    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{doc_id}/versions", response_model=List[DocumentVersionSummary])
def list_document_versions(
    doc_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Получить краткую историю документа без содержимого версий."""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return (
        db.query(DocumentVersionModel)
        .filter(DocumentVersionModel.document_id == doc_id)
        .order_by(DocumentVersionModel.version_number.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{doc_id}/versions/{version_number}", response_model=DocumentVersionResponse)
def get_document_version(
    doc_id: int,
    version_number: int,
    db: Session = Depends(get_db),
):
    """Получить полный снимок выбранной версии документа."""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    version = db.query(DocumentVersionModel).filter(
        DocumentVersionModel.document_id == doc_id,
        DocumentVersionModel.version_number == version_number,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found")
    return version


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    """Получить документ по ID"""
    doc = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc


@router.post("/{doc_id}/publish")
def publish_document(doc_id: int, db: Session = Depends(get_db)):
    """Опубликовать документ"""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.status = DocumentStatus.published
    doc.published_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """Удалить документ (мягкое удаление)"""
    doc = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.is_deleted = True
    db.commit()
    
    return {"status": "deleted", "id": doc_id}


@router.post("/{doc_id}/restore", response_model=DocumentResponse)
def restore_document(doc_id: int, db: Session = Depends(get_db)):
    """Восстановить мягко удалённый документ вместе с исходным статусом."""
    doc = db.query(DocumentModel).filter(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == True,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Deleted document not found")
    if not doc.file_path or not minio_service.file_exists(doc.file_path):
        raise HTTPException(status_code=409, detail="Исходный файл документа недоступен")

    doc.is_deleted = False
    db.commit()
    db.refresh(doc)
    return doc
