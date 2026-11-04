from pydantic import BaseModel


class AuditOut(BaseModel):
    id: int
    project_id: int
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    entity_title: str | None = None
    reviewer: str | None = None
    detail: str | None = None
    created_at: str