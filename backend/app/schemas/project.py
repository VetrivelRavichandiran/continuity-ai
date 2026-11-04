from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    objectives: list[str] = Field(default_factory=list)
    status: str = "active"


class ProjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    objectives: list[str] | None = None
    status: str | None = None


class ContinuityStats(BaseModel):
    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    blocked: int = 0
    total: int = 0
    percent: float | None = None
    available: bool = False


class ProjectStats(BaseModel):
    documents: int = 0
    decisions: int = 0
    tasks: int = 0
    open_tasks: int = 0
    risks: int = 0
    unresolved: int = 0
    pending_reviews: int = 0
    events: int = 0
    entities: int = 0
    conflicts: int = 0
    continuity: ContinuityStats = Field(default_factory=ContinuityStats)


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    category: str | None = None
    objectives: list[str] = Field(default_factory=list)
    status: str
    created_at: str
    updated_at: str
    stats: ProjectStats | None = None