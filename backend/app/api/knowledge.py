import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models import AuditLog, Conflict, KnowledgeItem
from app.models.project import utcnow
from app.schemas.knowledge import (ConflictOut, KnowledgeItemOut, KnowledgePatch,
                                   ReviewRequest, TimelineEntry)
from app.api.projects import get_project_or_404

router = APIRouter(tags=["knowledge"])

VALID_TYPES = {"decision", "task", "event", "risk", "question", "entity"}
VALID_TASK_STATUSES = {"completed", "in_progress", "pending", "blocked"}
VALID_REVIEW = {"pending", "approved", "rejected", "flagged"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def _details_blob(item: KnowledgeItem) -> str:
    try:
        return json.dumps(item.details or {}, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        return ""


@router.get("/api/projects/{project_id}/knowledge", response_model=list[KnowledgeItemOut])
def list_knowledge(project_id: int,
                   type: str | None = Query(default=None),
                   status: str | None = Query(default=None),
                   review_status: str | None = Query(default=None),
                   q: str | None = Query(default=None),
                   sort: str = Query(default="created_at"),
                   order: str = Query(default="desc"),
                   db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    query = db.query(KnowledgeItem).filter(KnowledgeItem.project_id == project_id)
    if type and type != "all":
        if type not in VALID_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid type: {type}")
        query = query.filter(KnowledgeItem.type == type)
    if status:
        if status not in VALID_TASK_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query = query.filter(KnowledgeItem.task_status == status)
    if review_status:
        if review_status not in VALID_REVIEW:
            raise HTTPException(status_code=400, detail=f"Invalid review_status: {review_status}")
        query = query.filter(KnowledgeItem.review_status == review_status)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(or_(
            KnowledgeItem.title.ilike(like),
            KnowledgeItem.summary.ilike(like),
        ))
        # also match inside details JSON (SQLite stores JSON as text)
        items = query.all()
        if q:
            items = [i for i in items
                     if q.lower() in (i.title or "").lower()
                     or q.lower() in (i.summary or "").lower()
                     or q.lower() in _details_blob(i)]
    else:
        items = query.all()
    # detail-level q filtering is done above; sort
    sort_col = {
        "created_at": KnowledgeItem.created_at,
        "updated_at": KnowledgeItem.updated_at,
        "title": KnowledgeItem.title,
    }.get(sort, KnowledgeItem.created_at)
    items = sorted(items, key=lambda i: (getattr(i, sort_col.name) or ""),
                   reverse=(order != "asc"))
    return [i.to_dict() for i in items]


@router.get("/api/knowledge/{item_id}", response_model=KnowledgeItemOut)
def get_knowledge(item_id: int, db: Session = Depends(get_db)):
    item = db.get(KnowledgeItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return item.to_dict()


@router.patch("/api/knowledge/{item_id}", response_model=KnowledgeItemOut)
def patch_knowledge(item_id: int, body: KnowledgePatch, db: Session = Depends(get_db)):
    item = db.get(KnowledgeItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    data = body.model_dump(exclude_unset=True)
    if "task_status" in data and data["task_status"] is not None \
            and data["task_status"] not in VALID_TASK_STATUSES:
        raise HTTPException(status_code=400,
                            detail=f"Invalid task_status: {data['task_status']}")
    if "severity" in data and data["severity"] is not None \
            and data["severity"] not in VALID_SEVERITIES:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {data['severity']}")
    if "status" in data and data["status"] is not None \
            and data["status"] not in VALID_TASK_STATUSES | {"open", "pending", "closed"}:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")

    was_approved = item.review_status == "approved"
    changed = []
    for field, value in data.items():
        if field == "details":
            merged = dict(item.details or {})
            merged.update(value or {})
            item.details = merged
        else:
            setattr(item, field, value)
        changed.append(field)
    if was_approved and changed:
        item.review_status = "pending"
    item.updated_at = utcnow()
    db.add(AuditLog(project_id=item.project_id, action="record_edited",
                    entity_type="knowledge", entity_id=item.id,
                    entity_title=item.title,
                    detail="Record edited: " + ", ".join(changed)))
    db.commit()
    db.refresh(item)
    return item.to_dict()


@router.post("/api/knowledge/{item_id}/review", response_model=KnowledgeItemOut)
def review_knowledge(item_id: int, body: ReviewRequest, db: Session = Depends(get_db)):
    item = db.get(KnowledgeItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    action = body.action
    if action not in {"approve", "reject", "flag", "resolve_conflict"}:
        raise HTTPException(status_code=400,
                            detail="action must be approve | reject | flag | resolve_conflict")
    if action == "resolve_conflict" and not (body.note or "").strip():
        raise HTTPException(status_code=400,
                            detail="resolve_conflict requires a note explaining which side was kept")

    action_map = {
        "approve": ("approved", "record_approved"),
        "reject": ("rejected", "record_rejected"),
        "flag": ("flagged", "record_flagged"),
        "resolve_conflict": ("approved", "conflict_resolved"),
    }
    review_status, audit_action = action_map[action]
    item.review_status = review_status
    if action == "resolve_conflict":
        item.evidence_status = "supported"
    item.reviewed_by = body.reviewer
    item.reviewed_at = utcnow()
    item.updated_at = utcnow()
    db.add(AuditLog(project_id=item.project_id, action=audit_action,
                    entity_type="knowledge", entity_id=item.id,
                    entity_title=item.title, reviewer=body.reviewer,
                    detail=body.note))
    db.commit()
    db.refresh(item)
    return item.to_dict()


@router.get("/api/projects/{project_id}/timeline", response_model=list[TimelineEntry])
def timeline(project_id: int, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.project_id == project_id).all()
    entries = []
    for i in items:
        if i.type == "event":
            date = (i.details or {}).get("event_date")
            entries.append({
                "id": i.id, "date": date, "title": i.title, "type": "event",
                "description": (i.details or {}).get("description") or i.summary,
                "evidence": i.evidence or [],
                "_created": i.created_at,
            })
        elif i.type == "decision" and (i.details or {}).get("decided_on"):
            entries.append({
                "id": i.id, "date": i.details["decided_on"], "title": i.title,
                "type": "decision", "description": i.summary,
                "evidence": i.evidence or [],
                "_created": i.created_at,
            })
    entries.sort(key=lambda e: (e["date"] or "9999-12-31", e["_created"]))
    for e in entries:
        e.pop("_created", None)
    return entries


@router.get("/api/projects/{project_id}/conflicts", response_model=list[ConflictOut])
def list_conflicts(project_id: int, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    conflicts = db.query(Conflict).filter(Conflict.project_id == project_id).all()
    return [c.to_dict() for c in conflicts]