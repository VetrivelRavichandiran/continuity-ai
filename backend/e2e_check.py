"""Full E2E check against the running backend."""
import json
import time
import urllib.request
import urllib.error
from collections import Counter

BASE = "http://localhost:8000"
PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, extra=""):
    results.append((PASS if cond else FAIL, name, extra))
    print(f"[{PASS if cond else FAIL}] {name} {extra}")


def req(method, path, body=None, raw=False, files=None):
    url = BASE + path
    data = None
    headers = {}
    if files is not None:
        boundary = "----e2eboundary123"
        parts = []
        for fname, content in files:
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(f'Content-Disposition: form-data; name="files"; filename="{fname}"\r\n'.encode())
            parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
            parts.append(content)
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            payload = resp.read()
            if raw:
                return resp.status, payload, dict(resp.headers)
            return resp.status, json.loads(payload)
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            body = json.loads(payload)
        except Exception:
            body = {"raw": payload.decode(errors="replace")}
        if raw:
            return e.code, body, {}
        return e.code, body


# --- create project ---
st, proj = req("POST", "/api/projects", {
    "name": "Autonomous Delivery Robot Development",
    "description": "Six-month development of an autonomous delivery robot.",
    "category": "R&D",
    "objectives": ["Ship a working prototype", "Pass thermal validation"],
    "status": "active",
})
check("create project 201", st == 201, f"status={st} id={proj.get('id')}")
pid = proj["id"]

# --- upload all four sample files ---
import pathlib
sd = pathlib.Path(__file__).parent.parent / "sample-data"
files = [
    ("project-overview.md", (sd / "project-overview.md").read_bytes()),
    ("meeting-notes.docx", (sd / "meeting-notes.docx").read_bytes()),
    ("technical-report.md", (sd / "technical-report.md").read_bytes()),
    ("development-tasks.txt", (sd / "development-tasks.txt").read_bytes()),
]
st, docs = req("POST", f"/api/projects/{pid}/documents", files=files)
check("upload 4 files 201", st == 201 and len(docs) == 4, f"status={st} n={len(docs)}")

# --- poll until all processed ---
deadline = time.time() + 60
all_done = False
while time.time() < deadline:
    st, dl = req("GET", f"/api/projects/{pid}/documents")
    pending = [d for d in dl if d["status"] in ("processing", "uploaded")]
    if not pending:
        all_done = True
        break
    time.sleep(1)
check("all documents processed", all_done,
      f"statuses={[d['status'] for d in dl]}")
failed = [d for d in dl if d["status"] == "failed"]
check("no failed documents", not failed,
      f"failed={[d['file_name'] for d in failed]} errors={[d['error'] for d in failed]}")

# --- knowledge counts ---
st, k = req("GET", f"/api/projects/{pid}/knowledge")
c = Counter(x["type"] for x in k)
print("   knowledge counts:", dict(c))
check(">=4 decisions", c.get("decision", 0) >= 4, f"n={c.get('decision',0)}")
check(">=10 tasks", c.get("task", 0) >= 10, f"n={c.get('task',0)}")
check(">=5 risks", c.get("risk", 0) >= 5, f"n={c.get('risk',0)}")
check(">=4 questions", c.get("question", 0) >= 4, f"n={c.get('question',0)}")
check(">=4 events", c.get("event", 0) >= 4, f"n={c.get('event',0)}")
check(">=6 entities", c.get("entity", 0) >= 6, f"n={c.get('entity',0)}")

# --- integration-testing conflict ---
st, conf = req("GET", f"/api/projects/{pid}/conflicts")
check("conflicts non-empty", st == 200 and len(conf) > 0, f"n={len(conf)}")
it_conflict = False
for cf in conf:
    titles = " ".join(it["title"] for it in cf["items"]).lower()
    if "integration" in titles and "test" in titles:
        it_conflict = True
        print("   integration-testing conflict topic:", cf["topic"])
        for it in cf["items"]:
            print("     -", it["type"], it["title"][:70])
check("integration-testing conflict exists", it_conflict)

# --- timeline ---
st, tl = req("GET", f"/api/projects/{pid}/timeline")
check("timeline non-empty", st == 200 and len(tl) > 0, f"n={len(tl)}")

# --- ask: Controller A ---
st, ask1 = req("POST", f"/api/projects/{pid}/ask",
               {"question": "Why was Controller A selected?"})
check("ask Controller A 200", st == 200, f"status={st}")
check("ask Controller A mentions thermal",
      "thermal" in ask1.get("answer", "").lower(),
      f"answer={ask1.get('answer','')[:120]!r}")
check("ask Controller A citations non-empty", len(ask1.get("citations", [])) > 0,
      f"n={len(ask1.get('citations',[]))}")
print("   ask1 evidence_status:", ask1.get("evidence_status"),
      "confidence:", ask1.get("confidence"))

# --- ask: capital of France (insufficient) ---
st, ask2 = req("POST", f"/api/projects/{pid}/ask",
               {"question": "What is the capital of France?"})
check("ask France 200", st == 200, f"status={st}")
check("ask France evidence_status insufficient",
      ask2.get("evidence_status") == "insufficient",
      f"evidence_status={ask2.get('evidence_status')}")
print("   ask2 answer:", ask2.get("answer", "")[:120])

# --- PATCH a knowledge item ---
some_item = k[0]
st, patched = req("PATCH", f"/api/knowledge/{some_item['id']}",
                  {"title": some_item["title"] + " (edited)"})
check("PATCH knowledge 200", st == 200, f"status={st}")
check("PATCH title saved", patched.get("title", "").endswith("(edited)"),
      f"title={patched.get('title')!r}")

# --- audit has record_edited ---
st, audit = req("GET", f"/api/projects/{pid}/audit?limit=200")
actions = [a["action"] for a in audit]
check("audit has record_edited", "record_edited" in actions,
      f"actions_sample={actions[:8]}")

# --- review approve ---
st, reviewed = req("POST", f"/api/knowledge/{some_item['id']}/review",
                   {"action": "approve", "reviewer": "Demo Reviewer",
                    "note": "Verified against source."})
check("review approve 200", st == 200, f"status={st}")
check("review_status approved", reviewed.get("review_status") == "approved",
      f"review_status={reviewed.get('review_status')}")
st, audit2 = req("GET", f"/api/projects/{pid}/audit?limit=200")
check("audit has record_approved",
      any(a["action"] == "record_approved" for a in audit2))

# --- handover (general) ---
st, ho = req("POST", f"/api/projects/{pid}/handovers", {"audience": "general"})
check("handover 201", st == 201, f"status={st}")
secs = ho.get("sections", [])
check("handover 15 sections", len(secs) == 15, f"n={len(secs)}")
keys = [s["key"] for s in secs]
expected_keys = ["overview", "objectives", "status", "completed", "in_progress",
                 "pending", "decisions", "architecture", "unresolved", "risks",
                 "dependencies", "milestones", "next_actions", "evidence", "verification"]
check("handover section keys match contract", keys == expected_keys,
      f"keys={keys}")
real_content = sum(1 for s in secs
                   if s["content"] and s["content"] != "No records of this type were found in the uploaded sources.")
check("handover has real content", real_content >= 8, f"sections_with_content={real_content}")
print("   handover summary:", ho.get("summary"))

# --- handover download -> valid PDF ---
st, pdf_bytes, hdrs = req("GET", f"/api/handovers/{ho['id']}/download", raw=True)
check("handover download 200", st == 200, f"status={st}")
ct = {k.lower(): v for k, v in hdrs.items()}.get("content-type", "")
check("content-type pdf", "application/pdf" in ct, f"ct={ct}")
check("pdf magic bytes", pdf_bytes[:4] == b"%PDF", f"head={pdf_bytes[:8]!r}")
import pymupdf
doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
check("pdf valid + >=1 page", doc.page_count >= 1, f"pages={doc.page_count}")
text_sample = doc[0].get_text()
check("pdf has project name", "Autonomous Delivery Robot" in text_sample,
      f"page1_has_name={'Autonomous Delivery Robot' in text_sample}")
doc.close()

# --- engineer handover reorders ---
st, ho2 = req("POST", f"/api/projects/{pid}/handovers", {"audience": "engineer"})
check("engineer handover 201", st == 201, f"status={st}")
ekeys = [s["key"] for s in ho2.get("sections", [])]
check("engineer reorders (decisions first)", ekeys[0] == "decisions",
      f"first3={ekeys[:3]}")
check("engineer version incremented", ho2.get("version", 0) > ho.get("version", 0),
      f"v1={ho.get('version')} v2={ho2.get('version')}")

# --- settings ---
st, settings = req("GET", "/api/settings")
check("settings 200", st == 200, f"status={st}")
check("settings ai_configured false", settings.get("ai_configured") is False)
check("settings max_file_mb 15", settings.get("max_file_mb") == 15)

# --- project stats ---
st, p = req("GET", f"/api/projects/{pid}")
stats = p.get("stats", {})
check("project stats continuity available", stats.get("continuity", {}).get("available") is True,
      f"continuity={stats.get('continuity')}")
check("project stats conflicts >=1", stats.get("conflicts", 0) >= 1,
      f"conflicts={stats.get('conflicts')}")

# --- duplicate file name -> 409 ---
st, dup = req("POST", f"/api/projects/{pid}/documents",
              files=[("project-overview.md", b"# dup")])
check("duplicate file name 409", st == 409, f"status={st} detail={dup.get('detail')}")

# --- wrong extension -> 400 ---
st, bad = req("POST", f"/api/projects/{pid}/documents",
              files=[("evil.exe", b"MZ...")])
check("wrong extension 400", st == 400, f"status={st} detail={bad.get('detail')}")

# --- oversized -> 400 ---
big = b"x" * (16 * 1024 * 1024)
st, bigres = req("POST", f"/api/projects/{pid}/documents",
                 files=[("big.md", big)])
check("oversized file 400", st == 400, f"status={st} detail={bigres.get('detail')}")

# --- empty file -> failed ---
st, emptyres = req("POST", f"/api/projects/{pid}/documents",
                   files=[("empty.md", b"   \n  ")])
check("empty file upload 201 then failed", st == 201, f"status={st}")
if st == 201:
    time.sleep(2)
    st, dl = req("GET", f"/api/projects/{pid}/documents")
    empty_doc = next((d for d in dl if d["file_name"] == "empty.md"), None)
    check("empty file status failed",
          empty_doc and empty_doc["status"] == "failed",
          f"status={empty_doc and empty_doc['status']} error={empty_doc and empty_doc['error']}")

# --- process endpoint on a doc ---
st, dl = req("GET", f"/api/projects/{pid}/documents")
first_doc = next(d for d in dl if d["file_name"] == "project-overview.md")
st, proc = req("POST", f"/api/documents/{first_doc['id']}/process")
check("process endpoint 200", st == 200, f"status={st} error={proc.get('error')}")

# --- knowledge GET filters ---
st, tasks = req("GET", f"/api/projects/{pid}/knowledge?type=task&status=in_progress")
check("knowledge filter type+status", st == 200 and all(
    t["type"] == "task" and t["task_status"] == "in_progress" for t in tasks),
    f"n={len(tasks)}")
st, qres = req("GET", f"/api/projects/{pid}/knowledge?q=controller")
check("knowledge q search", st == 200 and len(qres) > 0, f"n={len(qres)}")

# --- document preview ---
st, prev = req("GET", f"/api/documents/{first_doc['id']}/preview")
check("document preview 200", st == 200, f"status={st}")
check("preview has text+chunks", bool(prev.get("text")) and len(prev.get("chunks", [])) > 0,
      f"text_len={len(prev.get('text',''))} chunks={len(prev.get('chunks',[]))}")

# --- delete document ---
st, dl = req("GET", f"/api/projects/{pid}/documents")
empty_doc = next((d for d in dl if d["file_name"] == "empty.md"), None)
if empty_doc:
    st, dres = req("DELETE", f"/api/documents/{empty_doc['id']}")
    check("delete document 200", st == 200 and dres.get("deleted") is True, f"status={st}")

# --- summary ---
print("\n" + "=" * 60)
n_pass = sum(1 for r in results if r[0] == PASS)
n_fail = sum(1 for r in results if r[0] == FAIL)
print(f"E2E RESULT: {n_pass} passed, {n_fail} failed")
for r in results:
    if r[0] == FAIL:
        print("  FAILED:", r[1], r[2])