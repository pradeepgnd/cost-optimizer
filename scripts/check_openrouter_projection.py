"""Preview Zetaris-sourced OpenRouter serving costs without authorizing any model completion."""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.adapters.base import SetupIncomplete
from app.adapters.live_nightshift import NightshiftInference
from app.adapters.live_zetaris import ZetarisDataLayer
from app.adapters.sample import SampleMemory
from app.contracts import RunRequest
from app.controller import Checkpoints, Controller
from app.trace import Trace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="A RunRequest JSON; paid evaluation is always disabled.")
    parser.add_argument("--bindings", type=Path, required=True, help="Registered pinned Zetaris bindings.")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for pack, trace and report.")
    parser.add_argument("--critic", default="nvidia/nemotron-3-ultra-550b-a55b")
    parser.add_argument("--no-dotenv", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("use a new output directory; prior reports are retained")
    if not args.no_dotenv:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    try:
        req = RunRequest.model_validate_json(args.input.read_text())
        req = RunRequest.model_validate(req.model_copy(update={"run_id": f"openrouter-preview-{uuid4().hex[:16]}",
            "sample_mode": False, "evaluation_approved": False, "max_spend_usd": Decimal("0")}).model_dump())
        os.environ["ZETARIS_BINDINGS_FILE"] = str(args.bindings.resolve())
        args.output_dir.mkdir(parents=True)
        trace = Trace(req.run_id, "live", log_dir=str(args.output_dir), echo=False)
        controller = Controller(ZetarisDataLayer(trace), NightshiftInference(trace), SampleMemory(bridge_available=False),
            trace, "live", Checkpoints(str(args.output_dir / "runs.db")), critic_model=args.critic,
            planner_model=os.getenv("METERLESS_MODEL", ""), open_model=os.getenv("METERLESS_OPEN_MODEL", ""))
        pack = controller.run(req)
        if pack.dispatch_count != 0 or pack.spend_usd != 0:
            raise RuntimeError("preview unexpectedly dispatched or spent")
        pack_path = args.output_dir / "pack.json"
        pack_path.write_text(pack.model_dump_json(indent=2) + "\n")
        scenario_rows = [row for table in pack.openrouter_projection_tables for row in table.rows]
        report = {"status": "pass" if scenario_rows else "incomplete", "run_id": req.run_id,
                  "model_completions": pack.dispatch_count, "actual_nightshift_billing_verified": False,
                  "openrouter_scope": "hypothetical listed-token serving scenario",
                  "feature_count": len(pack.openrouter_projection_tables), "scenario_rows": len(scenario_rows),
                  "scenario_model_ids": sorted(set(row.model_id for row in scenario_rows)),
                  "catalog_source_ids": sorted(set(source.record_id for table in pack.openrouter_projection_tables
                                                   for source in table.sources)),
                  "known_monthly_rows": sum(row.monthly_with_levers_usd is not None for row in scenario_rows),
                  "actual_route_monthly_rows_known": sum(row.monthly_with_levers_usd is not None
                      for table in pack.stage_tables for row in table.rows),
                  "pack": str(pack_path), "trace": str(trace.path)}
        (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 0 if scenario_rows else 1
    except (OSError, ValueError, SetupIncomplete, RuntimeError, KeyError) as error:
        print(json.dumps({"status": "fail", "error_type": type(error).__name__,
                          "model_completions": 0}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
