"""Collect an immutable OpenRouter reference snapshot; performs no inference."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.source_snapshots import collect_snapshot, validate_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/localstack/catalog")
    parser.add_argument("--from-file", type=Path, help="Offline import; recorded as file_import, never API verification.")
    parser.add_argument("--validate", type=Path, help="Validate an existing snapshot without network access.")
    parser.add_argument("--search", help="List up to 100 matching catalog IDs/names from the retained snapshot.")
    args = parser.parse_args()
    try:
        if args.validate:
            target, manifest = args.validate, validate_snapshot(args.validate)[0]
        else:
            target, manifest = collect_snapshot(args.output_dir, from_file=args.from_file)
        report = {"status": "pass", "snapshot_dir": str(target.resolve()), "snapshot_id": manifest.snapshot_id,
                  "records": manifest.record_count, "rejected_records": manifest.rejected_record_count,
                  "upstream_records": manifest.upstream_record_count, "acquisition": manifest.acquisition, "purpose": manifest.purpose}
        if args.search:
            records = validate_snapshot(target)[1]
            matching = [record.model_dump(mode="json") for record in records if args.search.lower() in (record.catalog_id + " " + record.name).lower()]
            report.update(matches=matching[:100], matching_count=len(matching))
        print(json.dumps(report, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "fail", "error_type": type(error).__name__,
                          "message": str(error)[:240] if type(error) is ValueError else
                          "Snapshot was not accepted; existing snapshots are preserved."}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
