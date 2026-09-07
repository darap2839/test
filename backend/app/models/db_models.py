from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class VacancyStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class ApplicationStage(str, enum.Enum):
    new = "new"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"


class CandidateStatus(str, enum.Enum):
    active = "active"
    reserve = "reserve"
    hired = "hired"


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    login = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Пока nullable для mock auth
    email = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="regular")  # regular, specialist, admin
    specialties = Column(Text, default="")  # Комма-разделенный список специализаций
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VacancyModel(Base):
    __tablename__ = "vacancies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(Text, default="")  # JSON-like string separated by commas
    salary_from = Column(Integer, nullable=True)
    salary_to = Column(Integer, nullable=True)
    status = Column(Enum(VacancyStatus), default=VacancyStatus.open)
    visibility = Column(String(50), default="public")  # public, specialist, internal
    required_specialty = Column(String(100), nullable=True)  # Требуемая специализация
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    applications = relationship("ApplicationModel", back_populates="vacancy", cascade="all, delete-orphan")


class CandidateModel(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    skills = Column(Text, default="")  # JSON-like string separated by commas
    experience_years = Column(Integer, default=0)
    resume_text = Column(Text, nullable=True)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    applications = relationship("ApplicationModel", back_populates="candidate", cascade="all, delete-orphan")


class ApplicationModel(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    stage = Column(Enum(ApplicationStage), default=ApplicationStage.new)
    ai_analysis = Column(Text, nullable=True)  # JSON-like analysis data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    candidate = relationship("CandidateModel", back_populates="applications")
    vacancy = relationship("VacancyModel", back_populates="applications")


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    
    # Типы документов - используем String вместо Enum для простоты
    doc_type = Column(String(50), nullable=False, default="guide")  # policy, procedure, role_profile, template, guide
    department = Column(String(100), index=True)  # Отдел-владелец (IT, HR, Finance)
    role = Column(String(100), index=True)  # Должность (для role_profile)
    
    status = Column(String(50), default="draft")  # draft, published, archived
    tags = Column(Text, default="")  # Комма-разделенный список тегов
    access_level = Column(String(50), default="public")  # public, department, private
    
    # Файл
    file_path = Column(String(500))  # Путь в MinIO
    file_name = Column(String(200))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # Для RAG: извлеченный текст
    content_text = Column(Text)
    
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False)

    author = relationship("UserModel", backref="documents")
    versions = relationship(
        "DocumentVersionModel",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersionModel.version_number.desc()",
    )


class DocumentVersionModel(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    doc_type = Column(String(50), nullable=False)
    department = Column(String(100))
    role = Column(String(100))
    tags = Column(Text, default="")
    access_level = Column(String(50), default="public")
    content_text = Column(Text)
    status = Column(String(50), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("DocumentModel", back_populates="versions")
    changed_by = relationship("UserModel")
