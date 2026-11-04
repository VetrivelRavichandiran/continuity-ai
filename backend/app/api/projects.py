from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models import (AuditLog, Chunk, Conflict, Document, Handover,
                        KnowledgeItem, Project, Relationship)
from app.models.project import utcnow
from app.schemas.project import ProjectCreate, ProjectOut, ProjectPatch

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def compute_stats(db: Session, project_id: int) -> dict:
    documents = db.query(func.count(Document.id)).filter(
        Document.project_id == project_id).scalar() or 0
    tasks = db.query(KnowledgeItem).filter(
        KnowledgeItem.project_id == project_id,
        KnowledgeItem.type == "task").all()
    completed = sum(1 for t in tasks if t.task_status == "completed")
    in_progress = sum(1 for t in tasks if t.task_status == "in_progress")
    pending = sum(1 for t in tasks if t.task_status == "pending")
    blocked = sum(1 for t in tasks if t.task_status == "blocked")
    total = len(tasks)
    continuity = {
        "completed": completed,
        "in_progress": in_progress,
        "pending": pending,
        "blocked": blocked,
        "total": total,
        "percent": round(100.0 * completed / total, 1) if total else None,
        "available": total > 0,
    }
    return {
        "documents": documents,
        "decisions": db.query(func.count(KnowledgeItem.id)).filter(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.type == "decision").scalar() or 0,
        "tasks": total,
        "open_tasks": total - completed,
        "risks": db.query(func.count(KnowledgeItem.id)).filter(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.type == "risk").scalar() or 0,
        "unresolved": db.query(func.count(KnowledgeItem.id)).filter(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.type == "question").scalar() or 0,
        "pending_reviews": db.query(func.count(KnowledgeItem.id)).filter(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.review_status == "pending").scalar() or 0,
        "events": db.query(func.count(KnowledgeItem.id)).filter(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.type == "event").scalar() or 0,
        "entities": db.query(func.count(KnowledgeItem.id)).filter(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.type == "entity").scalar() or 0,
        "conflicts": db.query(func.count(Conflict.id)).filter(
            Conflict.project_id == project_id).scalar() or 0,
        "continuity": continuity,
    }


def project_out(project: Project, db: Session) -> dict:
    d = project.to_dict()
    d["stats"] = compute_stats(db, project.id)
    return d


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=body.name,
        description=body.description,
        category=body.category,
        objectives=body.objectives or [],
        status=body.status or "active",
    )
    db.add(project)
    db.flush()
    db.add(AuditLog(project_id=project.id, action="project_created",
                    entity_type="project", entity_id=project.id,
                    entity_title=project.name, detail="Project created"))
    db.commit()
    db.refresh(project)
    return project_out(project, db)


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.id).all()
    return [project_out(p, db) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return project_out(get_project_or_404(db, project_id), db)


@router.patch("/{project_id}", response_model=ProjectOut)
def patch_project(project_id: int, body: ProjectPatch, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(project, field, value)
    project.updated_at = utcnow()
    db.commit()
    db.refresh(project)
    return project_out(project, db)


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    from app.api.documents import remove_project_files

    project = get_project_or_404(db, project_id)
    remove_project_files(project)
    db.delete(project)
    db.commit()
    return {"deleted": True}