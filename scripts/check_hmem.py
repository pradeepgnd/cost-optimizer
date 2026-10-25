"""Verify offline H-MEM using synthetic facts, fresh processes and temporary storage.

Run: python scripts/check_hmem.py --output docs/hmem_engine_check.json
No credentials, founder actuals, services or inference are used.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.adapters.base import SetupIncomplete  # noqa: E402
from app.engines.hmem.bridge import HmemBridge, offline_bridge_available  # noqa: E402


def verify() -> tuple[dict, int]:
    report = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "status": "failed", "engine": "Meterless H-MEM deterministic reference",
              "inference_calls": 0, "storage": "temporary synthetic scopes, deleted after verification"}
    if not offline_bridge_available():
        report["message"] = "Offline self-test failed. Run npm ci --ignore-scripts in app/engines/hmem."
        return report, 2
    try:
        with tempfile.TemporaryDirectory(prefix="cost-optimizer-hmem-check-") as storage:
            bridge = HmemBridge(storage_dir=storage)
            saved = bridge.remember_confirmed("check-A", {
                "kind": "confirmed_constraint", "field": "devops_capacity", "value": "full",
                "source": "synthetic-setup-check"})
            restarted = HmemBridge(storage_dir=storage)
            recalled = restarted.recall("check-A", {"kind": "confirmed_constraint"})
            isolated = restarted.recall("check-B", {"kind": "confirmed_constraint"})
            replacement = restarted.remember_confirmed("check-A", {
                "kind": "confirmed_constraint", "field": "devops_capacity", "value": "none",
                "source": "synthetic-setup-correction"})
            current = HmemBridge(storage_dir=storage).recall("check-A", {"kind": "confirmed_constraint"})
            audit = restarted.audit("check-A")
            checks = {
                "offline_selftest": True,
                "fresh_process_recall": bool(saved["memory_ids"]) and saved["memory_ids"] == recalled["memory_ids"],
                "project_isolation": not isolated["memory_ids"],
                "superseded_constraint_excluded": current["memory_ids"] == replacement["memory_ids"]
                    and set(current["memory_ids"]).isdisjoint(saved["memory_ids"]),
                "provenance": all(record["source"] and record["provenance"] for record in current["records"]),
                "audit": {"create", "read", "update"} <= {entry["action"] for entry in audit["entries"]},
            }
            report.update(engine_revision=bridge.revision, checks=checks,
                          memory_ids=current["memory_ids"], audit_refs=audit["audit_refs"])
            report["status"] = "passed" if all(checks.values()) else "failed"
            return report, 0 if report["status"] == "passed" else 3
    except SetupIncomplete as error:
        report["message"] = str(error)
        return report, 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report, code = verify()
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
