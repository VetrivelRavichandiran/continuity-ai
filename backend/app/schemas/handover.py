from pydantic import BaseModel, Field


class HandoverCreate(BaseModel):
    audience: str = "general"


class Section(BaseModel):
    key: str
    title: str
    content: str


class HandoverSummary(BaseModel):
    decisions: int = 0
    tasks: int = 0
    risks: int = 0
    unresolved: int = 0
    approved: int = 0
    pending: int = 0


class HandoverOut(BaseModel):
    id: int
    project_id: int
    project_name: str
    audience: str
    version: int
    status: str
    generated_at: str
    sections: list[Section] = Field(default_factory=list)
    summary: HandoverSummary = Field(default_factory=HandoverSummary)


class HandoverMeta(BaseModel):
    id: int
    project_id: int
    project_name: str
    audience: str
    version: int
    status: str
    generated_at: str
    summary: HandoverSummary = Field(default_factory=HandoverSummary)