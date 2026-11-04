from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str


class Citation(BaseModel):
    document_id: int
    document_name: str
    page: int | None = None
    excerpt: str


class RelatedItem(BaseModel):
    id: int
    type: str
    title: str


class AskResponse(BaseModel):
    question: str
    answer: str
    evidence_status: str
    confidence: float
    citations: list[Citation] = Field(default_factory=list)
    related: list[RelatedItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)