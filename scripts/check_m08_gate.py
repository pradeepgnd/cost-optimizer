"""Read-only M08 preflight. No completion is sent and no dispatch is reserved.

Usage: .venv/bin/python scripts/check_m08_gate.py \
  --bindings data/localstack/openrouter/bindings-lightning-mid-gemma-open.json \
  --output /private/tmp/m08-gate.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from app.adapters.live_nightshift import NightshiftInference  # noqa: E402
from app.adapters.live_zetaris import ZetarisDataLayer  # noqa: E402
from app.contracts import RunRequest  # noqa: E402
from app.dispatch import StopRun, request_bound  # noqa: E402

SELECTED = ROOT / "data" / "source_examples" / "routes.selected.json"


def check(bindings: Path, bundle: Path | None = None, request: Path | None = None) -> dict:
    run_request = RunRequest.model_validate_json(request.read_text(encoding="utf-8")) if request else None
    candidate_tiers = tuple(run_request.candidate_tiers or ("frontier", "mid_tier", "open_source")) if run_request else (
        "frontier", "mid_tier", "open_source")
    validation_subset = set(candidate_tiers) != {"frontier", "mid_tier", "open_source"}
    load_dotenv(ROOT / ".env")
    os.environ["ZETARIS_BINDINGS_FILE"] = str(bindings.resolve())
    binding = json.loads(bindings.read_text(encoding="utf-8"))
    manifest_path = (bundle / "manifest.json" if bundle else
                     bindings.parent / "bundles" / binding["snapshot_id"] / "manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("bundle_id") != binding["snapshot_id"]:
            raise ValueError("bundle manifest does not match registered bindings snapshot")
        selected = manifest["route_map"]
    else:
        selected = json.loads(SELECTED.read_text(encoding="utf-8"))
    current = json.loads(SELECTED.read_text(encoding="utf-8"))
    selected_candidates = {(entry["tier"], entry["route_id"], entry["catalog_id"], bool(entry.get("required")))
                           for entry in selected["routes"] if entry.get("tier")}
    current_candidates = {(entry["tier"], entry["route_id"], entry["catalog_id"], bool(entry.get("required")))
                          for entry in current["routes"] if entry.get("tier")}
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "kind": "read_only_m08_gate",
              "bindings": str(bindings), "mapping_status": selected["mapping_status"],
              "route_map_manifest": str(manifest_path) if manifest_path.exists() else None,
              "selection_matches_current": selected_candidates == current_candidates,
              "run_id": run_request.run_id if run_request else None,
              "candidate_tiers": list(candidate_tiers), "validation_subset": validation_subset,
              "completion_sent": False, "routes": []}
    try:
        models = {model.model_id: model for model in ZetarisDataLayer().read_models()}
        offered = set(NightshiftInference().list_models())
    except Exception as error:
        result.update(status="incomplete", setup_error=type(error).__name__)
        return result
    result["model_rows"] = len(models)
    result["discovered_route_count"] = len(offered)
    critic = os.getenv("METERLESS_CRITIC_MODEL", "")
    planner = os.getenv("METERLESS_MODEL", "")
    candidate_routes = {entry["route_id"] for entry in selected["routes"] if entry.get("tier") in candidate_tiers}
    selected_routes = {entry["route_id"] for entry in selected["routes"]}
    required_routes = candidate_routes | {critic, planner}
    for entry in selected["routes"]:
        route = entry["route_id"]
        model = models.get(route)
        row = {"role": entry.get("tier", "critic"), "route_id": route,
               "catalog_id": entry["catalog_id"], "discovered": route in offered,
               "registered": model is not None, "required_for_run": route in required_routes}
        if model is not None:
            row["model_source_status"] = model.source.status.value
            row["dispatch_policy_present"] = model.dispatch_policy is not None
            try:
                _, reserved, _, _, _ = request_bound(model, "M08 tiny preflight", "OK?", 8)
                row["tiny_request_bound_usd"] = str(reserved)
                row["billing_gate"] = "pass"
            except StopRun as error:
                row["billing_gate"] = "blocked"
                row["billing_blocker"] = error.reason
        result["routes"].append(row)
    result["critic_route_selected_and_registered"] = critic in selected_routes and critic in models
    result["critic_shares_candidate_route"] = critic in candidate_routes
    result["critic_distinct_from_candidates"] = bool(critic) and critic not in candidate_routes
    result["planner_route_selected_and_registered"] = planner in selected_routes and planner in models
    ready = (all(
        row["discovered"] and row["registered"] and row.get("billing_gate") == "pass"
        for row in result["routes"] if row["required_for_run"]) and required_routes <= selected_routes
        and result["critic_route_selected_and_registered"]
        and result["planner_route_selected_and_registered"] and selected["mapping_status"] != "planned"
        and result["selection_matches_current"])
    result["status"] = ("ready_for_bounded_validation" if validation_subset else "ready_for_bounded_dispatch") if ready else "incomplete"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, help="Bundle directory if it is not next to the bindings file")
    parser.add_argument("--request", type=Path, help="RunRequest JSON; gate only its validation candidate subset, plus Planner/Critic.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a fresh path")
    report = check(args.bindings, args.bundle, args.request)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M08 gate: {report['status']}; {len(report['routes'])} selected routes; no completions sent. Report: {args.output}")
    return 0 if report["status"].startswith("ready_for_bounded_") else 1


if __name__ == "__main__":
    sys.exit(main())
