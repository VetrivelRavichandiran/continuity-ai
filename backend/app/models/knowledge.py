from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.project import utcnow

KNOWLEDGE_TYPES = ("decision", "task", "event", "risk", "question", "entity")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    details: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[str | None] = mapped_column(String(30), default="pending")
    task_status: Mapped[str | None] = mapped_column(String(20), default=None)
    severity: Mapped[str | None] = mapped_column(String(10), default=None)
    assignee: Mapped[str | None] = mapped_column(String(200), default=None)
    due_date: Mapped[str | None] = mapped_column(String(30), default=None)
    dependencies: Mapped[list | None] = mapped_column(JSON, default=list)
    evidence_status: Mapped[str] = mapped_column(String(20), default="unverified")
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    evidence: Mapped[list | None] = mapped_column(JSON, default=list)
    reviewed_by: Mapped[str | None] = mapped_column(String(200), default=None)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), default=None)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(40), default=utcnow)

    relationships = relationship(
        "Relationship", back_populates="knowledge_item", cascade="all, delete-orphan",
        passive_deletes=True, foreign_keys="Relationship.source_id",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "details": self.details or {},
            "status": self.status,
            "task_status": self.task_status,
            "severity": self.severity,
            "assignee": self.assignee,
            "due_date": self.due_date,
            "dependencies": self.dependencies or [],
            "evidence_status": self.evidence_status,
            "review_status": self.review_status,
            "evidence": self.evidence or [],
            "relationships": [r.to_dict() for r in self.relationships],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
        }


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_items.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("knowledge_items.id"), index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)

    knowledge_item = relationship("KnowledgeItem", back_populates="relationships",
                                  foreign_keys=[source_id])
    target = relationship("KnowledgeItem", foreign_keys=[target_id])

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "target_type": self.target.type if self.target else None,
            "target_id": self.target_id,
            "target_title": self.target.title if self.target else None,
        }


class Conflict(Base):
    __tablename__ = "conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    item_a: Mapped[int] = mapped_column(ForeignKey("knowledge_items.id"))
    item_b: Mapped[int] = mapped_column(ForeignKey("knowledge_items.id"))
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)

    item_a_obj = relationship("KnowledgeItem", foreign_keys=[item_a])
    item_b_obj = relationship("KnowledgeItem", foreign_keys=[item_b])

    def to_dict(self) -> dict:
        a, b = self.item_a_obj, self.item_b_obj
        return {
            "id": self.id,
            "project_id": self.project_id,
            "topic": self.topic,
            "items": [
                {
                    "id": a.id,
                    "title": a.title,
                    "type": a.type,
                    "evidence": a.evidence or [],
                },
                {
                    "id": b.id,
                    "title": b.title,
                    "type": b.type,
                    "evidence": b.evidence or [],
                },
            ],
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40), default=None)
    entity_id: Mapped[int | None] = mapped_column(Integer, default=None)
    entity_title: Mapped[str | None] = mapped_column(String(500), default=None)
    reviewer: Mapped[str | None] = mapped_column(String(200), default=None)
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_title": self.entity_title,
            "reviewer": self.reviewer,
            "detail": self.detail,
            "created_at": self.created_at,
        }


class Handover(Base):
    __tablename__ = "handovers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    project_name: Mapped[str] = mapped_column(String(300), default="")
    audience: Mapped[str] = mapped_column(String(20), default="general")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="generated")
    generated_at: Mapped[str] = mapped_column(String(40), default=utcnow)
    sections: Mapped[list | None] = mapped_column(JSON, default=list)
    summary: Mapped[dict | None] = mapped_column(JSON, default=dict)

    def to_dict(self, include_sections: bool = True) -> dict:
        d = {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "audience": self.audience,
            "version": self.version,
            "status": self.status,
            "generated_at": self.generated_at,
            "summary": self.summary or {},
        }
        if include_sections:
            d["sections"] = self.sections or []
        return d