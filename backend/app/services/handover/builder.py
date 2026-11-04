"""Handover document builder.

Assembles the 15 contract sections from actual knowledge records only
(no invented facts). Content strings use markdown-lite: "## " headings,
"- " bullets, **bold** inline, blank lines between paragraphs.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (AuditLog, Conflict, Document, Handover, KnowledgeItem,
                        Project)
from app.models.project import utcnow

NO_DATA = "No records of this type were found in the uploaded sources."

SECTION_DEFS = [
    ("overview", "1. Project Overview"),
    ("objectives", "2. Project Objectives"),
    ("status", "3. Current Project Status"),
    ("completed", "4. Completed Activities"),
    ("in_progress", "5. In-Progress Activities"),
    ("pending", "6. Pending Tasks"),
    ("decisions", "7. Important Decisions and Reasoning"),
    ("architecture", "8. Technical Architecture Changes"),
    ("unresolved", "9. Unresolved Issues"),
    ("risks", "10. Risks and Blockers"),
    ("dependencies", "11. Dependencies"),
    ("milestones", "12. Events and Milestones"),
    ("next_actions", "13. Recommended Next Actions"),
    ("evidence", "14. Evidence and Source References"),
    ("verification", "15. Verification Status"),
]

# Engineer audience: decisions + architecture + risks + pending + dependencies first
ENGINEER_ORDER = [
    "decisions", "architecture", "risks", "pending", "dependencies",
    "overview", "objectives", "status", "completed", "in_progress",
    "unresolved", "milestones", "next_actions", "evidence", "verification",
]


def _fmt_date(d: str | None) -> str:
    return d or "Not specified"


def _task_line(t: KnowledgeItem) -> str:
    parts = [f"- **{t.title}**"]
    if t.assignee:
        parts.append(f"owner {t.assignee}")
    if t.due_date:
        parts.append(f"due {_fmt_date(t.due_date)}")
    if t.dependencies:
        parts.append(f"depends on {', '.join(t.dependencies)}")
    line = " (" + "; ".join(parts[1:]) + ")" if len(parts) > 1 else ""
    detail = (t.details or {}).get("description")
    if detail:
        line += f" — {detail}"
    return line + "."


def _build_sections(project: Project, items: list[KnowledgeItem],
                    conflicts: list[Conflict], docs: list[Document],
                    audience: str) -> list[dict]:
    decisions = [i for i in items if i.type == "decision"]
    tasks = [i for i in items if i.type == "task"]
    events = [i for i in items if i.type == "event"]
    risks = [i for i in items if i.type == "risk"]
    questions = [i for i in items if i.type == "question"]
    entities = [i for i in items if i.type == "entity"]

    completed = [t for t in tasks if t.task_status == "completed"]
    in_progress = [t for t in tasks if t.task_status == "in_progress"]
    pending = [t for t in tasks if t.task_status == "pending"]
    blocked = [t for t in tasks if t.task_status == "blocked"]

    content: dict[str, str] = {}

    # 1. overview
    lines = [f"**{project.name}**"]
    if project.description:
        lines.append(project.description)
    if project.category:
        lines.append(f"Category: {project.category}")
    lines.append(f"Project status: {project.status}.")
    persons: list[str] = []
    for e in entities:
        if (e.details or {}).get("entity_kind") == "person" and e.title not in persons:
            persons.append(e.title)
    if persons:
        lines.append("Team: " + ", ".join(persons) + ".")
    content["overview"] = "\n".join(lines)

    # 2. objectives
    if project.objectives:
        content["objectives"] = "\n".join(f"- {o}" for o in project.objectives)
    else:
        content["objectives"] = NO_DATA

    # 3. status
    total = len(tasks)
    lines = [
        f"Task status across {total} recorded tasks: {len(completed)} completed, "
        f"{len(in_progress)} in progress, {len(pending)} pending, {len(blocked)} blocked.",
    ]
    if total:
        pct = round(100.0 * len(completed) / total, 1)
        lines.append(f"Overall completion: {pct}%.")
    if blocked:
        lines.append("Blocked work: " + "; ".join(t.title for t in blocked) + ".")
    content["status"] = "\n".join(lines)

    # 4. completed
    if completed:
        content["completed"] = "\n".join(_task_line(t) for t in completed)
    else:
        content["completed"] = NO_DATA

    # 5. in progress
    if in_progress:
        content["in_progress"] = "\n".join(_task_line(t) for t in in_progress)
    else:
        content["in_progress"] = NO_DATA

    # 6. pending
    if pending:
        content["pending"] = "\n".join(_task_line(t) for t in pending)
    else:
        content["pending"] = NO_DATA

    # 7. decisions
    if decisions:
        lines = []
        for d in decisions:
            det = d.details or {}
            lines.append(f"## {d.title}")
            if det.get("reason"):
                lines.append(f"Reason: {det['reason']}")
            if det.get("alternatives"):
                lines.append("Alternatives considered: " + ", ".join(det["alternatives"]) + ".")
            if det.get("decided_on"):
                lines.append(f"Decided on {_fmt_date(det['decided_on'])}.")
            if det.get("affected"):
                lines.append("Affects: " + ", ".join(det["affected"]) + ".")
            lines.append("")
        content["decisions"] = "\n".join(lines).rstrip()
    else:
        content["decisions"] = NO_DATA

    # 8. architecture
    arch_items = [i for i in items
                  if i.type in ("decision", "event", "task")
                  and "architecture" in (i.title + " " + (i.summary or "")).lower()]
    if arch_items:
        lines = []
        for a in arch_items:
            lines.append(f"- **{a.title}** — {a.summary or ''}".rstrip(" —"))
        content["architecture"] = "\n".join(lines)
    else:
        content["architecture"] = NO_DATA

    # 9. unresolved
    if questions:
        lines = []
        for q in questions:
            ctx = (q.details or {}).get("context")
            lines.append(f"- {q.title}" + (f" ({ctx})" if ctx else ""))
        content["unresolved"] = "\n".join(lines)
    else:
        content["unresolved"] = NO_DATA

    # 10. risks
    if risks:
        lines = []
        for r in risks:
            det = r.details or {}
            sev = det.get("severity") or r.severity or "unknown"
            lines.append(f"- **[{sev.upper()}]** {r.title}"
                         + (f" — {det['description']}" if det.get("description") and det["description"] != r.title else ""))
        content["risks"] = "\n".join(lines)
    else:
        content["risks"] = NO_DATA

    # 11. dependencies
    dep_lines = []
    for t in tasks:
        if t.dependencies:
            dep_lines.append(f"- {t.title} depends on {', '.join(t.dependencies)}.")
    content["dependencies"] = "\n".join(dep_lines) if dep_lines else NO_DATA

    # 12. milestones
    if events:
        lines = []
        for e in sorted(events, key=lambda x: (x.details or {}).get("event_date") or "9999"):
            det = e.details or {}
            lines.append(f"- **{_fmt_date(det.get('event_date'))}** — {e.title}"
                         + (f": {det['description']}" if det.get("description") else ""))
        content["milestones"] = "\n".join(lines)
    else:
        content["milestones"] = NO_DATA

    # 13. next actions
    lines = []
    if blocked:
        lines.append("## Unblock first")
        lines.extend(f"- {t.title} (owner: {t.assignee or 'unassigned'})" for t in blocked)
    if in_progress:
        lines.append("## Continue in-progress work")
        lines.extend(f"- {t.title} (owner: {t.assignee or 'unassigned'})" for t in in_progress)
    if pending:
        lines.append("## Start pending work")
        lines.extend(f"- {t.title} (owner: {t.assignee or 'unassigned'})" for t in pending)
    if audience == "engineer" and (blocked or in_progress):
        lines.append("## Immediate next steps")
        for t in blocked + in_progress:
            lines.append(f"- {t.title} — owner {t.assignee or 'unassigned'}"
                         + (f", due {_fmt_date(t.due_date)}" if t.due_date else ""))
    content["next_actions"] = "\n".join(lines) if lines else NO_DATA

    # 14. evidence
    if docs:
        lines = []
        for d in docs:
            lines.append(f"- **{d.file_name}** ({d.file_type}, {d.size_bytes} bytes"
                         + (f", {d.page_count} pages" if d.page_count else "")
                         + f") — {d.chunk_count} chunks extracted.")
        content["evidence"] = "\n".join(lines)
    else:
        content["evidence"] = NO_DATA

    # 15. verification
    approved = [i for i in items if i.review_status == "approved"]
    pending_rev = [i for i in items if i.review_status == "pending"]
    rejected = [i for i in items if i.review_status == "rejected"]
    flagged = [i for i in items if i.review_status == "flagged"]
    lines = [
        f"Records by review status: {len(approved)} approved, {len(pending_rev)} pending, "
        f"{len(rejected)} rejected, {len(flagged)} flagged.",
    ]
    unverified_decisions = [d for d in decisions
                            if d.evidence_status in ("unverified", "conflicting", "inferred")]
    if unverified_decisions:
        lines.append("Key decisions not yet verified against sources:")
        lines.extend(f"- {d.title} (evidence status: {d.evidence_status})" for d in unverified_decisions)
    else:
        lines.append("All key decisions have supported evidence.")
    if conflicts:
        lines.append("Open conflicts:")
        for c in conflicts:
            lines.append(f"- {c.topic}")
    content["verification"] = "\n".join(lines)

    # assemble in order (engineer audience reorders)
    order = ENGINEER_ORDER if audience == "engineer" else [k for k, _ in SECTION_DEFS]
    title_by_key = dict(SECTION_DEFS)
    sections = []
    for idx, key in enumerate(order, start=1):
        sections.append({
            "key": key,
            "title": f"{idx}. {title_by_key[key].split('. ', 1)[1]}",
            "content": content.get(key, NO_DATA),
        })
    return sections


def build_handover(db: Session, project: Project, audience: str) -> Handover:
    items = db.query(KnowledgeItem).filter(KnowledgeItem.project_id == project.id).all()
    conflicts = db.query(Conflict).filter(Conflict.project_id == project.id).all()
    docs = db.query(Document).filter(Document.project_id == project.id).all()

    sections = _build_sections(project, items, conflicts, docs, audience)

    tasks = [i for i in items if i.type == "task"]
    summary = {
        "decisions": len([i for i in items if i.type == "decision"]),
        "tasks": len(tasks),
        "risks": len([i for i in items if i.type == "risk"]),
        "unresolved": len([i for i in items if i.type == "question"]),
        "approved": len([i for i in items if i.review_status == "approved"]),
        "pending": len([i for i in items if i.review_status == "pending"]),
    }

    prev = db.query(Handover).filter(Handover.project_id == project.id).count()
    handover = Handover(
        project_id=project.id,
        project_name=project.name,
        audience=audience,
        version=prev + 1,
        status="generated",
        generated_at=utcnow(),
        sections=sections,
        summary=summary,
    )
    db.add(handover)
    db.flush()
    db.add(AuditLog(
        project_id=project.id, action="handover_generated",
        entity_type="handover", entity_id=handover.id,
        entity_title=f"Handover v{handover.version} ({audience})",
        detail=f"{len(sections)} sections generated",
    ))
    db.commit()
    db.refresh(handover)
    return handover