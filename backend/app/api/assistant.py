from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import is_ai_configured
from app.database.db import get_db
from app.models import Chunk, Conflict, Document, KnowledgeItem
from app.schemas.assistant import AskRequest, AskResponse
from app.services.extraction import llm
from app.services.extraction.engine import significant_words
from app.services.retrieval.tfidf import retrieve_chunks, retrieve_knowledge
from app.api.projects import get_project_or_404

router = APIRouter(prefix="/api/projects", tags=["assistant"])

INSUFFICIENT_ANSWER = (
    "The available project records do not establish an answer to this question. "
    "No sufficiently relevant evidence was found in the uploaded sources."
)


def _excerpt(text: str, max_len: int = 300) -> str:
    text = " ".join((text or "").split())
    return text[:max_len]


@router.post("/{project_id}/ask", response_model=AskResponse)
def ask(project_id: int, body: AskRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    get_project_or_404(db, project_id)
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty")

    chunks = db.query(Chunk).filter(Chunk.project_id == project_id).all()
    items = db.query(KnowledgeItem).filter(KnowledgeItem.project_id == project_id).all()
    docs = {d.id: d for d in db.query(Document).filter(
        Document.project_id == project_id).all()}

    chunk_hits = retrieve_chunks(project_id, question,
                                 top_k=settings.ASK_TOP_CHUNKS, chunks=chunks)
    knowledge_hits = retrieve_knowledge(project_id, question,
                                        top_k=settings.ASK_TOP_KNOWLEDGE, items=items)

    # warnings: conflicts whose topic words appear in the question
    warnings: list[str] = []
    qwords = significant_words(question)
    conflicts = db.query(Conflict).filter(Conflict.project_id == project_id).all()
    for c in conflicts:
        twords = significant_words(c.topic)
        if twords & qwords:
            a = db.get(KnowledgeItem, c.item_a)
            b = db.get(KnowledgeItem, c.item_b)
            warnings.append(
                f"Two sources disagree on {c.topic.lower()}: "
                f"'{a.title if a else '?'}' vs '{b.title if b else '?'}'.")

    if not chunk_hits and not knowledge_hits:
        return AskResponse(
            question=question, answer=INSUFFICIENT_ANSWER,
            evidence_status="insufficient", confidence=0.0,
            citations=[], related=[], warnings=warnings +
            ["No sufficiently relevant evidence was found in the uploaded sources."])

    top_score = max([h.score for h in chunk_hits] +
                    [h.score for h in knowledge_hits])
    if top_score < settings.ASK_MIN_SCORE:
        return AskResponse(
            question=question, answer=INSUFFICIENT_ANSWER,
            evidence_status="insufficient", confidence=0.0,
            citations=[], related=[], warnings=warnings +
            ["No sufficiently relevant evidence was found in the uploaded sources."])

    # citations from top chunks
    citations = []
    for h in chunk_hits:
        doc = docs.get(h.document_id)
        citations.append({
            "document_id": h.document_id,
            "document_name": doc.file_name if doc else "unknown",
            "page": h.page,
            "excerpt": _excerpt(h.text or ""),
        })

    related = [{"id": h.id, "type": h.ktype, "title": h.title}
               for h in knowledge_hits]

    # answer: LLM if configured, else deterministic template
    answer = None
    if is_ai_configured() and chunk_hits:
        passages = [{"document_name": c["document_name"], "page": c["page"],
                     "excerpt": c["excerpt"]} for c in citations]
        try:
            answer = llm.answer_question(question, passages)
            if not answer or answer.strip().upper().startswith("INSUFFICIENT"):
                answer = None
        except llm.LLMError:
            answer = None

    if answer is None:
        parts: list[str] = []
        if knowledge_hits:
            best = db.get(KnowledgeItem, knowledge_hits[0].id)
            if best and best.summary:
                parts.append(best.summary)
        for h in chunk_hits[:3]:
            parts.append(_excerpt(h.text or "", 200))
        if parts:
            answer = "Based on the project records: " + " ".join(parts)
        else:
            answer = "The available project records mention this topic but do not " \
                     "establish a definitive answer."

    return AskResponse(
        question=question,
        answer=answer,
        evidence_status="supported",
        confidence=round(min(1.0, top_score), 4),
        citations=citations,
        related=related,
        warnings=warnings,
    )