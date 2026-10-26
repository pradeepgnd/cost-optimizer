"""Build explicit, pinned application records without promoting catalog prices to tariffs."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contracts import ApproachProfile, FounderBrief, SourceRef, EvidenceStatus
from app.source_contracts import RouteMap
from app.source_snapshots import build_bundle, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--route-map", required=True, type=Path)
    parser.add_argument("--discovery", type=Path, help="Retained output from discover_source_routes.py; all mapped routes must be offered.")
    parser.add_argument("--brief", action="append", type=Path, default=[], help="FounderBrief or RunRequest JSON; repeatable.")
    parser.add_argument("--approaches", type=Path, help="Optional JSON list of cited ApproachProfile records.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/localstack/bundles")
    args = parser.parse_args()
    try:
        mapping = RouteMap.model_validate_json(args.route_map.read_text())
        if args.discovery:
            raw = args.discovery.read_bytes()
            discovery = json.loads(raw)
            from app.adapters.validation import validate_model_ids
            routes = set(validate_model_ids(discovery["routes"]))
            if any(route.route_id not in routes for route in mapping.routes):
                raise ValueError("mapped route was not offered by the retained discovery")
            mapping = mapping.model_copy(update={"mapping_status": "discovery_observed", "discovery_source": SourceRef(
                source_set="nightshift_discovery", record_id="offered_routes", version=digest(raw),
                origin_url=discovery["source_url"], verified_at=discovery["checked_at"], status=EvidenceStatus.verified)})
        briefs = []
        for path in args.brief:
            payload = json.loads(path.read_text())
            briefs.append(FounderBrief.model_validate(payload.get("brief", payload)))
        approaches = [ApproachProfile.model_validate(item) for item in json.loads(args.approaches.read_text())] if args.approaches else []
        target, manifest = build_bundle(args.catalog, mapping, args.output_dir, briefs, approaches)
        print(json.dumps({"status": "pass", "bundle_dir": str(target.resolve()), "snapshot_id": manifest["bundle_id"],
                          "counts": manifest["counts"], "execution_tariffs_verified": False}, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "fail", "error_type": type(error).__name__, "message": "Bundle rejected; check IDs, hashes and typed inputs."}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
