"""TF-IDF retrieval over project chunks + knowledge titles/summaries."""
from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RetrievalHit:
    kind: str  # "chunk" | "knowledge"
    id: int
    score: float
    # chunk fields
    page: int | None = None
    text: str | None = None
    document_id: int | None = None
    # knowledge fields
    ktype: str | None = None
    title: str | None = None


def _fit_transform(vectorizer: TfidfVectorizer, docs: list[str], query: str):
    mat = vectorizer.fit_transform(docs)
    qv = vectorizer.transform([query])
    scores = cosine_similarity(qv, mat).ravel()
    return scores


def retrieve_chunks(project_id: int, query: str, top_k: int = 6,
                    chunks: list | None = None) -> list[RetrievalHit]:
    """chunks: list of Chunk ORM rows for the project (loaded by caller)."""
    if not chunks:
        return []
    docs = [c.text or "" for c in chunks]
    try:
        vectorizer = TfidfVectorizer(lowercase=True, stop_words="english",
                                     token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{1,}\b")
        scores = _fit_transform(vectorizer, docs, query)
    except ValueError:
        return []
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    hits = []
    for i in order[:top_k]:
        if scores[i] <= 0:
            continue
        c = chunks[i]
        hits.append(RetrievalHit(
            kind="chunk", id=c.id, score=float(scores[i]), page=c.page,
            text=c.text, document_id=c.document_id,
        ))
    return hits


def retrieve_knowledge(project_id: int, query: str, top_k: int = 4,
                       items: list | None = None) -> list[RetrievalHit]:
    """items: list of KnowledgeItem ORM rows for the project."""
    if not items:
        return []
    docs = [f"{i.title} {i.summary or ''}" for i in items]
    try:
        vectorizer = TfidfVectorizer(lowercase=True, stop_words="english",
                                     token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{1,}\b")
        scores = _fit_transform(vectorizer, docs, query)
    except ValueError:
        return []
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    hits = []
    for i in order[:top_k]:
        if scores[i] <= 0:
            continue
        it = items[i]
        hits.append(RetrievalHit(
            kind="knowledge", id=it.id, score=float(scores[i]),
            ktype=it.type, title=it.title,
        ))
    return hits