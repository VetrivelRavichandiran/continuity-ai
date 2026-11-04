import hashlib
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.db import get_db
from app.models import AuditLog, Chunk, Document, KnowledgeItem, Project, Relationship
from app.services.extraction.engine import (process_document_sync,
                                            submit_document_processing)
from app.schemas.document import DocumentOut, DocumentPreviewOut
from app.api.projects import get_project_or_404

router = APIRouter(tags=["documents"])


def _safe_name(name: str) -> str:
    name = Path(name).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "file"


def _store_file(project: Project, file_name: str, data: bytes) -> tuple[Path, str]:
    """Store under DATA_DIR/files/{project_id}/{sha256[:12]}_{original_name}."""
    settings = get_settings()
    dirpath = settings.files_dir / str(project.id)
    dirpath.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    dest = dirpath / f"{digest[:12]}_{_safe_name(file_name)}"
    dest.write_bytes(data)
    return dest, digest


def remove_project_files(project: Project) -> None:
    settings = get_settings()
    dirpath = settings.files_dir / str(project.id)
    if dirpath.exists():
        shutil.rmtree(dirpath, ignore_errors=True)


@router.post("/api/projects/{project_id}/documents",
             response_model=list[DocumentOut], status_code=201)
def upload_documents(project_id: int,
                     files: list[UploadFile] = File(...),
                     db: Session = Depends(get_db)):
    settings = get_settings()
    project = get_project_or_404(db, project_id)

    if len(files) > settings.MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: max {settings.MAX_FILES_PER_UPLOAD} per upload")

    existing_names = {d.file_name for d in db.query(Document).filter(
        Document.project_id == project_id).all()}
    seen_in_request: set[str] = set()

    created: list[Document] = []
    for uf in files:
        file_name = uf.filename or "unnamed"
        ext = Path(file_name).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext or file_name}'. "
                       f"Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}")
        if file_name in existing_names or file_name in seen_in_request:
            raise HTTPException(status_code=409,
                                detail=f"Duplicate file name in project: {file_name}")
        seen_in_request.add(file_name)

        data = uf.file.read()
        if len(data) > settings.MAX_FILE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_name} exceeds {settings.MAX_FILE_MB} MB")

        dest, digest = _store_file(project, file_name, data)
        doc = Document(
            project_id=project_id,
            file_name=file_name,
            file_type=ext.lstrip("."),
            size_bytes=len(data),
            status="processing",
            storage_path=str(dest),
            sha256=digest,
        )
        db.add(doc)
        db.flush()
        db.add(AuditLog(project_id=project_id, action="document_uploaded",
                        entity_type="document", entity_id=doc.id,
                        entity_title=file_name, detail=f"{len(data)} bytes"))
        created.append(doc)
    db.commit()
    for doc in created:
        db.refresh(doc)
        submit_document_processing(doc.id)
    return [d.to_dict() for d in created]


@router.get("/api/projects/{project_id}/documents", response_model=list[DocumentOut])
def list_documents(project_id: int, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    docs = db.query(Document).filter(Document.project_id == project_id) \
        .order_by(Document.id).all()
    return [d.to_dict() for d in docs]


@router.get("/api/documents/{document_id}/preview", response_model=DocumentPreviewOut)
def document_preview(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id) \
        .order_by(Chunk.char_offset).all()
    text = "\n".join(c.text for c in chunks)
    return {
        "document": doc.to_dict(),
        "text": text,
        "chunks": [{"id": c.id, "page": c.page, "text": c.text} for c in chunks],
    }


@router.post("/api/documents/{document_id}/process", response_model=DocumentOut)
def process_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.storage_path or not Path(doc.storage_path).exists():
        doc.status = "failed"
        doc.error = "Stored file missing"
        db.commit()
        raise HTTPException(status_code=422,
                            detail=f"Processing failed: stored file missing")
    try:
        result = process_document_sync(document_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Processing failed: {exc}")
    if result.status == "failed":
        raise HTTPException(status_code=422,
                            detail=f"Processing failed: {result.error}")
    return result.to_dict()


@router.delete("/api/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    # delete chunks
    db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
    # items citing only this document are deleted; others keep remaining evidence
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.project_id == doc.project_id).all()
    for item in items:
        ev = item.evidence or []
        if any(e.get("document_id") == doc.id for e in ev):
            remaining = [e for e in ev if e.get("document_id") != doc.id]
            if remaining:
                item.evidence = remaining
            else:
                db.delete(item)
    db.query(Relationship).filter(Relationship.project_id == doc.project_id).delete()
    # conflicts referencing deleted items
    from app.models import Conflict
    conflicts = db.query(Conflict).filter(
        Conflict.project_id == doc.project_id).all()
    for c in conflicts:
        a = db.get(KnowledgeItem, c.item_a)
        b = db.get(KnowledgeItem, c.item_b)
        if a is None or b is None:
            db.delete(c)
    # remove file on disk
    if doc.storage_path and Path(doc.storage_path).exists():
        Path(doc.storage_path).unlink(missing_ok=True)
    db.add(AuditLog(project_id=doc.project_id, action="document_deleted",
                    entity_type="document", entity_id=doc.id,
                    entity_title=doc.file_name, detail="Document and its exclusive knowledge items removed"))
    db.delete(doc)
    db.commit()
    return {"deleted": True}