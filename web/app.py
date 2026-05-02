"""
Flask web dashboard for the LLM Prompt Injection Lab.
Run with: python web/app.py
Then open: http://localhost:5000
"""

import sys
import os
import threading

# Allow imports from the project root regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import queue
import uuid
from flask import Flask, render_template, jsonify, request, Response, stream_with_context

from lab import (
    PromptInjectionLab, OllamaClient, ResultsDB,
    build_payloads, MODELS, DB_PATH,
)
from scripts.report import generate_report

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Active-run registry
# ---------------------------------------------------------------------------

_runs: dict[str, dict] = {}
_runs_lock = threading.Lock()


class _QueueWriter:
    """Redirect stdout writes into a Queue so SSE can forward them."""
    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, s: str):
        if s.strip():
            self.q.put(s.rstrip())

    def flush(self):
        pass


def _execute_run(run_id: str, models: list[str], runs: int, system_prompt: str = None):
    q = _runs[run_id]["queue"]
    _runs[run_id]["status"] = "running"

    old_stdout = sys.stdout
    sys.stdout = _QueueWriter(q)
    try:
        lab = PromptInjectionLab(models=models, runs_per_payload=runs, system_prompt=system_prompt)
        lab.run()
        generate_report()
        q.put("__DONE__")
        _runs[run_id]["status"] = "done"
    except Exception as exc:
        q.put(f"[ERROR] {exc}")
        q.put("__DONE__")
        _runs[run_id]["status"] = "error"
    finally:
        sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API — meta
# ---------------------------------------------------------------------------

@app.route("/api/models")
def api_models():
    client = OllamaClient()
    try:
        available = client.list_models()
    except Exception:
        available = []
    return jsonify({"available": available, "defaults": MODELS})


@app.route("/api/payloads")
def api_payloads():
    payloads = build_payloads()
    return jsonify([
        {
            "name": p.name,
            "type": p.payload_type,
            "severity": p.severity,
            "prompt_preview": p.prompt[:300] + ("…" if len(p.prompt) > 300 else ""),
            "indicators": p.success_indicators,
        }
        for p in payloads
    ])


# ---------------------------------------------------------------------------
# API — stats & results
# ---------------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    db = ResultsDB(DB_PATH)
    try:
        stats = db.fetch_stats()
        all_rows = db.fetch_all()
        total = len(all_rows)
        successes = sum(1 for r in all_rows if r["success"] == "yes")
        stats["total_runs"] = total
        stats["total_successes"] = successes
        stats["overall_rate"] = round(successes / total * 100, 1) if total else 0
        return jsonify(stats)
    except Exception as exc:
        return jsonify({"error": str(exc), "total_runs": 0}), 200


@app.route("/api/results")
def api_results():
    model  = request.args.get("model", "")
    ptype  = request.args.get("type", "")
    success = request.args.get("success", "")
    limit  = int(request.args.get("limit", 200))
    offset = int(request.args.get("offset", 0))

    db = ResultsDB(DB_PATH)
    rows = db.fetch_all()

    if model:
        rows = [r for r in rows if r["model_name"] == model]
    if ptype:
        rows = [r for r in rows if r["payload_type"] == ptype]
    if success in ("yes", "no"):
        rows = [r for r in rows if r["success"] == success]

    total = len(rows)
    rows = rows[offset: offset + limit]
    return jsonify({"total": total, "rows": rows})


# ---------------------------------------------------------------------------
# API — results management
# ---------------------------------------------------------------------------

@app.route("/api/results/clear", methods=["DELETE"])
def api_clear_results():
    db = ResultsDB(DB_PATH)
    db.clear_all()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API — run control
# ---------------------------------------------------------------------------

@app.route("/api/run", methods=["POST"])
def api_start_run():
    body          = request.get_json(silent=True) or {}
    models        = body.get("models") or MODELS
    runs          = int(body.get("runs", 5))
    system_prompt = body.get("system_prompt") or None

    run_id = str(uuid.uuid4())[:8]
    with _runs_lock:
        _runs[run_id] = {
            "status": "pending",
            "queue": queue.Queue(),
        }

    t = threading.Thread(target=_execute_run, args=(run_id, models, runs, system_prompt), daemon=True)
    t.start()

    return jsonify({"run_id": run_id})


@app.route("/api/run/<run_id>/status")
def api_run_status(run_id: str):
    with _runs_lock:
        run = _runs.get(run_id)
    if not run:
        return jsonify({"error": "not found"}), 404
    return jsonify({"status": run["status"]})


@app.route("/api/run/<run_id>/stream")
def api_run_stream(run_id: str):
    """Server-Sent Events stream of live lab output."""
    with _runs_lock:
        run = _runs.get(run_id)
    if not run:
        return jsonify({"error": "not found"}), 404

    q: queue.Queue = run["queue"]

    def event_stream():
        consecutive_empty = 0
        while True:
            try:
                msg = q.get(timeout=25)
                consecutive_empty = 0
            except queue.Empty:
                yield ": keepalive\n\n"
                consecutive_empty += 1
                if consecutive_empty >= 12:
                    run_status = _runs[run_id].get("status")
                    if run_status in ("done", "error"):
                        yield "data: __DONE__\n\n"
                    else:
                        yield "data: [TIMEOUT — no output for 5 min, run may have stalled]\n\n"
                        yield "data: __DONE__\n\n"
                    break
                continue

            if msg == "__DONE__":
                yield "data: __DONE__\n\n"
                break

            escaped = msg.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000, threaded=True)
