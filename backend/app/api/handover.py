import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models import Handover
from app.schemas.handover import HandoverCreate, HandoverMeta, HandoverOut
from app.services.handover import pdf as pdf_mod
from app.services.handover.builder import build_handover
from app.api.projects import get_project_or_404

router = APIRouter(tags=["handover"])


def _handover_out(h: Handover, include_sections: bool = True) -> dict:
    return h.to_dict(include_sections=include_sections)


@router.post("/api/projects/{project_id}/handovers",
             response_model=HandoverOut, status_code=201)
def create_handover(project_id: int, body: HandoverCreate, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    if body.audience not in ("general", "engineer"):
        raise HTTPException(status_code=400,
                            detail="audience must be 'general' or 'engineer'")
    handover = build_handover(db, project, body.audience)
    return _handover_out(handover, include_sections=True)


@router.get("/api/projects/{project_id}/handovers",
            response_model=list[HandoverMeta])
def list_handovers(project_id: int, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    handovers = db.query(Handover).filter(Handover.project_id == project_id) \
        .order_by(Handover.id).all()
    return [_handover_out(h, include_sections=False) for h in handovers]


@router.get("/api/handovers/{handover_id}", response_model=HandoverOut)
def get_handover(handover_id: int, db: Session = Depends(get_db)):
    handover = db.get(Handover, handover_id)
    if handover is None:
        raise HTTPException(status_code=404, detail="Handover not found")
    return _handover_out(handover, include_sections=True)


@router.get("/api/handovers/{handover_id}/download")
def download_handover(handover_id: int, db: Session = Depends(get_db)):
    handover = db.get(Handover, handover_id)
    if handover is None:
        raise HTTPException(status_code=404, detail="Handover not found")
    data = pdf_mod.render_pdf(handover.to_dict(include_sections=True),
                              handover.project_name)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", handover.project_name)[:60]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"CONTINUITY_AI_Handover_{safe_name}_{ts}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )