from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.project import utcnow


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    error: Mapped[str | None] = mapped_column(Text, default=None)
    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str | None] = mapped_column(String(500), default=None)
    sha256: Mapped[str | None] = mapped_column(String(64), default=None)
    uploaded_at: Mapped[str] = mapped_column(String(40), default=utcnow)
    processed_at: Mapped[str | None] = mapped_column(String(40), default=None)

    project = relationship("Project", back_populates="documents")
    chunks = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "error": self.error,
            "page_count": self.page_count,
            "chunk_count": self.chunk_count,
            "uploaded_at": self.uploaded_at,
            "processed_at": self.processed_at,
        }


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    page: Mapped[int | None] = mapped_column(Integer, default=None)
    char_offset: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    document = relationship("Document", back_populates="chunks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "project_id": self.project_id,
            "page": self.page,
            "char_offset": self.char_offset,
            "text": self.text,
        }