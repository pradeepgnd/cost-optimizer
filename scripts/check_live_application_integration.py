"""Check live application integration without paid inference or sealed reads.

Optional --write-evidence ingests two synthetic setup records and verifies exact Zetaris readback.
This is integration evidence only; approved data/rates are required for an evaluated live run.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.adapters.live import NightshiftInference, ZetarisDataLayer
from app.contracts import RunRequest, RunState
from app.controller import Checkpoints, Controller
from app.engines.hmem.bridge import HmemBridge
from app.trace import Trace


def verify(brief_id="brief-avl-prebuild", write_evidence=False):
    report = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "status": "failed", "scope": "local integration plumbing; not a founder benchmark",
              "inference_calls": 0, "sealed_content_queried": False}
    layer = None
    try:
        run_id = "live-integration-" + uuid.uuid4().hex[:12]
        trace = Trace(run_id, "live", str(ROOT / "logs"), echo=False)
        layer = ZetarisDataLayer(trace)
        inference = NightshiftInference(trace)
        brief, ref = layer.read_brief(brief_id)
        approaches, models = layer.read_approaches(), layer.read_models()
        dev = layer.read_task_cases("development")
        discovered = inference.list_models()
        import os
        configured = [mid.strip() for mid in os.getenv("METERLESS_CANDIDATE_MODELS", "").split(",") if mid.strip()]
        critic = os.getenv("METERLESS_CRITIC_MODEL", "")
        with tempfile.TemporaryDirectory(prefix="cost-optimizer-live-integration-") as temporary:
            controller = Controller(layer, inference, HmemBridge(storage_dir=Path(temporary) / "memory"),
                trace, "live", Checkpoints(str(Path(temporary) / "runs.db")), critic_model=critic, candidate_models=configured)
            def forbidden():
                raise AssertionError("Sealed adapter dispatched before freeze")
            denied = all(controller._read(key, forbidden).status == "denied_sealed"
                         for key in ("dev_task_cases:holdout", "retrospective_actuals"))
            request = RunRequest(run_id=run_id, project_id=brief.project_id or "proj-" + brief_id,
                                 brief=brief, evaluation_approved=False, max_spend_usd=0, sample_mode=False)
            pack = controller.run(request)
            checks = {"registered_brief": ref.record_id == brief_id,
                      "registered_approaches": bool(approaches), "registered_models": bool(models),
                      "development_cases": len(dev) == 3 and all(t.split == "development" for t in dev),
                      "configured_routes_discovered": len(configured) == 2 and bool(critic) and set(configured + [critic]) <= set(discovered),
                      "sealed_guard_before_dispatch": denied,
                      "unapproved_evaluation_stops": pack.status == RunState.needs_input and pack.spend_usd == 0 and not pack.development_results}
            report["unapproved_run_limitations"] = pack.limitations
            report["project_evidence_ids"] = sorted({ref.record_id for ref in pack.evidence_refs})
            if write_evidence:
                proof = layer.write_evidence({"id": run_id + "/setup", "run_id": run_id,
                    "project_id": request.project_id, "kind": "synthetic_live_integration_check", "inference_calls": 0})
                checks["evidence_ingestion_and_zetaris_readback"] = proof.source_set == "evaluation_evidence"
                report["writeback_ref"] = proof.model_dump(mode="json")
                appended = layer.write_evidence({"id": run_id + "/append", "run_id": run_id,
                    "project_id": request.project_id, "kind": "synthetic_live_integration_append", "inference_calls": 0})
                checks["evidence_append_and_readback"] = appended.source_set == "evaluation_evidence"
                report["append_ref"] = appended.model_dump(mode="json")
            controller.ckpt.conn.close()
        report.update(checks=checks, status="passed" if all(checks.values()) else "failed",
                      fixture_records=sorted(layer.fixture_records), trace_path=str(trace.path),
                      limitations=["No paid candidate/critic workflow was exercised.",
                                   "Approved founder/task records and dated prices for the configured routes are still required.",
                                   "No server-side sealed-source permission claim is made by this check."])
        return report, 0 if report["status"] == "passed" else 3
    except Exception as error:
        report.update(error_type=type(error).__name__, message="Integration check did not finish; check service availability, registered schema and evidence writer setup.")
        return report, 3
    finally:
        if layer:
            layer.client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief-id", default="brief-avl-prebuild")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    report, code = verify(args.brief_id, args.write_evidence)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
