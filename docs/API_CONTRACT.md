# CONTINUITY AI — API Contract (v1)

This is the single source of truth for the backend REST API. The frontend is built
strictly against these shapes. All JSON bodies are UTF-8. Timestamps are ISO-8601
strings (e.g. `2026-10-12T14:30:00Z`). IDs are integers.

Base URL (dev): `http://localhost:8000`
Frontend dev proxy: Vite proxies `/api` and `/health` → `http://localhost:8000`.

## Conventions

- Errors: `{ "detail": "human readable message" }` with an appropriate HTTP status
  (400 validation, 404 not found, 409 conflict/duplicate, 422 processing failed, 502 AI unavailable).
- Every list endpoint returns a plain JSON array.
- `evidence_status` ∈ `supported | inferred | conflicting | unverified`
- `review_status` ∈ `pending | approved | rejected | flagged`
- `knowledge_type` ∈ `decision | task | event | risk | question | entity`
- `task_status` ∈ `completed | in_progress | pending | blocked` (null allowed)
- `severity` ∈ `low | medium | high | critical` (risk only)
- `document_status` ∈ `uploaded | processing | processed | failed | needs_attention`

## Envelope helpers

A knowledge item always appears in this shape (call it `KnowledgeItem`):

```json
{
  "id": 12,
  "project_id": 1,
  "type": "decision",
  "title": "Select Motor Controller A",
  "summary": "Controller A chosen over B and C after thermal testing.",
  "details": {
    "reason": "Better thermal performance during testing",
    "alternatives": ["Motor Controller B", "Motor Controller C"],
    "decided_on": "2026-09-18",
    "affected": ["Motor system", "Power distribution"]
  },
  "status": "pending",
  "task_status": null,
  "severity": null,
  "assignee": null,
  "due_date": null,
  "dependencies": [],
  "evidence_status": "supported",
  "review_status": "pending",
  "evidence": [
    {
      "document_id": 3,
      "document_name": "Meeting_Notes_October.docx",
      "chunk_id": 17,
      "page": 2,
      "excerpt": "The team selected Controller A after testing both alternatives. Thermal performance was a key consideration."
    }
  ],
  "relationships": [
    { "type": "affects", "target_type": "entity", "target_id": 5, "target_title": "Motor system" }
  ],
  "created_at": "2026-11-03T08:00:00Z",
  "updated_at": "2026-11-03T08:05:00Z",
  "reviewed_by": null,
  "reviewed_at": null
}
```

`details` is a free-form object whose keys depend on `type`:

- decision: `reason`, `alternatives[]`, `decided_on`, `affected[]`
- task: `description`, `assignee`, `due_date`, `dependencies[]`
- event: `event_date`, `description`
- risk: `severity`, `description`, `status` (open|mitigated|closed), `mentioned` (bool: true if the source explicitly states it, false if model-inferred)
- question: `context`
- entity: `entity_kind` (person|component|system|module|tool|organization)

`details` may contain `null` values; the UI must render "Not specified" for them.

## Endpoints

### Health & meta

`GET /health` → `200`
```json
{ "status": "ok", "version": "1.0.0", "ai_configured": true, "ai_provider": "gemini" }
```
`ai_configured` is false when no LLM key is set (extraction still works via the
deterministic fallback; the UI shows a banner "AI key not configured — using
deterministic extraction").

### Projects

`POST /api/projects` body:
```json
{ "name": "Autonomous Delivery Robot Development",
  "description": "Six-month development of an autonomous delivery robot.",
  "category": "R&D",
  "objectives": ["Ship a working prototype", "Pass thermal validation"],
  "status": "active" }
```
→ `201` `Project` (below).

`GET /api/projects` → `200` `Project[]`

`GET /api/projects/{id}` → `200` `Project`
```json
{
  "id": 1,
  "name": "Autonomous Delivery Robot Development",
  "description": "...",
  "category": "R&D",
  "objectives": ["..."],
  "status": "active",
  "created_at": "2026-11-03T08:00:00Z",
  "updated_at": "2026-11-03T08:00:00Z",
  "stats": {
    "documents": 4,
    "decisions": 5,
    "tasks": 12,
    "open_tasks": 7,
    "risks": 6,
    "unresolved": 4,
    "pending_reviews": 9,
    "events": 8,
    "entities": 14,
    "conflicts": 1,
    "continuity": {
      "completed": 4, "in_progress": 3, "pending": 4, "blocked": 1,
      "total": 12, "percent": 33.3, "available": true
    }
  }
}
```
`stats.continuity` is computed from task statuses. `available` is false (and
`percent` null) when there are no tasks — the UI then shows "Unavailable".

`PATCH /api/projects/{id}` body: any subset of `name, description, category, objectives, status` → `200` `Project`

`DELETE /api/projects/{id}` → `200` `{ "deleted": true }` (removes all related data + files)

### Documents

`POST /api/projects/{id}/documents` — multipart/form-data, field name `files`
(one or more files). → `201` `Document[]` (one entry per file).
Validation: allowed extensions `.pdf .docx .txt .md`; max 15 MB each; max 20 files
per request. Duplicate file name within the same project → `409` with
`detail` naming the file.

`GET /api/projects/{id}/documents` → `200` `Document[]`
```json
{
  "id": 3,
  "project_id": 1,
  "file_name": "Meeting_Notes_October.docx",
  "file_type": "docx",
  "size_bytes": 48211,
  "status": "processed",
  "error": null,
  "page_count": 3,
  "chunk_count": 9,
  "uploaded_at": "2026-11-03T08:02:00Z",
  "processed_at": "2026-11-03T08:02:04Z"
}
```

`GET /api/documents/{id}/preview` → `200`
```json
{ "document": { ...Document... }, "text": "full extracted text...", "chunks": [
  { "id": 17, "page": 2, "text": "..." }
] }
```

`POST /api/documents/{id}/process` → `200` `Document` (re-runs extraction +
knowledge extraction for this document; deletes and recreates its chunks and
knowledge items). If extraction fails → `422` with `error` set on the document.

`DELETE /api/documents/{id}` → `200` `{ "deleted": true }` (removes the file,
chunks, and knowledge items that cite ONLY this document; items citing multiple
documents keep their remaining evidence).

### Knowledge

`GET /api/projects/{id}/knowledge?type=&status=&review_status=&q=&sort=` → `200` `KnowledgeItem[]`
Query params (all optional):
- `type`: one of the knowledge types, or `all`
- `status`: for tasks, one of task statuses
- `review_status`: `pending | approved | rejected | flagged`
- `q`: case-insensitive substring search over title/summary/details
- `sort`: `created_at` (default) | `updated_at` | `title`
- `order`: `asc` | `desc` (default desc)

`GET /api/knowledge/{id}` → `200` `KnowledgeItem`

`PATCH /api/knowledge/{id}` body: any subset of
`{ "title", "summary", "details": {...}, "status", "task_status", "severity",
  "assignee", "due_date", "dependencies" }` → `200` `KnowledgeItem`
(sets `review_status` back to `pending` if it was approved, and records an audit
entry "record edited").

`POST /api/knowledge/{id}/review` body:
```json
{ "action": "approve", "reviewer": "Demo Reviewer", "note": "Verified against source." }
```
`action` ∈ `approve | reject | flag | resolve_conflict`.
- `approve` → `review_status: approved`
- `reject` → `review_status: rejected`
- `flag` → `review_status: flagged`
- `resolve_conflict` → `review_status: approved`, `evidence_status: supported`
  (requires `note` explaining which side was kept)
→ `200` `KnowledgeItem`. All actions write an audit log entry.

`GET /api/projects/{id}/timeline` → `200` chronological events:
```json
[ { "id": 20, "date": "2026-09-18", "title": "Controller A selected",
    "type": "event", "description": "...", "evidence": [ ... ] } ]
```
Sorted by `date` asc (events without a date go last, by created_at).

`GET /api/projects/{id}/conflicts` → `200`
```json
[ { "topic": "Integration testing status",
    "items": [ { "id": 31, "title": "...", "evidence": [...] },
               { "id": 44, "title": "...", "evidence": [...] } ] } ]
```

### Assistant

`POST /api/projects/{id}/ask` body: `{ "question": "Why was Controller A selected?" }`
→ `200`
```json
{
  "question": "Why was Controller A selected?",
  "answer": "Controller A was selected following comparative testing...",
  "evidence_status": "supported",
  "confidence": 0.82,
  "citations": [
    { "document_id": 3, "document_name": "Meeting_Notes_October.docx",
      "page": 2, "excerpt": "The team selected Controller A after testing both alternatives..." }
  ],
  "related": [ { "id": 12, "type": "decision", "title": "Select Motor Controller A" } ],
  "warnings": ["Two sources disagree on integration testing status."]
}
```
`evidence_status` is `supported` when relevant passages were found, else
`insufficient` — in which case `answer` MUST be a statement that the available
records do not establish the answer (never a fabricated one). `confidence` is a
0–1 float derived from retrieval scores. `warnings` lists detected conflicts or
insufficient-evidence notes.

### Handover

`POST /api/projects/{id}/handovers` body: `{ "audience": "general" }`
(`audience` ∈ `general | engineer`) → `201`
```json
{
  "id": 1,
  "project_id": 1,
  "project_name": "Autonomous Delivery Robot Development",
  "audience": "general",
  "version": 1,
  "status": "generated",
  "generated_at": "2026-11-03T09:00:00Z",
  "sections": [
    { "key": "overview", "title": "1. Project Overview", "content": "..." },
    { "key": "objectives", "title": "2. Project Objectives", "content": "..." },
    { "key": "status", "title": "3. Current Project Status", "content": "..." },
    { "key": "completed", "title": "4. Completed Activities", "content": "..." },
    { "key": "in_progress", "title": "5. In-Progress Activities", "content": "..." },
    { "key": "pending", "title": "6. Pending Tasks", "content": "..." },
    { "key": "decisions", "title": "7. Important Decisions and Reasoning", "content": "..." },
    { "key": "architecture", "title": "8. Technical Architecture Changes", "content": "..." },
    { "key": "unresolved", "title": "9. Unresolved Issues", "content": "..." },
    { "key": "risks", "title": "10. Risks and Blockers", "content": "..." },
    { "key": "dependencies", "title": "11. Dependencies", "content": "..." },
    { "key": "milestones", "title": "12. Events and Milestones", "content": "..." },
    { "key": "next_actions", "title": "13. Recommended Next Actions", "content": "..." },
    { "key": "evidence", "title": "14. Evidence and Source References", "content": "..." },
    { "key": "verification", "title": "15. Verification Status", "content": "..." }
  ],
  "summary": { "decisions": 5, "tasks": 12, "risks": 6, "unresolved": 4,
               "approved": 3, "pending": 9 }
}
```
`content` strings may contain simple markdown (headings `##`, bullets `-`,
bold `**`). The UI renders them with a small markdown renderer.

`GET /api/projects/{id}/handovers` → `200` list of handover metadata (same shape
without `sections`).

`GET /api/handovers/{id}` → `200` full handover (with sections).

`GET /api/handovers/{id}/download` → `200` `application/pdf`
(`Content-Disposition: attachment; filename="CONTINUITY_AI_Handover_<project>_<ts>.pdf"`).

### Audit

`GET /api/projects/{id}/audit?limit=50` → `200`
```json
[ { "id": 8, "project_id": 1, "action": "record_approved",
    "entity_type": "knowledge", "entity_id": 12, "entity_title": "Select Motor Controller A",
    "reviewer": "Demo Reviewer", "detail": "Verified against source.",
    "created_at": "2026-11-03T09:10:00Z" } ]
```
`action` ∈ `project_created | document_uploaded | document_processed |
document_deleted | knowledge_created | record_edited | record_approved |
record_rejected | record_flagged | conflict_resolved | handover_generated`.

### Settings (runtime info)

`GET /api/settings` → `200`
```json
{ "ai_configured": true, "ai_provider": "gemini", "ai_model": "gemini-2.0-flash",
  "allowed_extensions": [".pdf", ".docx", ".txt", ".md"],
  "max_file_mb": 15, "max_files_per_upload": 20,
  "data_disclosure": "Document text is sent to the configured LLM provider for extraction and question answering when an API key is configured. With no key, a deterministic local extractor is used and no text leaves this machine." }
```

## Frontend → backend notes

- The frontend never calls the LLM directly; all AI work happens server-side.
- Polling: after upload, the frontend polls `GET /api/projects/{id}/documents`
  every 2.5 s until no document has status `processing`/`uploaded`.
- The "Process" button calls `POST /api/documents/{id}/process` then polls.
- All knowledge list views use one endpoint with query params (no separate
  endpoints per type).