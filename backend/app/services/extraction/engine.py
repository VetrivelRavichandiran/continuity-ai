"""Extraction orchestrator.

Flow per document:
  extract text -> chunk -> (LLM if configured, validated against chunks,
  else deterministic rules) -> create knowledge items with evidence linked
  to chunks -> project-level relationships -> project-level conflict pass.
"""
from __future__ import annotations

import difflib
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from app.core.security import is_ai_configured
from app.database.db import SessionLocal
from app.models import (AuditLog, Chunk, Conflict, Document, KnowledgeItem,
                        Project, Relationship)
from app.models.project import utcnow
from app.services.extraction import llm, rules
from app.services.ingestion import extract_text as et
from app.services.ingestion.chunking import chunk_text
from app.services.textutils import significant_words
from app.services.verification import conflicts as conflict_mod

_executor = ThreadPoolExecutor(max_workers=4)
_project_locks: dict[int, threading.Lock] = {}
_project_locks_guard = threading.Lock()


def _project_lock(project_id: int) -> threading.Lock:
    with _project_locks_guard:
        if project_id not in _project_locks:
            _project_locks[project_id] = threading.Lock()
        return _project_locks[project_id]


def rebuild_project_derived(project_id: int) -> None:
    """Rebuild project-level derived data (relationships + conflicts) from
    the current knowledge items. Called after every document finishes
    processing, under a per-project lock so parallel document processing
    cannot clobber each other's results."""
    db = SessionLocal()
    try:
        with _project_lock(project_id):
            build_relationships(db, project_id)
            conflict_mod.detect_conflicts(db, project_id)
            db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# LLM validation
# ---------------------------------------------------------------------------

def find_quote_in_text(quote: str, text: str, window: int = 40,
                       threshold: float = 0.8) -> bool:
    """True if the quote (or a 40-char window of it) appears in text with
    >=80% char overlap."""
    q = (quote or "").strip()
    if not q:
        return False
    if len(q) < 8:
        return q in text
    if q in text:
        return True
    step = max(4, window // 4)
    for start in range(0, max(1, len(q) - window + 1), step):
        w = q[start:start + window]
        if len(w) < 20:
            continue
        probe = w[:8]
        idx = text.find(probe)
        while idx != -1:
            seg = text[idx:idx + window]
            if len(seg) >= 20 and difflib.SequenceMatcher(None, w, seg).ratio() >= threshold:
                return True
            idx = text.find(probe, idx + 1)
    return False


def _validate_llm_items(raw: dict, chunk_texts: list[str]) -> tuple[list[dict], int]:
    """Validate LLM items: every item's evidence_quote must be found (fuzzy)
    in some chunk. Returns (kept_items, dropped_count)."""
    kept: list[dict] = []
    dropped = 0

    def check(quote: str) -> bool:
        if not quote:
            return False
        return any(find_quote_in_text(quote, t) for t in chunk_texts)

    def norm_list(v) -> list:
        return [str(x) for x in v] if isinstance(v, list) else []

    for d in raw.get("decisions", []) or []:
        if not isinstance(d, dict) or not d.get("title"):
            dropped += 1
            continue
        if not check(d.get("evidence_quote", "")):
            dropped += 1
            continue
        kept.append({
            "type": "decision", "title": str(d["title"]),
            "summary": d.get("summary"),
            "details": {
                "reason": d.get("reason"),
                "alternatives": norm_list(d.get("alternatives")),
                "decided_on": d.get("decided_on"),
                "affected": norm_list(d.get("affected")),
            },
            "evidence_phrases": [d.get("evidence_quote", "")],
        })
    for t in raw.get("tasks", []) or []:
        if not isinstance(t, dict) or not t.get("title"):
            dropped += 1
            continue
        if not check(t.get("evidence_quote", "")):
            dropped += 1
            continue
        kept.append({
            "type": "task", "title": str(t["title"]),
            "summary": t.get("description") or str(t["title"]),
            "details": {
                "description": t.get("description"),
                "assignee": t.get("assignee"),
                "due_date": t.get("due_date"),
                "dependencies": norm_list(t.get("dependencies")),
            },
            "task_status": t.get("task_status"),
            "assignee": t.get("assignee"),
            "due_date": t.get("due_date"),
            "evidence_phrases": [t.get("evidence_quote", "")],
        })
    for e in raw.get("events", []) or []:
        if not isinstance(e, dict) or not e.get("title"):
            dropped += 1
            continue
        if not check(e.get("evidence_quote", "")):
            dropped += 1
            continue
        kept.append({
            "type": "event", "title": str(e["title"]),
            "summary": e.get("description"),
            "details": {"event_date": e.get("event_date"),
                        "description": e.get("description")},
            "evidence_phrases": [e.get("evidence_quote", "")],
        })
    for r in raw.get("risks", []) or []:
        if not isinstance(r, dict) or not r.get("title"):
            dropped += 1
            continue
        if not check(r.get("evidence_quote", "")):
            dropped += 1
            continue
        kept.append({
            "type": "risk", "title": str(r["title"]),
            "summary": r.get("description"),
            "details": {"severity": r.get("severity"),
                        "description": r.get("description"),
                        "status": r.get("status") or "open",
                        "mentioned": bool(r.get("mentioned", True))},
            "severity": r.get("severity"),
            "evidence_phrases": [r.get("evidence_quote", "")],
        })
    for q in raw.get("questions", []) or []:
        if not isinstance(q, dict) or not q.get("title"):
            dropped += 1
            continue
        if not check(q.get("evidence_quote", "")):
            dropped += 1
            continue
        kept.append({
            "type": "question", "title": str(q["title"]),
            "summary": q.get("context") or str(q["title"]),
            "details": {"context": q.get("context")},
            "evidence_phrases": [q.get("evidence_quote", "")],
        })
    for ent in raw.get("entities", []) or []:
        if not isinstance(ent, dict) or not ent.get("title"):
            dropped += 1
            continue
        if not check(ent.get("evidence_quote", "")):
            dropped += 1
            continue
        kept.append({
            "type": "entity", "title": str(ent["title"]),
            "summary": f"{ent.get('entity_kind', 'entity')}: {ent['title']}",
            "details": {"entity_kind": ent.get("entity_kind") or "system"},
            "evidence_phrases": [ent.get("evidence_quote", "")],
        })
    return kept, dropped


# ---------------------------------------------------------------------------
# evidence linking
# ---------------------------------------------------------------------------

def _excerpt_around(text: str, idx: int, match_len: int, max_len: int = 300) -> str:
    room = max(0, max_len - match_len)
    start = max(0, idx - room // 2)
    end = min(len(text), start + max_len)
    start = max(0, end - max_len)
    excerpt = text[start:end]
    if start > 0:
        sp = excerpt.find(" ")
        if 0 < sp < 40:
            excerpt = excerpt[sp + 1:]
    if end < len(text):
        sp = excerpt.rfind(" ")
        if sp > 0 and len(excerpt) - sp - 1 < 40:
            excerpt = excerpt[:sp]
    return excerpt.strip()[:max_len]


def _plain(text: str) -> str:
    """Strip markdown bold markers so phrase search tolerates **bold**."""
    return (text or "").replace("**", "")


def _find_evidence(phrase: str, chunks: list[Chunk], doc: Document) -> dict | None:
    """Find the chunk containing phrase (case-insensitive, markdown-tolerant);
    return an evidence dict or None."""
    if not phrase:
        return None
    low = _plain(phrase).lower()
    for chunk in chunks:
        text = chunk.text or ""
        idx = _plain(text).lower().find(low)
        if idx == -1:
            # try a shorter core of the phrase
            core = " ".join(low.split()[:4])
            if len(core) >= 8:
                idx = _plain(text).lower().find(core)
        if idx != -1:
            match_len = min(len(phrase), 60)
            return {
                "document_id": doc.id,
                "document_name": doc.file_name,
                "chunk_id": chunk.id,
                "page": chunk.page,
                "excerpt": _excerpt_around(text, idx, match_len),
            }
    return None


def _link_evidence(item_spec: dict, chunks: list[Chunk], doc: Document) -> tuple[list[dict], str]:
    """Attach evidence to an item spec. Returns (evidence_list, evidence_status)."""
    evidence: list[dict] = []
    phrases = item_spec.get("evidence_phrases") or []
    for phrase in phrases:
        ev = _find_evidence(phrase, chunks, doc)
        if ev and ev not in evidence:
            evidence.append(ev)
        if len(evidence) >= 2:
            break
    if evidence:
        return evidence, "supported"
    if item_spec.get("inferred"):
        return [], "inferred"
    return [], "unverified"


# ---------------------------------------------------------------------------
# per-document processing
# ---------------------------------------------------------------------------

def _create_items(db, project_id: int, doc: Document, chunks: list[Chunk],
                  item_specs: list[dict]) -> list[KnowledgeItem]:
    created: list[KnowledgeItem] = []
    for spec in item_specs:
        evidence, evidence_status = _link_evidence(spec, chunks, doc)
        item = KnowledgeItem(
            project_id=project_id,
            type=spec["type"],
            title=spec["title"],
            summary=spec.get("summary"),
            details=spec.get("details") or {},
            status=spec.get("status") or "pending",
            task_status=spec.get("task_status"),
            severity=spec.get("severity"),
            assignee=spec.get("assignee"),
            due_date=spec.get("due_date"),
            dependencies=spec.get("dependencies") or [],
            evidence_status=evidence_status,
            review_status="pending",
            evidence=evidence,
        )
        db.add(item)
        db.flush()
        db.add(AuditLog(
            project_id=project_id, action="knowledge_created",
            entity_type="knowledge", entity_id=item.id, entity_title=item.title,
            detail=f"Extracted from {doc.file_name}",
        ))
        created.append(item)
    return created


def _llm_or_rules(doc: Document, full_text: str, chunks: list[Chunk]) -> list[dict]:
    """Return item specs for the document, using the LLM when configured and
    successful, else the deterministic rules."""
    if is_ai_configured():
        try:
            raw = llm.extract_document(full_text)
            kept, dropped = _validate_llm_items(raw, [c.text or "" for c in chunks])
            total = len(kept) + dropped
            if total == 0 or dropped <= total / 2:
                if kept:
                    return kept
        except llm.LLMError:
            pass
        # fall through to rules on any failure / >50% dropped
    return rules.extract_with_rules(full_text)["items"]


def process_document(doc_id: int) -> None:
    """Full pipeline for one document. Runs in a background thread with its
    own DB session. Sets status to processed/failed."""
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            return
        doc.status = "processing"
        doc.error = None
        db.commit()

        data = open(doc.storage_path, "rb").read()
        full_text, pages = et.extract_text(doc.file_type, data)

        # delete old chunks + items that cite this document
        old_chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).all()
        for c in old_chunks:
            db.delete(c)
        old_items = db.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == doc.project_id).all()
        for item in old_items:
            ev = item.evidence or []
            if any(e.get("document_id") == doc.id for e in ev):
                remaining = [e for e in ev if e.get("document_id") != doc.id]
                if remaining:
                    item.evidence = remaining
                else:
                    db.delete(item)
        db.flush()

        specs = chunk_text(doc.id, full_text, pages)
        chunks: list[Chunk] = []
        for s in specs:
            ch = Chunk(document_id=doc.id, project_id=doc.project_id,
                       page=s.page, char_offset=s.char_offset, text=s.text)
            db.add(ch)
            chunks.append(ch)
        db.flush()

        item_specs = _llm_or_rules(doc, full_text, chunks)
        created = _create_items(db, doc.project_id, doc, chunks, item_specs)

        doc.page_count = len(pages) if pages else None
        doc.chunk_count = len(chunks)
        doc.status = "processed"
        doc.processed_at = utcnow()
        db.add(AuditLog(
            project_id=doc.project_id, action="document_processed",
            entity_type="document", entity_id=doc.id, entity_title=doc.file_name,
            detail=f"{len(chunks)} chunks, {len(created)} knowledge items",
        ))
        project_id = doc.project_id
        db.commit()
        rebuild_project_derived(project_id)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        try:
            doc = db.get(Document, doc_id)
            if doc is not None:
                doc.status = "failed"
                doc.error = str(exc)[:500]
                db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
    finally:
        db.close()


def process_document_sync(doc_id: int) -> Document:
    """Synchronous variant used by the re-process endpoint (422 on failure)."""
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            raise LookupError("document not found")
        doc.status = "processing"
        doc.error = None
        db.commit()

        data = open(doc.storage_path, "rb").read()
        full_text, pages = et.extract_text(doc.file_type, data)

        old_chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).all()
        for c in old_chunks:
            db.delete(c)
        old_items = db.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == doc.project_id).all()
        for item in old_items:
            ev = item.evidence or []
            if any(e.get("document_id") == doc.id for e in ev):
                remaining = [e for e in ev if e.get("document_id") != doc.id]
                if remaining:
                    item.evidence = remaining
                else:
                    db.delete(item)
        db.flush()

        specs = chunk_text(doc.id, full_text, pages)
        chunks: list[Chunk] = []
        for s in specs:
            ch = Chunk(document_id=doc.id, project_id=doc.project_id,
                       page=s.page, char_offset=s.char_offset, text=s.text)
            db.add(ch)
            chunks.append(ch)
        db.flush()

        item_specs = _llm_or_rules(doc, full_text, chunks)
        created = _create_items(db, doc.project_id, doc, chunks, item_specs)

        doc.page_count = len(pages) if pages else None
        doc.chunk_count = len(chunks)
        doc.status = "processed"
        doc.processed_at = utcnow()
        db.add(AuditLog(
            project_id=doc.project_id, action="document_processed",
            entity_type="document", entity_id=doc.id, entity_title=doc.file_name,
            detail=f"{len(chunks)} chunks, {len(created)} knowledge items",
        ))
        project_id = doc.project_id
        db.commit()
        db.refresh(doc)
        rebuild_project_derived(project_id)
        return doc
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        doc = db.get(Document, doc_id)
        if doc is not None:
            doc.status = "failed"
            doc.error = str(exc)[:500]
            db.commit()
            db.refresh(doc)
            return doc
        raise
    finally:
        db.close()


def submit_document_processing(doc_id: int) -> None:
    _executor.submit(process_document, doc_id)


# ---------------------------------------------------------------------------
# relationships
# ---------------------------------------------------------------------------

def build_relationships(db, project_id: int, chunks: list[Chunk] | None = None) -> None:
    """Rebuild relationship records for the whole project. Idempotent:
    existing relationships for the project are deleted first, so it is safe
    to call repeatedly (callers serialize via the project lock)."""
    db.query(Relationship).filter(Relationship.project_id == project_id).delete()
    items = db.query(KnowledgeItem).filter(KnowledgeItem.project_id == project_id).all()
    by_id = {i.id: i for i in items}

    def find_entity(title: str) -> KnowledgeItem | None:
        low = title.lower()
        for i in items:
            if i.type == "entity" and i.title.lower() == low:
                return i
        return None

    def find_task_by_tid(tid: str) -> KnowledgeItem | None:
        for i in items:
            if i.type == "task" and i.title.startswith(tid):
                return i
        return None

    # decision -> affects -> entity (components mentioned in decision text)
    for item in items:
        if item.type != "decision":
            continue
        blob = " ".join(filter(None, [
            item.title, item.summary or "",
            " ".join((item.details or {}).get("affected") or []),
        ]))
        for name, rx in rules.COMPONENT_PATTERNS:
            if rx.search(blob):
                ent = find_entity(name)
                if ent:
                    db.add(Relationship(project_id=project_id, source_id=item.id,
                                        target_id=ent.id, type="affects"))

    # task -> depends_on -> task
    for item in items:
        if item.type != "task":
            continue
        for dep in item.dependencies or []:
            m = re.match(r"(T-\d{2,})", str(dep))
            target = find_task_by_tid(m.group(1)) if m else None
            if target:
                db.add(Relationship(project_id=project_id, source_id=item.id,
                                    target_id=target.id, type="depends_on"))

    # task -> assigned_to -> entity(person)
    for item in items:
        if item.type != "task" or not item.assignee:
            continue
        ent = find_entity(item.assignee)
        if ent:
            db.add(Relationship(project_id=project_id, source_id=item.id,
                                target_id=ent.id, type="assigned_to"))

    # risk -> related_to -> task (shared significant words)
    risks = [i for i in items if i.type == "risk"]
    tasks = [i for i in items if i.type == "task"]
    for risk in risks:
        rwords = significant_words(risk.title + " " + (risk.summary or ""))
        for task in tasks:
            twords = significant_words(task.title + " " + (task.summary or ""))
            shared = rwords & twords
            if len(shared) >= 2:
                db.add(Relationship(project_id=project_id, source_id=risk.id,
                                    target_id=task.id, type="related_to"))
    db.flush()