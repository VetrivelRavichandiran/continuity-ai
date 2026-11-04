from pydantic import BaseModel, Field


class EvidenceOut(BaseModel):
    document_id: int
    document_name: str
    chunk_id: int | None = None
    page: int | None = None
    excerpt: str


class RelationshipOut(BaseModel):
    type: str
    target_type: str | None = None
    target_id: int | None = None
    target_title: str | None = None


class KnowledgeItemOut(BaseModel):
    id: int
    project_id: int
    type: str
    title: str
    summary: str | None = None
    details: dict = Field(default_factory=dict)
    status: str | None = "pending"
    task_status: str | None = None
    severity: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    evidence_status: str
    review_status: str
    evidence: list[EvidenceOut] = Field(default_factory=list)
    relationships: list[RelationshipOut] = Field(default_factory=list)
    created_at: str
    updated_at: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class KnowledgePatch(BaseModel):
    title: str | None = None
    summary: str | None = None
    details: dict | None = None
    status: str | None = None
    task_status: str | None = None
    severity: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    dependencies: list[str] | None = None


class ReviewRequest(BaseModel):
    action: str  # approve | reject | flag | resolve_conflict
    reviewer: str | None = None
    note: str | None = None


class TimelineEntry(BaseModel):
    id: int
    date: str | None = None
    title: str
    type: str
    description: str | None = None
    evidence: list[EvidenceOut] = Field(default_factory=list)


class ConflictItemRef(BaseModel):
    id: int
    title: str
    type: str | None = None
    evidence: list[EvidenceOut] = Field(default_factory=list)


class ConflictOut(BaseModel):
    id: int
    project_id: int
    topic: str
    items: list[ConflictItemRef]