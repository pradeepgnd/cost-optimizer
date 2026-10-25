"""Export the bundled setup fixtures into separate S3-ready objects.

  python scripts/prepare_localstack_data.py

This prepares reconstructed/synthetic/unverified fixtures for storage integration
tests. It does not approve a founder brief, verify prices, or create model results.
No real retrospective actuals are read or exported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.contracts import ApproachProfile, DevTaskCase, FounderBrief, ModelProfile  # noqa: E402


def envelope(record_type: str, payload: dict, identity: str) -> dict:
    """A simple table schema with the full validated contract preserved as JSON."""
    source = payload.get("source") or {}
    row = {
        "record_id": payload[identity],
        "record_type": record_type,
        "source_version": source.get("version", payload.get("brief_version", "sample-setup-1")),
        "evidence_status": source.get("status", "reconstructed"),
        "setup_fixture": True,
        "payload_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }
    row[identity] = payload[identity]
    if "split" in payload:
        row["split"] = payload["split"]
    return row


def prepare(output: Path) -> dict:
    source = ROOT / "data/sample"
    briefs = [FounderBrief.model_validate(x).model_dump(mode="json")
              for x in json.loads((source / "founder_briefs.json").read_text(encoding="utf-8"))]
    pricing = json.loads((source / "pricing_snapshots.json").read_text(encoding="utf-8"))
    approaches = [ApproachProfile.model_validate(x).model_dump(mode="json") for x in pricing["approaches"]]
    models = [ModelProfile.model_validate(x).model_dump(mode="json") for x in pricing["models"]]
    tasks = [DevTaskCase.model_validate(x).model_dump(mode="json")
             for x in json.loads((source / "dev_task_cases.json").read_text(encoding="utf-8"))]
    objects = {
        "inputs/founder_briefs.json": [envelope("founder_brief", x, "brief_id") for x in briefs],
        "inputs/pricing_snapshots_approaches.json": [envelope("approach", x, "approach_id") for x in approaches],
        "inputs/pricing_snapshots_models.json": [envelope("model", x, "model_id") for x in models],
        "inputs/dev_task_cases_development.json": [envelope("task", x, "task_id") for x in tasks if x["split"] == "development"],
        "sealed/dev_task_cases_holdout.json": [envelope("task", x, "task_id") for x in tasks if x["split"] == "holdout"],
    }
    manifest = {
        "dataset_version": "localstack-setup-2",
        "storage": "LocalStack S3 emulation",
        "setup_fixtures_only": True,
        "limitations": ["Pricing is unverified sample data.", "Founder brief and task rubric approval remain pending.",
                        "No live model results or real retrospective actuals are included.",
                        "A sealed prefix is organizational separation, not an access-control guarantee."],
        "objects": [],
    }
    for key, rows in objects.items():
        path = output / key
        path.parent.mkdir(parents=True, exist_ok=True)
        # The installed Zetaris reader consumes complete JSON documents; arrays
        # preserve all records where JSON Lines returned only the first object.
        encoded = (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        path.write_bytes(encoded)
        manifest["objects"].append({"key": key, "rows": len(rows), "sha256": hashlib.sha256(encoded).hexdigest(),
                                    "format": "JSON array", "sealed": key.startswith("sealed/")})
    probe = output / "connectivity_check.csv"
    probe.write_text("id,message\n1,localstack_connection_ok\n", encoding="utf-8")
    manifest["objects"].append({"key": probe.name, "rows": 1, "sha256": hashlib.sha256(probe.read_bytes()).hexdigest(),
                                "format": "CSV", "sealed": False})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/localstack")
    args = parser.parse_args()
    manifest = prepare(args.output_dir)
    print(json.dumps({"status": "prepared", "setup_fixtures_only": True, "output_dir": str(args.output_dir),
                      "objects": manifest["objects"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
