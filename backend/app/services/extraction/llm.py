"""Gemini REST client via urllib (no external HTTP deps)."""
import json
import urllib.request
import urllib.error

from app.core.config import get_settings

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class LLMError(Exception):
    pass


EXTRACTION_PROMPT = """You are a knowledge-extraction engine for a project continuity platform.
Extract structured knowledge from the provided project document text.

Respond with STRICT JSON only (no markdown fences) matching exactly this schema:
{
  "decisions": [
    {"title": str, "summary": str, "reason": str|null,
     "alternatives": [str], "decided_on": "YYYY-MM-DD"|null,
     "affected": [str], "evidence_quote": str}
  ],
  "tasks": [
    {"title": str, "description": str|null, "assignee": str|null,
     "due_date": "YYYY-MM-DD"|null, "task_status": "completed|in_progress|pending|blocked",
     "dependencies": [str], "evidence_quote": str}
  ],
  "events": [
    {"title": str, "event_date": "YYYY-MM-DD"|null, "description": str|null,
     "evidence_quote": str}
  ],
  "risks": [
    {"title": str, "description": str|null, "severity": "low|medium|high|critical",
     "status": "open|mitigated|closed", "mentioned": true, "evidence_quote": str}
  ],
  "questions": [
    {"title": str, "context": str|null, "evidence_quote": str}
  ],
  "entities": [
    {"title": str, "entity_kind": "person|component|system|module|tool|organization",
     "evidence_quote": str}
  ]
}

Rules:
- "evidence_quote" MUST be a verbatim substring of the provided text (copy it exactly).
- Only include items actually present in the text. Never invent facts.
- task_status must be one of: completed, in_progress, pending, blocked.
- severity must be one of: low, medium, high, critical.
- decided_on / due_date / event_date: ISO dates only if present in the text, else null.
"""


def _post_json(url: str, payload: dict, timeout: int = 90) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMError(f"LLM HTTP {exc.code}: {body[:300]}") from exc
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"LLM request failed: {exc}") from exc


def _extract_text_from_response(data: dict) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected LLM response shape: {str(data)[:300]}") from exc


def generate_json(system_prompt: str, text: str, max_chars: int = 60000) -> dict:
    """Call the configured LLM and return parsed JSON. Raises LLMError on any
    failure (network, HTTP, non-JSON response)."""
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise LLMError("No API key configured")
    url = f"{API_BASE}/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": text[:max_chars]}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    data = _post_json(url, payload, timeout=90)
    raw = _extract_text_from_response(data)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM returned invalid JSON: {raw[:200]}") from exc


def extract_document(text: str) -> dict:
    """Run the extraction prompt against document text; returns the parsed
    JSON dict with keys decisions/tasks/events/risks/questions/entities."""
    return generate_json(EXTRACTION_PROMPT, text)


def answer_question(question: str, passages: list[dict]) -> str:
    """Grounded answer generation. passages: [{document_name, page, excerpt}].
    Returns the answer string. Raises LLMError on failure."""
    passage_text = "\n\n".join(
        f"[{i + 1}] ({p['document_name']}, page {p.get('page') or '?'})\n{p['excerpt']}"
        for i, p in enumerate(passages))
    prompt = f"""Answer the user's question using ONLY the provided passages.
If the passages do not contain enough information to answer, reply exactly with:
"INSUFFICIENT_EVIDENCE"
Otherwise answer in 2-4 sentences, citing the passage numbers like [1].

PASSAGES:
{passage_text}

QUESTION: {question}
"""
    settings = get_settings()
    url = f"{API_BASE}/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    data = _post_json(url, payload, timeout=90)
    answer = _extract_text_from_response(data).strip()
    return answer