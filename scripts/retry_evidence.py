"""Replay the local evidence outbox through the configured writer/readback, never model generation."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.adapters.live_zetaris import ZetarisDataLayer, record_id
from app.dispatch import Checkpoints
from app.source_contracts import SourceBindings
from app.source_snapshots import canonical, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-db", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bindings", type=Path)
    parser.add_argument("--stage-test-fixture", action="store_true", help="Create a new test-only outbox DB with one labeled fixture; no setup or network.")
    parser.add_argument("--no-dotenv", action="store_true")
    args = parser.parse_args()
    if args.stage_test_fixture:
        if args.runs_db.exists():
            parser.error("fixture staging requires a new database path; real/existing runs are preserved")
        run_id = record_id(args.run_id)
        if "/" in run_id:
            parser.error("run ID cannot contain a slash")
        args.runs_db.parent.mkdir(parents=True, exist_ok=True)
        store = Checkpoints(str(args.runs_db))
        store.claim(run_id)
        record = {"id": run_id + "/outbox-fixture", "run_id": run_id, "kind": "integration_test_fixture",
                  "payload": {"message": "manual outbox recovery fixture; no inference", "fixture": True}}
        store.stage_evidence(run_id, record)
        store.conn.close()
        print(json.dumps({"status": "pending", "record_id": record["id"], "model_completions": 0}))
        return 0
    if not args.bindings:
        parser.error("--bindings is required for publication retry")
    if not args.runs_db.exists():
        parser.error("existing run database required; no empty replacement database is created")
    if not args.no_dotenv:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    store = Checkpoints(str(args.runs_db))
    layer = ZetarisDataLayer(bindings=SourceBindings.model_validate_json(args.bindings.read_text()))
    published, pending = [], []
    for record in store.pending_evidence(args.run_id):
        try:
            written = layer.write_evidence(record)
            payload, source = layer.read_evidence(record["id"])
            if canonical(payload) != canonical(record) or source.version != written.version or source.content_sha256 != digest(canonical(record)):
                raise ValueError("readback mismatch")
            store.evidence_status(record["id"], source=source)
            published.append(record["id"])
        except Exception as error:
            store.evidence_status(record["id"], error=type(error).__name__)
            pending.append(record["id"])
    layer.client.close()
    store.conn.close()
    print(json.dumps({"published": published, "pending": pending, "model_completions": 0,
                      "pack_refinalized": False, "note": "Existing packs are not silently rewritten; publication receipts are retained in the outbox."}, indent=2))
    return 1 if pending else 0


if __name__ == "__main__":
    sys.exit(main())
