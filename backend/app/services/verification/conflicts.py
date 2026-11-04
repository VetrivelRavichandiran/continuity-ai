"""Conflict detection.

Practical approach:
  1. Topic match: two items (any types) discuss the same topic when their
     title+summary share >=3 significant words, or share a 2-word bigram
     (e.g. "integration testing").
  2. Opposite claims:
     a. one item's title/summary states completion ("is complete",
        "closed out", "passed") and the other states pending work
        ("is pending", "not yet", "in progress", "blocked") — with the
        opposite side not also stating its own claim; or
     b. one item states completion while another item's *evidence excerpt*
        states the same topic is pending (e.g. a meeting decision says
        testing is closed out, but the technical report it cites says
        "integration testing is pending").
  For each conflict both items get evidence_status="conflicting" and a
  Conflict record is created.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import Conflict, KnowledgeItem
from app.services.textutils import significant_words

# Word-boundary phrases so "complete" inside "incomplete" never matches.
POSITIVE_PHRASES = [
    r"\bis complete\b", r"\bclosed out\b", r"\bclosed-out\b", r"\bis closed\b",
    r"\btest cases \d+.*\bpassed\b", r"\ball \d+ test cases passed\b",
    r"\bexecuted and passed\b",
]
PENDING_PHRASES = [
    r"\bis pending\b", r"\bhave not yet\b", r"\bnot yet been\b", r"\bnot yet\b",
    r"\bin progress\b", r"\bblocked\b",
]
# Stricter set for excerpts (avoids "in progress" false positives in chunks
# that quote other work).
EXCERPT_PENDING_PHRASES = [
    r"\bis pending\b", r"\bhave not yet\b", r"\bnot yet been\b", r"\bnot yet\b",
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _has_any(text: str, phrases: list[str]) -> bool:
    low = _norm(text)
    return any(re.search(p, low) for p in phrases)


def _title_summary(item: KnowledgeItem) -> str:
    return f"{item.title or ''} {item.summary or ''}"


def _stance_text(item: KnowledgeItem) -> str:
    """Text used for stance detection: title + summary with status *labels*
    stripped. A milestone's 'In progress' status or a task's 'Status:
    Pending' field is a schedule label, not a claim that the work is
    pending — only genuine claims (e.g. 'integration testing is pending')
    should trigger conflict detection."""
    base = _title_summary(item)
    base = re.sub(r"status\s*:\s*\w+", "", base, flags=re.I)
    base = re.sub(r",\s*status\s+\w+", "", base, flags=re.I)
    return base


def _bigrams(text: str) -> set[tuple[str, str]]:
    toks = _norm(text).split()
    return {(toks[i], toks[i + 1]) for i in range(len(toks) - 1)}


def _topic_shared(a: KnowledgeItem, b: KnowledgeItem) -> bool:
    wa = significant_words(_title_summary(a))
    wb = significant_words(_title_summary(b))
    if len(wa & wb) >= 3:
        return True
    # shared 2-word bigram (e.g. "integration testing")
    return bool(_bigrams(a.title or "") & _bigrams(b.title or ""))


def _item_excerpt_text(item: KnowledgeItem) -> str:
    return " ".join((ev.get("excerpt") or "") for ev in item.evidence or [])


def detect_conflicts(db: Session, project_id: int) -> list[Conflict]:
    """Run the conflict pass over all items of a project. Idempotent:
    existing conflicts for the project are replaced."""
    db.query(Conflict).filter(Conflict.project_id == project_id).delete()
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.project_id == project_id).all()
    # reset any previously conflicting status
    for item in items:
        if item.evidence_status == "conflicting":
            item.evidence_status = "supported" if item.evidence else "unverified"

    found: list[Conflict] = []
    seen_pairs: set[tuple[int, int]] = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if (a.id, b.id) in seen_pairs:
                continue
            if not _topic_shared(a, b):
                continue

            conflict = False
            # Rule (a): opposite stances in title/summary
            ta, tb = _stance_text(a), _stance_text(b)
            a_done = _has_any(ta, POSITIVE_PHRASES) and not _has_any(ta, PENDING_PHRASES)
            b_done = _has_any(tb, POSITIVE_PHRASES) and not _has_any(tb, PENDING_PHRASES)
            a_pending = _has_any(ta, PENDING_PHRASES) and not _has_any(ta, POSITIVE_PHRASES)
            b_pending = _has_any(tb, PENDING_PHRASES) and not _has_any(tb, POSITIVE_PHRASES)
            if (a_done and b_pending) or (b_done and a_pending):
                conflict = True
            # Rule (b): one side done, the other's evidence excerpt says pending
            if not conflict:
                ea, eb = _item_excerpt_text(a), _item_excerpt_text(b)
                if a_done and _has_any(eb, EXCERPT_PENDING_PHRASES) and not b_done:
                    conflict = True
                elif b_done and _has_any(ea, EXCERPT_PENDING_PHRASES) and not a_done:
                    conflict = True
            if not conflict:
                continue

            # topic label from shared significant words
            wa = significant_words(_title_summary(a))
            wb = significant_words(_title_summary(b))
            shared = sorted(wa & wb, key=len, reverse=True)[:4]
            topic = " ".join(w.capitalize() for w in shared) + " status"
            a.evidence_status = "conflicting"
            b.evidence_status = "conflicting"
            conflict_row = Conflict(project_id=project_id, topic=topic,
                                    item_a=a.id, item_b=b.id)
            db.add(conflict_row)
            found.append(conflict_row)
            seen_pairs.add((a.id, b.id))
    db.flush()
    return found