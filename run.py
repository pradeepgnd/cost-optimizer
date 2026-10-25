"""Programmatic entry point. JSON in, JSON out, JSONL trace on stderr/logs, one final_result line on stdout.

  python run.py --input input_examples/example_1.json --output result.json
  SAMPLE_MODE=true python run.py --input input_examples/example_1.json --output result.json

Exit codes: 0 valid result (complete, partial or needs_input); 2 invalid input; 3 setup incomplete; 4 operational error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from app.adapters.base import SetupIncomplete
from app.contracts import RunError, RunRequest
from app.controller import Checkpoints, Controller, DuplicateRun
from app.trace import Trace


def is_sample(req: RunRequest) -> bool:
    if req.sample_mode is not None:
        return req.sample_mode
    return os.getenv("SAMPLE_MODE", "false").strip().lower() in {"1", "true", "yes"}


def build_controller(req: RunRequest, trace: Trace) -> Controller:
    if is_sample(req):
        # Offline adapters are constructed before any network client or secret validation.
        from app.adapters.sample import RulePolicyInference, SampleDataLayer, SampleMemory
        from app.engines.hmem.bridge import offline_bridge_available
        return Controller(SampleDataLayer(), RulePolicyInference(), SampleMemory(bridge_available=offline_bridge_available()),
                          trace, "sample", Checkpoints(os.getenv("RUNS_DB", "runs-sample.db")))
    from app.adapters.live_nightshift import NightshiftInference
    from app.adapters.live_zetaris import ZetarisDataLayer
    from app.engines.hmem.bridge import HmemBridge
    # Candidates are the frontier, mid-tier and open-source models in the pricing snapshots (model_id == route).
    return Controller(ZetarisDataLayer(trace), NightshiftInference(trace), HmemBridge(trace), trace, "live",
                      Checkpoints(os.getenv("RUNS_DB", "runs.db")),
                      critic_model=os.getenv("METERLESS_CRITIC_MODEL", ""), planner_model=os.getenv("METERLESS_MODEL", ""),
                      open_model=os.getenv("METERLESS_OPEN_MODEL", ""))


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        req = RunRequest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as e:
        err = RunError(run_id=str(payload.get("run_id", "unknown")) if isinstance(locals().get("payload"), dict) else "unknown",
                       code="INVALID_INPUT", message=str(e)[:500], recoverable=False)
        print(err.model_dump_json(), file=sys.stderr)
        Path(args.output).write_text(err.model_dump_json(indent=2), encoding="utf-8")
        return 2

    mode = "sample" if is_sample(req) else "live"
    trace = Trace(req.run_id, mode)
    trace.event("Controller", "start", output_summary=f"mode={mode} brief={req.brief.brief_id} approved={req.evaluation_approved}")
    try:
        ctl = build_controller(req, trace)
        pack = ctl.run(req)
    except DuplicateRun as e:
        err = RunError(run_id=req.run_id, code="DUPLICATE_RUN", message=str(e), recoverable=False, trace_path=str(trace.path))
        trace.event("Controller", "refused_duplicate", status="denied", output_summary=str(e))
        Path(args.output).write_text(err.model_dump_json(indent=2), encoding="utf-8")
        trace.final(err.model_dump(mode="json"))
        return 4
    except SetupIncomplete as e:
        err = RunError(run_id=req.run_id, code="SETUP_INCOMPLETE", message=str(e), recoverable=True, trace_path=str(trace.path))
        trace.event("Controller", "error", status="error", output_summary=str(e))
        Path(args.output).write_text(err.model_dump_json(indent=2), encoding="utf-8")
        trace.final(err.model_dump(mode="json"))
        return 3
    except Exception as e:  # operational failure: structured, no raw stack trace to the user
        err = RunError(run_id=req.run_id, code="OPERATIONAL_ERROR", message=f"{type(e).__name__}: {str(e)[:300]}",
                       recoverable=False, trace_path=str(trace.path))
        trace.event("Controller", "error", status="error", output_summary=err.message)
        Path(args.output).write_text(err.model_dump_json(indent=2), encoding="utf-8")
        trace.final(err.model_dump(mode="json"))
        return 4

    Path(args.output).write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    trace.event("Controller", "complete", status=pack.status.value, output_summary=f"spend={pack.spend_usd} gaps={len(pack.evidence_gaps)}")
    trace.final({"status": pack.status.value, "output": args.output, "trace": str(trace.path), "execution_mode": mode})
    return 0


if __name__ == "__main__":
    sys.exit(main())
