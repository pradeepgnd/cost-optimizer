"""Check all three sample CLI inputs without credentials or Python network access.

Run with the project virtual environment:
    python scripts/check_sample_examples.py
    python scripts/check_sample_examples.py --output-dir /path/to/new/artifact-directory

Artifacts are retained in a fresh temporary directory by default. Existing inputs,
example outputs and run databases are never modified. Exit 0 means the offline
checks passed, not that sponsor integrations are ready.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]

# Use the real CLI while preventing dotenv from loading private configuration.
# Node subprocesses also receive the H-MEM network guard below.
OFFLINE_BOOTSTRAP = """
import pathlib, runpy, socket, sys
import dotenv
def denied(*args, **kwargs):
    raise RuntimeError('Network access forbidden by the sample checker')
socket.socket.connect = denied
socket.socket.connect_ex = denied
socket.socket.sendto = denied
socket.create_connection = denied
socket.getaddrinfo = denied
dotenv.load_dotenv = lambda *args, **kwargs: False
entry = sys.argv.pop(1)
sys.argv[0] = entry
sys.path.insert(0, str(pathlib.Path(entry).parent))
runpy.run_path(entry, run_name='__main__')
"""


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
        timeout=10, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def sample_environment(case_dir: Path) -> dict[str, str]:
    # Preserve only operating-system/toolchain settings, never provider settings.
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(
        SAMPLE_MODE="true", LOG_DIR=str(case_dir / "logs"),
        RUNS_DB=str(case_dir / "runs.db"), HMEM_STORAGE_DIR=str(case_dir / "memory"),
        NODE_OPTIONS=f'--require="{(ROOT / "scripts" / "hmem_network_guard.cjs").as_posix()}"',
        PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def inspect_pack(pack: dict, events: list[dict], payload: dict) -> dict[str, bool]:
    runs = pack.get("feature_runs", [])
    tables = pack.get("stage_tables", [])
    rows = [row for table in tables for row in table["rows"]]
    expected_features = {feature["feature_id"] for feature in payload["brief"]["ai_features"]}
    selected = [entry for entry in pack.get("candidate_shortlist", []) if entry["selected"]]
    expected_pairs = {(fid, model["model_id"]) for fid in expected_features for model in selected}
    return {
        "sample_mode": pack.get("execution_mode") == "sample",
        "complete": pack.get("status") == "complete",
        "sponsor_readiness_not_verified": pack.get("readiness", {}).get("scope") == "sponsor_integration"
                                         and pack.get("readiness", {}).get("status") == "not_verified",
        "offline_label": any(note.startswith("SAMPLE/OFFLINE") for note in pack.get("limitations", [])),
        "zero_spend": Decimal(str(pack.get("spend_usd", "NaN"))) == 0,
        "zero_dispatches_or_reservations": pack.get("dispatch_count") == 0
                                         and Decimal(str(pack.get("reserved_spend_usd", "NaN"))) == 0
                                         and not pack.get("operations"),
        "three_candidate_tiers": {entry["tier"] for entry in selected} == {"frontier", "mid_tier", "open_source"} and len(selected) == 3,
        "feature_tables": {table["feature_id"] for table in tables} == expected_features and len(tables) == len(expected_features),
        "feature_candidate_pairs": {(run["feature_id"], run["model_id"]) for run in runs} == expected_pairs and len(runs) == len(expected_pairs),
        "estimated_rows": bool(rows) and all(row["token_basis"] == "estimated" for row in rows),
        "no_generations": bool(runs) and all(not run["executed"] and not run["samples"] and run["measured_mean"] is None for run in runs),
        "no_quality_results": bool(runs) and all(run["rubric"] is None for run in runs),
        "no_qualified_switches": all(not table["switch_points"] for table in tables),
        "stack_requires_live": bool(pack.get("model_stack")) and all(entry["status"] == "requires_live_run" for entry in pack["model_stack"]),
        "no_repair": not pack.get("revisions"),
        "trace_is_sample": bool(events) and all(event["execution_mode"] == "sample" and event.get("model") is None for event in events),
        "no_inference_requests": bool(events) and all(event["action"] != "nightshift_request" and event.get("execution_kind") != "live_inference" for event in events),
    }


def check_example(number: int, output_dir: Path) -> dict:
    source = ROOT / "input_examples" / f"example_{number}.json"
    original_hash = fingerprint(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload.update(sample_mode=True, run_id=f"m00-example-{number}-{uuid.uuid4().hex[:12]}")
    case_dir = output_dir / f"example_{number}"
    case_dir.mkdir()
    request, output = case_dir / "input.json", case_dir / "pack.json"
    request.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", OFFLINE_BOOTSTRAP, str(ROOT / "run.py"),
         "--input", str(request), "--output", str(output)],
        cwd=ROOT, env=sample_environment(case_dir), capture_output=True,
        text=True, encoding="utf-8", timeout=60, check=False,
    )
    (case_dir / "cli-stdout.txt").write_text(result.stdout, encoding="utf-8")
    (case_dir / "cli-stderr.txt").write_text(result.stderr, encoding="utf-8")
    checks = {"cli_exit_zero": result.returncode == 0, "source_unchanged": fingerprint(source) == original_hash}
    trace_path = case_dir / "logs" / f"trace-{payload['run_id']}.jsonl"
    pack = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    if result.returncode == 0 and trace_path.exists():
        events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        checks.update(inspect_pack(pack, events, payload))
    else:
        checks["pack_and_trace_available"] = False
    return {
        "example": number, "status": "pass" if all(checks.values()) else "fail",
        "source_sha256": original_hash, "run_id": payload["run_id"],
        "feature_tables": len(pack.get("stage_tables", [])),
        "feature_runs": len(pack.get("feature_runs", [])), "checks": checks,
        "request": str(request.relative_to(output_dir)), "pack": str(output.relative_to(output_dir)),
        "trace": str(trace_path.relative_to(output_dir)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="New directory; an existing directory is refused.")
    args = parser.parse_args()
    if args.output_dir:
        output_dir = args.output_dir.resolve()
        if output_dir.exists():
            parser.error("--output-dir must not already exist; existing artifacts are preserved")
        output_dir.mkdir(parents=True)
    else:
        output_dir = Path(tempfile.mkdtemp(prefix="cost-optimizer-sample-check-")).resolve()
    results = []
    for number in (1, 2, 3):
        try:
            results.append(check_example(number, output_dir))
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            results.append({"example": number, "status": "fail", "error_type": type(error).__name__})
    manifest = {
        "milestone": "M00", "status": "pass" if all(item["status"] == "pass" for item in results) else "fail",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "revision": git_revision(), "python": platform.python_version(),
        "working_tree_source_hashes": {
            str(path.relative_to(ROOT)): fingerprint(path)
            for path in [ROOT / "run.py", Path(__file__).resolve(),
                         *sorted((ROOT / "app").rglob("*.py")),
                         ROOT / "data/sample/pricing_snapshots.json", ROOT / "data/sample/manifest.json"]
        },
        "python_network_guard": True, "dotenv_loading": False,
        "sponsor_readiness": "not_verified", "results": results,
        "limitations": ["Offline regression evidence only; prices are sample placeholders.",
                         "Python sockets are blocked. Node engine network behavior requires the separate M07 check.",
                         "A passing baseline does not close known product or integration gaps."],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for item in results:
        print(f"Example {item['example']}: {item['status'].upper()} ({item.get('feature_tables', 0)} feature tables)")
    print(f"Manifest: {manifest_path}")
    return 0 if manifest["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
