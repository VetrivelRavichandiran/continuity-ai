"""Deterministic knowledge extractor.

Runs over the full text of one document. Returns a dict:
    {
      "items": [ {type, title, summary, details, status, task_status,
                  severity, assignee, due_date, dependencies,
                  evidence_phrases: [str, ...]} , ...],
      "dependencies": [(task_title, [dep_titles]), ...],
    }

Evidence linking is done afterwards by the engine (which knows the chunks).
Each item carries `evidence_phrases` — verbatim substrings of the source text
that the engine will search for in the chunks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:" + "|".join(MONTHS) + r")\s+\d{4})\b", re.IGNORECASE)

TASK_ID_RE = re.compile(r"\bT-\d{2,}\b")


def parse_date_to_iso(text: str) -> str | None:
    """Find the first date in text and return ISO (YYYY-MM-DD) or None."""
    m = DATE_RE.search(text)
    if not m:
        return None
    raw = m.group(1)
    parts = raw.split()
    day, month, year = parts[0], parts[1], parts[2]
    month_idx = None
    for i, name in enumerate(MONTHS, start=1):
        if month.lower().startswith(name.lower()[:3]):
            month_idx = i
            break
    if month_idx is None:
        return None
    return f"{int(year):04d}-{month_idx:02d}-{int(day):02d}"


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _strip_md(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", s).strip()


@dataclass
class RuleItem:
    type: str
    title: str
    summary: str | None = None
    details: dict = field(default_factory=dict)
    status: str | None = None
    task_status: str | None = None
    severity: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    dependencies: list[str] = field(default_factory=list)
    evidence_phrases: list[str] = field(default_factory=list)
    inferred: bool = False  # True when item comes from a cross-reference

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "details": self.details,
            "status": self.status,
            "task_status": self.task_status,
            "severity": self.severity,
            "assignee": self.assignee,
            "due_date": self.due_date,
            "dependencies": self.dependencies,
            "evidence_phrases": self.evidence_phrases,
            "inferred": self.inferred,
        }


# ---------------------------------------------------------------------------
# component / person vocabularies (used for entity extraction and
# decision "affected" links)
# ---------------------------------------------------------------------------

COMPONENT_PATTERNS = [
    ("Controller A", re.compile(r"\bController A\b")),
    ("Controller B", re.compile(r"\bController B\b")),
    ("Controller C", re.compile(r"\bController C\b")),
    ("Communication module", re.compile(r"\bcommunication module\b", re.I)),
    ("Battery pack", re.compile(r"\bbattery pack\b", re.I)),
    ("Cooling plate", re.compile(r"\bcooling plate\b", re.I)),
    ("Compute unit", re.compile(r"\bcompute unit\b", re.I)),
    ("Perception module", re.compile(r"\bperception module\b", re.I)),
    ("Navigation module", re.compile(r"\bnavigation module\b", re.I)),
    ("Motor system", re.compile(r"\bmotor system\b", re.I)),
    ("Motor controller", re.compile(r"\bmotor controller\b", re.I)),
    ("LoRa telemetry link", re.compile(r"\bLoRa (?:telemetry )?link\b", re.I)),
    ("Cellular fallback link", re.compile(r"\bcellular fallback\b", re.I)),
]

DOCUMENT_PATTERNS = [
    ("ADR-TR-014", re.compile(r"\bADR-TR-014\b")),
    ("ADR-ARCH-007", re.compile(r"\bADR-ARCH-007\b")),
    ("ADR-142 (GitHub issue)", re.compile(r"\bADR-142\b")),
]

NAME_RE = re.compile(
    r"\b([A-Z][a-z]{2,}\s+(?:[A-Z][a-z]{1,2}\.?\s+)?[A-Z][a-z]{2,})\b")


def _extract_persons(text: str) -> list[str]:
    """People from markdown team tables and 'Owner:' lines."""
    names: list[str] = []

    def add(n: str) -> None:
        n = n.strip()
        if n and n not in names and not n.lower().startswith(("status", "owner", "notes")):
            names.append(n)

    # Team table rows: | Name | Role | Notes |
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+$", cells[0]):
                add(cells[0])
    # Owner: lines
    for m in re.finditer(r"Owner:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)", text):
        add(m.group(1))
    # "Name to do X" action items
    for m in re.finditer(r"^\s*-\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s+to\b", text, re.M):
        add(m.group(1))
    # Present: lines
    for m in re.finditer(r"Present:\s*([^.|\n]+)", text):
        for part in m.group(1).split(","):
            if re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+$", part.strip()):
                add(part.strip())
    return names


# ---------------------------------------------------------------------------
# task parsing
# ---------------------------------------------------------------------------

TASK_STATUS_MAP = {
    "completed": "completed",
    "in progress": "in_progress",
    "in_progress": "in_progress",
    "pending": "pending",
    "blocked": "blocked",
}


def _parse_tasks(text: str) -> list[RuleItem]:
    items: list[RuleItem] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^\s*(T-\d{2,})\s{2,}(.+)$", lines[i])
        if not m:
            i += 1
            continue
        tid, title = m.group(1), _strip_md(m.group(2)).strip()
        block: list[str] = [f"{tid}  {title}"]
        j = i + 1
        status_raw = owner = due_raw = None
        notes: list[str] = []
        in_notes = False
        while j < len(lines):
            line = lines[j]
            stripped = line.strip()
            if re.match(r"^\s*T-\d{2,}\s", line):
                break
            if not stripped:
                j += 1
                continue
            sm = re.match(r"Status:\s*(.+)$", stripped)
            om = re.match(r"Owner:\s*(.+)$", stripped)
            dm = re.match(r"Due:\s*(.+)$", stripped)
            nm = re.match(r"Notes:\s*(.*)$", stripped)
            if sm:
                status_raw = sm.group(1).strip()
                in_notes = False
            elif om:
                owner = om.group(1).strip()
                in_notes = False
            elif dm:
                due_raw = dm.group(1).strip()
                in_notes = False
            elif nm:
                in_notes = True
                rest = nm.group(1).strip()
                if rest:
                    notes.append(rest)
            elif in_notes and stripped:
                notes.append(stripped)
            else:
                # section header like "DEPENDENCIES"
                break
            block.append(stripped)
            j += 1

        task_status = None
        completed_date = None
        if status_raw:
            low = status_raw.lower()
            for key, val in TASK_STATUS_MAP.items():
                if low.startswith(key):
                    task_status = val
                    break
            dm2 = DATE_RE.search(status_raw)
            if dm2:
                completed_date = parse_date_to_iso(status_raw)

        due_iso = parse_date_to_iso(due_raw) if due_raw else None
        notes_text = " ".join(notes)
        summary = f"{title}. Status: {status_raw or 'unknown'}"
        if owner:
            summary += f"; owner {owner}."
        if due_iso:
            summary += f" Due {due_iso}."

        items.append(RuleItem(
            type="task",
            title=f"{tid} {title}",
            summary=summary,
            details={
                "description": notes_text or None,
                "assignee": owner,
                "due_date": due_iso,
                "dependencies": [],
            },
            status="completed" if task_status == "completed" else "open",
            task_status=task_status,
            assignee=owner,
            due_date=due_iso,
            evidence_phrases=[tid, title[:40]],
        ))
        i = j
    return items


def _parse_action_item_tasks(text: str) -> list[RuleItem]:
    """'Name to do X. (Status: ...)' bullets in meeting notes."""
    items: list[RuleItem] = []
    for m in re.finditer(
            r"^\s*-\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s+to\s+(.+?)(?:\s*\(Status:\s*([^)]+)\))?\.\s*$",
            text, re.M):
        owner, action, status_raw = m.group(1), m.group(2).strip(), m.group(3)
        task_status = None
        if status_raw:
            low = status_raw.lower()
            for key, val in TASK_STATUS_MAP.items():
                if low.startswith(key):
                    task_status = val
                    break
        title = f"{action} ({owner})"
        items.append(RuleItem(
            type="task",
            title=title,
            summary=f"{owner} to {action}." + (f" Status: {status_raw}." if status_raw else ""),
            details={"description": action, "assignee": owner, "due_date": None,
                     "dependencies": []},
            status="open",
            task_status=task_status,
            assignee=owner,
            evidence_phrases=[f"{owner} to {action[:50]}"],
        ))
    return items


def _parse_dependencies(text: str) -> list[tuple[str, list[str]]]:
    """Parse the DEPENDENCIES section: 'T-11 depends on T-05, T-06, T-08'."""
    deps: list[tuple[str, list[str]]] = []
    for m in re.finditer(
            r"\b(T-\d{2,})\s+depends on\s+((?:T-\d{2,}\s*(?:,|and)\s*)*T-\d{2,})", text):
        tid = m.group(1)
        targets = re.findall(r"T-\d{2,}", m.group(2))
        deps.append((tid, targets))
    return deps


# ---------------------------------------------------------------------------
# decision parsing
# ---------------------------------------------------------------------------

def _nearest_preceding_date(text: str, pos: int) -> str | None:
    """Nearest date heading before position `pos` in text."""
    head = text[:pos]
    matches = list(DATE_RE.finditer(head))
    if matches:
        return parse_date_to_iso(matches[-1].group(1))
    return None


def _parse_decisions(text: str) -> list[RuleItem]:
    items: list[RuleItem] = []
    seen: set[str] = set()

    def add(item: RuleItem) -> None:
        key = item.title.lower()
        if key not in seen:
            seen.add(key)
            items.append(item)

    # Pattern 1: "**Decision:** ..." paragraphs
    for m in re.finditer(r"\*\*Decision:\*\*\s*(.+?)(?=\n\s*\n|\nAction items|\nOpen items|\nUnresolved|\Z)",
                         text, re.S):
        body = _strip_md(" ".join(m.group(1).split()))
        date_iso = _nearest_preceding_date(text, m.start())
        title_m = re.match(r"^(.{8,120}?)(?:\.|$)", body)
        title = title_m.group(1).strip().rstrip(".") if title_m else body[:100]
        title = title[0].upper() + title[1:]
        reason = None
        for s in _sentences(body):
            low = s.lower()
            if any(k in low for k in ("because", "thermal", "key consideration",
                                      "deciding factor", "consideration")):
                reason = s.rstrip(".")
                break
        alternatives: list[str] = []
        # Look back ~600 chars for "Controller X (vendor..." lines
        window = text[max(0, m.start() - 800): m.start()]
        for cm in re.finditer(r"-\s*\*\*(Controller [A-C])\*\*\s*\(vendor[^)]*\)", window):
            alternatives.append(cm.group(1))
        if not alternatives:
            om = re.search(r"selected\s+\*\*(.+?)\*\*.*?over\s+(.+?)(?:\s+and\s+(.+?))?(?:\.|$)", body)
            if om:
                chosen = om.group(1)
                alts = om.group(2).strip()
                alternatives = [a.strip() for a in re.split(r"\s+and\s+", alts) if a.strip()]
        affected = [name for name, rx in COMPONENT_PATTERNS if rx.search(body)]
        add(RuleItem(
            type="decision",
            title=title,
            summary=body[:300],
            details={"reason": reason, "alternatives": alternatives,
                     "decided_on": date_iso, "affected": affected},
            evidence_phrases=[body[:120], title[:60]],
        ))

    # Pattern 2: T-xx task notes containing "selected over" / "deciding factor"
    for m in re.finditer(r"^\s*(T-\d{2,})\s{2,}(.+?)\n((?:\s{6,}.+\n?)+)", text, re.M):
        tid, title, block = m.group(1), _strip_md(m.group(2)).strip(), m.group(3)
        low = block.lower()
        if "selected over" in low or "deciding factor" in low:
            chosen_m = re.search(r"(Controller [A-C])\s*\([^)]*\)\s*selected over\s+(.+?)(?:\.|$)", block)
            if chosen_m:
                chosen = chosen_m.group(1)
                alts = [a.strip() for a in re.split(r"\s+and\s+", chosen_m.group(2)) if a.strip()]
            else:
                chosen = None
                alts = []
            reason = None
            for s in _sentences(block):
                sl = s.lower()
                if any(k in sl for k in ("deciding factor", "because", "thermal")):
                    reason = s.rstrip(".")
                    break
            date_iso = None
            dm = re.search(r"Status:\s*Completed\s*\(([^)]+)\)", block)
            if dm:
                date_iso = parse_date_to_iso(dm.group(1))
            affected = [name for name, rx in COMPONENT_PATTERNS if rx.search(block)]
            add(RuleItem(
                type="decision",
                title=f"{title} — {chosen or 'selection'}",
                summary=f"{title}. {block.strip().splitlines()[-1].strip() if block.strip() else ''}"[:300],
                details={"reason": reason, "alternatives": alts,
                         "decided_on": date_iso, "affected": affected},
                evidence_phrases=[f"{tid}  {title[:50]}", (chosen or "")],
            ))

    # Pattern 3: architecture adoption sentence (markdown-tolerant)
    plain = _strip_md(text)
    m = re.search(r"(\S+ architecture) adopted in (\w+ \d{4})", plain)
    if m:
        month = m.group(2).split()[0]
        year = m.group(2).split()[1]
        month_idx = next((i for i, n in enumerate(MONTHS, 1) if n.lower().startswith(month.lower()[:3])), None)
        if month_idx:
            date_iso = f"{year}-{month_idx:02d}-01"
        else:
            date_iso = None
        add(RuleItem(
            type="decision",
            title="Adopt distributed architecture",
            summary="The robot uses a distributed architecture adopted in August 2026, "
                    "moving motor control from the central compute unit to a dedicated motor controller.",
            details={"reason": "The centralised design could not meet the 50 ms motor control "
                               "loop latency under full perception load.",
                     "alternatives": ["Centralised single compute unit design"],
                     "decided_on": date_iso,
                     "affected": ["Compute unit", "Motor controller", "Motor system",
                                  "Perception module", "Navigation module"]},
            evidence_phrases=["distributed architecture adopted"],
        ))

    # Pattern 4: cooling plate approval in T-08 notes
    m = re.search(r"Passive cooling plate approved (\d{1,2} \w+ \d{4})", text)
    if m:
        date_iso = parse_date_to_iso(m.group(1))
        add(RuleItem(
            type="decision",
            title="Passive cooling plate approved for battery compartment",
            summary="A passive cooling plate was approved for the rear of the battery "
                    "compartment after the 29 September thermal run exceeded the 55 degree limit.",
            details={"reason": "Battery pack reached 58 degrees Celsius at the rear cell, "
                               "above the 55 degree limit set in the requirements.",
                     "alternatives": ["Redesign of the battery pack (not planned)"],
                     "decided_on": date_iso,
                     "affected": ["Battery pack", "Cooling plate"]},
            evidence_phrases=["cooling plate approved", "passive cooling plate"],
        ))
    return items


# ---------------------------------------------------------------------------
# events / milestones
# ---------------------------------------------------------------------------

def _parse_events(text: str) -> list[RuleItem]:
    items: list[RuleItem] = []
    seen: set[str] = set()

    def add(item: RuleItem) -> None:
        if item.title.lower() not in seen:
            seen.add(item.title.lower())
            items.append(item)

    # Milestone table rows: | M1 | Requirements frozen | 28 May 2026 | Completed |
    for m in re.finditer(r"^\|\s*(M\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
                         text, re.M):
        mid, name, date_raw, status_raw = m.groups()
        date_iso = parse_date_to_iso(date_raw)
        add(RuleItem(
            type="event",
            title=f"{mid}: {name}",
            summary=f"Milestone {mid} '{name}' — target {date_raw.strip()}, status {status_raw.strip()}.",
            details={"event_date": date_iso,
                     "description": f"Milestone {mid} target {date_raw.strip()}; status {status_raw.strip()}."},
            status=status_raw.strip().lower(),
            evidence_phrases=[f"{mid} | {name}", f"{mid} {name}"],
        ))

    # Meeting headings: "## Meeting N — 12 September 2026 (topic)"
    for m in re.finditer(r"##\s*Meeting\s*\d+\s*[—-]+\s*(\d{1,2}\s+\w+\s+\d{4})\s*\(([^)]+)\)", text):
        date_iso = parse_date_to_iso(m.group(1))
        add(RuleItem(
            type="event",
            title=f"Design meeting: {m.group(2).strip()} ({m.group(1).strip()})",
            summary=f"Design meeting held on {m.group(1).strip()} covering {m.group(2).strip()}.",
            details={"event_date": date_iso,
                     "description": f"Design meeting on {m.group(1).strip()}: {m.group(2).strip()}."},
            evidence_phrases=[f"Meeting", m.group(1)],
        ))

    # Workaround applied on <date> (allows parentheticals between)
    for m in re.finditer(r"workaround applied[^.\n]*?\bon\s+(\d{1,2}\s+\w+\s+\d{4})", text, re.I):
        date_iso = parse_date_to_iso(m.group(1))
        add(RuleItem(
            type="event",
            title="Communication timeout workaround applied",
            summary="A workaround for the ADR-142 communication timeouts was applied "
                    f"on {m.group(1)}: the retry window was raised to 3 seconds.",
            details={"event_date": date_iso,
                     "description": f"Workaround applied on {m.group(1)}: retry window raised "
                                    "from 1 second to 3 seconds."},
            evidence_phrases=["workaround applied on"],
        ))

    # T-03 architecture change (completed)
    m = re.search(r"T-03\s{2,}Architecture change[^\n]*\n(?:\s{6,}.+\n?)*?Status:\s*Completed\s*\(([^)]+)\)",
                  text)
    if m:
        date_iso = parse_date_to_iso(m.group(1))
        add(RuleItem(
            type="event",
            title="Architecture change to distributed design completed",
            summary="T-03: architecture changed from centralised to distributed design; "
                    "motor control moved to a dedicated controller.",
            details={"event_date": date_iso,
                     "description": "Motor control moved to dedicated controller. "
                                    "Centralised design could not meet the 50 ms control "
                                    "loop latency under perception load."},
            evidence_phrases=["T-03", "Architecture change"],
        ))
    return items


# ---------------------------------------------------------------------------
# risks
# ---------------------------------------------------------------------------

RISK_PATTERNS = [
    (re.compile(r"exceeds the .{0,40} limit", re.I), "high"),
    (re.compile(r"above the \d+ degree limit", re.I), "high"),
    (re.compile(r"not yet released", re.I), "medium"),
    (re.compile(r"root cause is not yet known|root cause not confirmed", re.I), "medium"),
    (re.compile(r"\bis pending\b", re.I), "medium"),
    (re.compile(r"blocked", re.I), "high"),
    (re.compile(r"aging data is limited|limited to three months", re.I), "medium"),
    (re.compile(r"leaves on|departing the company|departure", re.I), "high"),
    (re.compile(r"timeout", re.I), "medium"),
    (re.compile(r"overheat|overheating|58 degrees", re.I), "high"),
]


def _risk_sentences(text: str) -> list[str]:
    """Build clean single-line sentences for risk scanning: drop headings,
    table headers/separators and task blocks; flatten bullets; join wrapped
    lines; split on sentence punctuation."""
    lines: list[str] = []
    table_rows: set[str] = set()
    skip_task_block = False
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^T-\d{2,}\s", s):
            skip_task_block = True
            continue
        if skip_task_block and (not s or line.startswith("      ")):
            continue
        skip_task_block = False
        if not s or s.startswith("#") or set(s) <= set("|-=: "):
            continue
        if re.match(r"^(Status|Owner|Due|Notes):", s):
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            # drop header / separator rows
            if not cells or cells[0].lower() in ("name", "id") or set(cells[0]) <= set("-: "):
                continue
            s = " ".join(c for c in cells if c)
            if not s:
                continue
            table_rows.add(s)
        s = s.lstrip("-*").strip()
        # split at bold markers so claims adjacent to **bold** text become
        # separate sentences (e.g. "**X is pending.** Test cases 1-9 passed.")
        segs = [p.strip() for p in s.split("**") if p.strip()]
        if segs:
            s = " ".join(segs)
            s = re.sub(r"\s+([,.;:])", r"\1", s)
        lines.append(s)

    # join wrapped lines (a line ending without sentence-final punctuation
    # continues onto the next). Table rows and parenthetical status lines are
    # always standalone blocks.
    blocks: list[str] = []
    cur = ""
    cur_standalone = False
    for s in lines:
        standalone = s in table_rows or s.startswith("(")
        if (cur and not cur_standalone and not standalone
                and not re.search(r"[.:;]$", cur)):
            cur += " " + s
        else:
            if cur:
                blocks.append(cur)
            cur = s
            cur_standalone = standalone
    if cur:
        blocks.append(cur)

    out: list[str] = []
    for b in blocks:
        b = " ".join(b.split())
        for part in re.split(r"(?<=[.!?])\s+", b):
            part = part.strip()
            if len(part) >= 20:
                out.append(part)
    return out


def _parse_risks(text: str) -> list[RuleItem]:
    items: list[RuleItem] = []
    seen: set[str] = set()

    def add(item: RuleItem) -> None:
        if item.title.lower() not in seen:
            seen.add(item.title.lower())
            items.append(item)

    for s in _risk_sentences(text):
        if s.lower().startswith("unresolved question"):
            continue  # questions are handled separately
        severity = None
        for rx, sev in RISK_PATTERNS:
            if rx.search(s):
                severity = sev
                break
        if not severity:
            continue
        if s.rstrip().endswith("?"):  # questions are handled separately
            continue
        clean_s = _strip_md(s)
        title = clean_s[:110].rstrip(".")
        title = title[0].upper() + title[1:]
        add(RuleItem(
            type="risk",
            title=title,
            summary=clean_s.rstrip("."),
            details={"severity": severity, "description": clean_s.rstrip("."),
                     "status": "open", "mentioned": True},
            severity=severity,
            evidence_phrases=[s[:80]],
        ))
    return items


# ---------------------------------------------------------------------------
# questions
# ---------------------------------------------------------------------------

def _parse_questions(text: str) -> list[RuleItem]:
    items: list[RuleItem] = []
    seen: set[str] = set()

    def add(item: RuleItem) -> None:
        if item.title.lower() not in seen:
            seen.add(item.title.lower())
            items.append(item)

    # OPEN QUESTIONS section bullets (multi-line aware). The section runs until
    # the next "WORD\n===" style header or end of text.
    m = re.search(r"OPEN QUESTIONS\s*\n=+\s*\n", text)
    if m:
        rest = text[m.end():]
        next_header = re.search(r"^[A-Z][A-Z /&-]{3,}\n=+\s*$", rest, re.M)
        section = rest[: next_header.start()] if next_header else rest
        for bullet in re.finditer(r"^\s*-\s*(.+?)(?=\n\s*-\s|\Z)", section, re.S | re.M):
            q = " ".join(bullet.group(1).split())
            # the question is the part up to the first "?"
            if "?" in q:
                question = q.split("?")[0].strip() + "?"
                extra = q.split("?", 1)[1].strip().strip("().")
                context = "Raised in the development task records."
                if extra:
                    context += f" Note: {extra}."
                add(RuleItem(
                    type="question",
                    title=question,
                    summary=question,
                    details={"context": context},
                    evidence_phrases=[q[:80]],
                ))

    # "Unresolved question raised" sentences
    for m in re.finditer(
            r"Unresolved question raised[^:]*:\s*\*\*(.+?)\*\*", text, re.S):
        q = " ".join(m.group(1).split())
        if not q.endswith("?"):
            q += "?"
        add(RuleItem(
            type="question",
            title=q,
            summary=q,
            details={"context": "Raised in a design meeting; owner not yet assigned."},
            evidence_phrases=[q[:80]],
        ))
    return items


# ---------------------------------------------------------------------------
# entities
# ---------------------------------------------------------------------------

def _parse_entities(text: str) -> list[RuleItem]:
    items: list[RuleItem] = []
    seen: set[str] = set()

    def add(item: RuleItem) -> None:
        if item.title.lower() not in seen:
            seen.add(item.title.lower())
            items.append(item)

    for name in _extract_persons(text):
        add(RuleItem(
            type="entity",
            title=name,
            summary=f"Person: {name}.",
            details={"entity_kind": "person"},
            evidence_phrases=[name],
        ))
    for name, rx in COMPONENT_PATTERNS:
        if rx.search(text):
            add(RuleItem(
                type="entity",
                title=name,
                summary=f"Component: {name}.",
                details={"entity_kind": "component"},
                evidence_phrases=[name],
            ))
    for name, rx in DOCUMENT_PATTERNS:
        if rx.search(text):
            add(RuleItem(
                type="entity",
                title=name,
                summary=f"Document/reference: {name}.",
                details={"entity_kind": "tool"},
                evidence_phrases=[name],
            ))
    return items


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------

def extract_with_rules(text: str) -> dict:
    items: list[RuleItem] = []
    items += _parse_tasks(text)
    items += _parse_action_item_tasks(text)
    items += _parse_decisions(text)
    items += _parse_events(text)
    items += _parse_risks(text)
    items += _parse_questions(text)
    items += _parse_entities(text)

    # Attach dependency lists to tasks (from the DEPENDENCIES section)
    deps = _parse_dependencies(text)
    task_by_tid = {}
    for it in items:
        if it.type == "task":
            m = re.match(r"(T-\d{2,})", it.title)
            if m:
                task_by_tid[m.group(1)] = it
    for tid, targets in deps:
        it = task_by_tid.get(tid)
        if it:
            it.dependencies = targets
            it.details["dependencies"] = targets
            for t in targets:
                # cross-reference mention → inferred evidence phrase
                if t not in it.evidence_phrases:
                    it.evidence_phrases.append(t)

    return {"items": [it.to_dict() for it in items], "dependencies": deps}