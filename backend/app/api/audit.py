from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models import AuditLog
from app.schemas.audit import AuditOut
from app.api.projects import get_project_or_404

router = APIRouter(prefix="/api/projects", tags=["audit"])


@router.get("/{project_id}/audit", response_model=list[AuditOut])
def list_audit(project_id: int, limit: int = Query(default=50, ge=1, le=500),
               db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    entries = db.query(AuditLog).filter(AuditLog.project_id == project_id) \
        .order_by(AuditLog.id.desc()).limit(limit).all()
    return [e.to_dict() for e in entries]