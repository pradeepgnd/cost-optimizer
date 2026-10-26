"""Shared operations behind the Streamlit UI. Business rules stay in the core: a run is executed by `run.py`, the same
entry point the CLI uses, so UI and CLI cannot diverge. A run ID owns one result file; asking again loads it and never
starts a second (possibly paid) run."""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from pydantic import ValidationError

from app.contracts import RunRequest

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "data" / "ui"
EXAMPLES_DIR = ROOT / "input_examples"
FEATURE_DEFAULTS = {"calls_per_use": "1", "expected_output_words": 100, "mode": "interactive", "rubric_checks": []}
MODALITIES = ("text", "audio_in", "audio_out", "image_in", "image_out")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


DEFAULT_BINDINGS = ROOT / "data" / "localstack" / "bindings.json"   # where the README's source setup writes it


def find_bindings(override: str = "") -> dict:
    """Which Zetaris bindings file a live run will use, and what it pins. Order: an explicit override, then
    ZETARIS_BINDINGS_FILE (environment or .env), then the README's default location. Never guesses another file."""
    for source, value in (("override", override), ("ZETARIS_BINDINGS_FILE", os.getenv("ZETARIS_BINDINGS_FILE", "")),
                          ("default location", str(DEFAULT_BINDINGS))):
        if not value.strip():
            continue
        path = Path(value.strip()).expanduser()
        path = path if path.is_absolute() else ROOT / path
        if not path.exists():
            if source == "default location":
                break
            return {"ok": False, "source": source, "path": str(path), "problem": "file not found"}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {"ok": True, "source": source, "path": str(path), "snapshot_id": data["snapshot_id"],
                    "counts": data.get("expected_counts", {})}
        except (ValueError, KeyError, OSError) as error:
            return {"ok": False, "source": source, "path": str(path), "problem": f"not a bindings file ({type(error).__name__})"}
    return {"ok": False, "source": None, "path": None,
            "problem": "no bindings file: set ZETARIS_BINDINGS_FILE in .env, or run the source setup (README, Level 2), "
                       "which writes data/localstack/bindings.json"}


ROUTE_MAP = ROOT / "data" / "source_examples" / "routes.selected.json"


def candidate_options(sample: bool, bindings_path: str = "") -> dict[str, str]:
    """Routes a founder may pick as candidates, with a short label. Live: the model rows pinned by the bindings file.
    Sample: the bundled placeholders. Routes with a curated billing profile can be measured; the rest are projected
    only. The controller validates every pick again (offered, priced, modality, one per tier)."""
    if sample:
        from app.adapters.sample import SampleDataLayer
        return {m.model_id: f"{m.model_id} ({m.tier}, sample placeholder)" for m in SampleDataLayer().read_models()}
    if not bindings_path:
        return {}
    try:
        ids = json.loads(Path(bindings_path).read_text(encoding="utf-8"))["expected_ids"]["models"]
        routes = json.loads(ROUTE_MAP.read_text(encoding="utf-8"))["routes"]
    except (OSError, ValueError, KeyError):
        return {}
    measured = {r["route_id"]: r.get("tier") for r in routes if r.get("billing_profile")}
    return {mid: f"{mid} ({'can be measured' if mid in measured else 'projected only'})"
            for mid in sorted(ids, key=lambda mid: (mid not in measured, mid)) if not mid.startswith("meterless/")}


def list_examples() -> list[str]:
    return sorted(path.stem for path in EXAMPLES_DIR.glob("example_*.json"))


def load_template(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def new_run_id(prefix: str = "ui") -> str:
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}"


def parse_modality(text) -> list[str]:
    items = [item.strip() for item in str(text or "text").replace(";", ",").split(",") if item.strip()]
    return items or ["text"]


def build_request(template: dict, *, run_id: str, idea: str, user: str, features: list[dict], stages: list[dict],
                  switch_threshold, monthly_ceiling, approved: bool, max_spend, candidate_models=None,
                  subscription_price=None, paying_fraction=None) -> dict:
    """Overlay the form on a template request. Existing features keep their other fields; new rows get defaults."""
    request = copy.deepcopy(template)
    brief = request["brief"]
    known = {item["feature_id"]: item for item in brief["ai_features"]}
    merged = []
    for row in features:
        feature = copy.deepcopy(known.get(row["feature_id"]) or {**FEATURE_DEFAULTS, "field_status": {}})
        feature.update({"feature_id": row["feature_id"], "description": row["description"],
                        "example_input": row["example_input"], "mode": row["mode"],
                        "modality": parse_modality(row["modality"]), "uses_per_user_month": str(row["uses_per_user_month"])})
        feature.setdefault("field_status", {})["uses_per_user_month"] = "assumed"
        merged.append(feature)
    brief.update({"product_concept": idea, "target_user": user, "ai_features": merged,
                  "growth_stages": [{"name": s["name"], "active_users": int(s["active_users"]), "status": "assumed"} for s in stages],
                  "switch_threshold_usd": str(switch_threshold),
                  "monthly_ai_budget_usd": str(monthly_ceiling) if monthly_ceiling not in (None, "", 0, "0") else None})
    usage = brief.setdefault("usage", {})
    for field, value in (("subscription_price_usd", subscription_price), ("paying_fraction", paying_fraction)):
        if value not in (None, ""):
            usage[field] = str(value)
            usage.setdefault("field_status", {})[field] = "assumed"
    request.update({"run_id": run_id, "evaluation_approved": bool(approved), "max_spend_usd": str(max_spend)})
    if candidate_models:
        request["candidate_models"] = list(candidate_models)
    else:
        request.pop("candidate_models", None)
    return request


def validate(request: dict) -> tuple[RunRequest | None, str]:
    try:
        return RunRequest.model_validate(request), ""
    except ValidationError as error:
        return None, "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors()[:8])


def result_path(run_id: str) -> Path:
    if not _RUN_ID.match(run_id):
        raise ValueError("Run IDs use letters, digits, dots, underscores and hyphens")
    return UI_DIR / f"{run_id}.result.json"


def load_result(run_id: str) -> dict | None:
    path = result_path(run_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def read_events(path: Path, start: int = 0) -> tuple[list[dict], int]:
    """Trace events appended since byte offset `start`; only complete lines are read, so a half-written line waits."""
    if not path.exists():
        return [], start
    with path.open("rb") as handle:
        handle.seek(start)
        chunk = handle.read()
    complete = chunk[:chunk.rfind(b"\n") + 1]
    events = []
    for line in complete.decode("utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events, start + len(complete)


def submit_run(request: dict, *, sample: bool, env_extra: dict | None = None, timeout_s: int = 900,
               on_progress=None, poll_s: float = 0.5) -> dict:
    """Run once per run ID. A second call returns the stored result and never invokes `run.py` again.
    While the run is going, `on_progress(events)` receives the trace events written so far (read-only)."""
    run_id = request["run_id"]
    existing = load_result(run_id)
    if existing is not None:
        return {"result": existing, "reused": True, "exit_code": None}
    UI_DIR.mkdir(parents=True, exist_ok=True)
    input_path, output_path = UI_DIR / f"{run_id}.request.json", result_path(run_id)
    input_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
    env = {**os.environ, "RUNS_DB": str(UI_DIR / ("runs-sample.db" if sample else "runs-live.db"))}
    env["SAMPLE_MODE"] = "true" if sample else "false"
    env.update({k: v for k, v in (env_extra or {}).items() if v})
    trace_path = Path(env.get("LOG_DIR") or "logs")
    trace_path = (trace_path if trace_path.is_absolute() else ROOT / trace_path) / f"trace-{run_id}.jsonl"
    log_path = UI_DIR / f"{run_id}.stderr.log"
    # A trace file is appended to; start after anything already there so only this run's steps are shown.
    events, offset, started = [], trace_path.stat().st_size if trace_path.exists() else 0, time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--input", str(input_path),
                                    "--output", str(output_path)], stdout=subprocess.DEVNULL, stderr=log, text=True,
                                   env=env, cwd=ROOT)
        while True:
            finished = process.poll() is not None
            new, offset = read_events(trace_path, offset)
            if new:
                events += new
                if on_progress is not None:
                    on_progress(events)
            if finished:
                break
            if time.monotonic() - started > timeout_s:
                process.kill()
                process.wait()
                break
            time.sleep(poll_s)
    stderr = log_path.read_text(encoding="utf-8", errors="replace")
    result = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else \
        {"code": "OPERATIONAL_ERROR", "message": (stderr or "run.py wrote no output")[-300:], "run_id": run_id}
    return {"result": result, "reused": False, "exit_code": process.returncode}


STEP_LABELS = {"hmem_recall": "Recalling earlier runs (H-MEM)", "retrieve_evidence": "Reading evidence (Zetaris)",
               "zetaris_query": "Zetaris query", "nightshift_models": "Listing Nightshift routes",
               "select_candidates": "Choosing candidate models", "candidates_projected_only": "Marking projected-only models",
               "estimate_tokens": "Estimating tokens", "domain_risk_review": "Planner reviewing risks",
               "nightshift_request": "Model request", "dispatch_receipt": "Spend receipt",
               "run_feature": "Running a feature on a model", "critique": "Critic flagging issues",
               "rubric_check": "Checking outputs", "critic_shares_candidate_route": "Critic shares a candidate route", "repair": "Repair", "calculate_cost": "Calculating costs", "build_panel": "Build panel",
               "hmem_remember_confirmed": "Saving the decision (H-MEM)", "evidence_publication": "Writing evidence back (Zetaris)",
               "state_transition": "Run state", "stop": "Stopped", "complete": "Finished"}


def _bookkeeping(event: dict) -> bool:
    return str(event.get("action", "")).endswith("_attempt") or (
        event.get("action") == "dispatch_receipt" and event.get("status") == "dispatching")


def _detail(event: dict) -> str:
    """Plain detail for a step; a model request shows its tokens and time instead of the adapter's field count."""
    extra = event.get("extra") or {}
    usage = extra.get("usage") if isinstance(extra, dict) else None
    if event.get("action") == "nightshift_request" and event.get("status") == "success" and isinstance(usage, dict):
        return (f"{usage.get('prompt_tokens')} in / {usage.get('completion_tokens')} out tokens"
                + (f", {extra['elapsed_s']} s" if extra.get("elapsed_s") is not None else ""))
    return (event.get("output_summary") or "")[:120]


def progress_rows(events: list[dict], limit: int = 12) -> tuple[dict, list[dict]]:
    """A short summary and the latest steps for the live progress view. Attempt/pending bookkeeping is hidden."""
    requests = [e for e in events if e.get("action") == "nightshift_request" and e.get("status") == "success"]
    shown = [e for e in events if not _bookkeeping(e)]
    current = events[-1] if events else None
    if current is not None and _bookkeeping(current):   # a request or query is in flight
        current = {**current, "action": "nightshift_request" if current["action"] == "dispatch_receipt"
                   else current["action"].removesuffix("_attempt")}
    latest = "Starting" if current is None else STEP_LABELS.get(current["action"], current["action"])
    if current is not None and _bookkeeping(events[-1]):
        latest += " (waiting)"
    summary = {"steps": len(events), "model_requests": len(requests),
               "errors": sum(1 for e in events if e.get("status") == "error"), "latest": latest}
    return summary, [{"#": e.get("seq"), "agent": e.get("agent_name"),
                      "step": STEP_LABELS.get(e.get("action"), e.get("action")), "status": e.get("status"),
                      "model": e.get("model") or e.get("requested_model") or "", "detail": _detail(e)}
                     for e in shown[-limit:]]


def stop_reason(result: dict) -> str:
    """Why a run stopped, read from its trace: the first error or stop event, with the failing step."""
    reasons = []
    for line in trace_text(result).splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("status") in ("error", "needs_input", "denied", "partial", "failed") and event.get("output_summary") and event.get("action") != "complete":
            reasons.append(f"{event.get('agent_name')} {event.get('action')}: {event['output_summary']}")
    return "; ".join(dict.fromkeys(reasons))[:600]


def outbox_hint(result: dict) -> str:
    """A run whose model work finished but whose evidence could not be written back ends partial; say so plainly."""
    pending = result.get("unpublished_evidence_ids") or []
    if not pending:
        return ""
    replay = (f"python scripts/retry_evidence.py --runs-db {UI_DIR / 'runs-live.db'} --run-id {result.get('run_id')} "
              "--bindings <bindings file>")
    if any(ref.get("source_set") == "evaluation_evidence" for ref in result.get("evidence_refs") or []):
        # The publisher accepted other records from this run, so it was reachable; the cause is elsewhere.
        return (f"{len(pending)} evidence record(s) were not written back to Zetaris, although the publisher accepted "
                "other records from this run. See the stop reason and the trace for the failing step. The records are "
                f"kept in the local outbox; replay them with: {replay}")
    return (f"{len(pending)} evidence record(s) were not written back to Zetaris: the evidence publisher was not "
            "running (or SOURCE_INGEST_TOKEN/SOURCE_INGEST_URL were not set in the shell that started Streamlit). "
            "The model runs and costs are complete and the records are kept in the local outbox. Start the publisher "
            f"before the next run (README, Level 3), and replay this run with: {replay}")


def setup_hint(reason: str) -> str:
    if "SetupIncomplete" in reason:
        return ("Live mode is missing setup. Check the price data line in the sidebar (set ZETARIS_BINDINGS_FILE in "
                ".env, or run the README's Level 2 source setup), the Zetaris and Nightshift settings in .env, and that "
                "both services are running.")
    return ""


def trace_text(result: dict) -> str:
    path = result.get("trace_path")
    if not path:
        return ""
    full = Path(path) if Path(path).is_absolute() else ROOT / path
    return full.read_text(encoding="utf-8") if full.exists() else ""
