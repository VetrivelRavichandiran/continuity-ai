# Continuity AI

A self-hosted knowledge-management app for teams. Upload project documents, and the system extracts structured knowledge (facts, decisions, risks, tasks, people, tech), builds a relationship graph, detects conflicts between documents, answers questions with evidence, and generates a handover document (HTML + PDF) when someone leaves the project.

## Features

- **Projects & document upload** — PDF, DOCX, TXT, MD (max 15 MB / 20 files per upload), background processing with status polling
- **Knowledge extraction** — rule-based engine + optional Gemini LLM (structured JSON output, validated & merged)
- **Knowledge graph** — typed relationships between people, decisions, risks, tasks, tech, milestones
- **Conflict detection** — verifies contradictions between documents (e.g. two different deadlines) with evidence
- **Assistant** — RAG-style Q&A over project knowledge (TF-IDF retrieval + LLM), every answer cites its evidence
- **Handover** — one-click handover document (HTML + PDF) covering status, open items, risks, people, and knowledge
- **Audit log** — full trail of extraction, conflicts, and assistant activity
- **Settings** — per-project LLM model, temperature, extraction mode
- **Dark/light UI** — React + Tailwind, responsive

## Tech stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, SQLite |
| Extraction | PyMuPDF (PDF), python-docx (DOCX), regex rules, Gemini API (optional) |
| Retrieval | scikit-learn TF-IDF |
| PDF output | ReportLab |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, lucide-react |

## Project structure

```
continuity-ai/
├── backend/
│   ├── requirements.txt
│   ├── e2e_check.py              # end-to-end smoke test (no API key needed)
│   └── app/
│       ├── main.py               # FastAPI app, CORS, startup, static SPA serving
│       ├── core/
│       │   └── config.py         # settings (env vars), security helpers
│       ├── database/             # SQLAlchemy engine/session
│       ├── models/               # Project, Document, Chunk, KnowledgeItem, Relationship, Conflict, AuditLog, Handover
│       ├── schemas/              # Pydantic schemas
│       ├── api/                  # routers: projects, documents, knowledge, assistant, handover, settings, audit
│       └── services/
│           ├── extraction/       # engine, rules, Gemini LLM client
│           ├── ingestion/        # text extraction (pdf/docx/txt/md), chunking
│           ├── retrieval/        # TF-IDF retrieval
│           ├── verification/     # conflict detection
│           └── handover/         # handover builder + ReportLab PDF
├── frontend/
│   ├── package.json
│   ├── vite.config.ts            # dev proxy /api -> :8000
│   └── src/
│       ├── main.tsx, App.tsx, index.css
│       ├── lib/                  # types.ts, api.ts (fetch client + polling)
│       ├── components/           # AppShell, EvidenceList, KnowledgeItemCard, KnowledgeDetailModal, ui
│       └── pages/                # Dashboard, ProjectOverview, Documents, Knowledge, Timeline, Conflicts, Assistant, Handover, Audit, Settings
├── sample-data/                  # sample project docs (md/docx/txt)
├── docs/API_CONTRACT.md          # full REST API reference
└── make_sample_docs.py           # regenerates sample-data/
```

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # or use system python
pip install -r requirements.txt

# Optional: enable LLM extraction & assistant (otherwise rule-based mode is used)
export GEMINI_API_KEY="your-key-here"

uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api to :8000)
```

### Windows (PowerShell)

PowerShell below 7.0 does **not** support `&&` — run each command on its own line.

**Terminal 1 — backend:**
```powershell
cd E:\continuity-ai\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

If `Activate.ps1` is blocked by execution policy, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.\.venv\Scripts\Activate.bat` instead.

**Troubleshooting `python -m venv` on Windows:** if it fails with
`Could not find platform independent libraries <prefix>` / `No module named 'types'`,
your Python install is broken or `PYTHONHOME`/`PYTHONPATH` is mis-set.
Check with `echo $env:PYTHONHOME` and `echo $env:PYTHONPATH`, remove any values
(`Remove-Item Env:\PYTHONHOME`), delete the half-created `.venv`, and retry —
or reinstall Python 3.11+ from python.org with **"Add python.exe to PATH"** ticked.

**Terminal 2 — frontend:**
```powershell
cd E:\continuity-ai\frontend
npm install
npm run dev
```

### 3. Use it

1. Open http://localhost:5173
2. Create a project (e.g. "Website Redesign")
3. Upload documents from `sample-data/` (or your own)
4. Watch knowledge items, relationships, and conflicts appear
5. Ask questions in **Assistant**, open **Handover** to generate the handover doc

### Production build

```bash
cd frontend
npm run build        # outputs frontend/dist/
# serve dist/ statically and proxy /api to the backend, or:
# uvicorn serves the built frontend automatically if dist/ exists
```

## Configuration (env vars)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(empty)* | Enables Gemini LLM extraction & assistant. Without it, rule-based extraction is used. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | LLM model for extraction & assistant |
| `DATA_DIR` | `./data` | Where SQLite DB + generated handover files live |
| `MAX_FILE_MB` | `15` | Max upload size per file |
| `MAX_FILES_PER_UPLOAD` | `20` | Max files per upload request |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins |

## Running the end-to-end test

```bash
cd backend
python3 e2e_check.py
```

Creates a project, uploads the sample docs, waits for processing, and verifies knowledge extraction, relationships, conflicts, assistant, handover, and audit — all without an API key.

## Notes

- Works fully offline (rule-based extraction + TF-IDF retrieval); the LLM adds richer extraction and conversational answers.
- All data is stored in a single SQLite file at `data/continuity.db`; uploaded documents are kept under `data/files/`.
- Handover PDFs are rendered on demand and served via `/api/handovers/{id}/download`.