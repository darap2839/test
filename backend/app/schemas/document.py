"""Document schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Annotated
from datetime import datetime


# String literals for document types and status
DocumentType = Literal["policy", "procedure", "role_profile", "template", "guide"]
DocumentStatus = Literal["draft", "published", "archived"]


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    doc_type: Annotated[DocumentType, Field(default="guide")] = "guide"
    department: Optional[str] = None
    role: Optional[str] = None
    tags: Optional[str] = ""
    access_level: str = "public"


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    doc_type: Optional[Annotated[DocumentType, Field(default="guide")]] = None
    department: Optional[str] = None
    role: Optional[str] = None
    tags: Optional[str] = None
    access_level: Optional[str] = None
    content_text: Optional[str] = None
    status: Optional[Annotated[DocumentStatus, Field(default="draft")]] = None


class DocumentResponse(DocumentBase):
    id: int
    status: Annotated[DocumentStatus, Field(default="draft")] = "draft"
    author_id: Optional[int] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    content_text: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    is_deleted: bool = False

    class Config:
        from_attributes = True


class DocumentVersionSummary(BaseModel):
    version_number: int
    changed_fields: List[str] = Field(default_factory=list)
    changed_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentVersionResponse(DocumentVersionSummary, DocumentBase):
    document_id: int
    content_text: Optional[str] = None
    status: Annotated[DocumentStatus, Field(default="draft")] = "draft"
