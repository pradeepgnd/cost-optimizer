"""Create one synthetic, bounded M08 live request from example 3; send nothing."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.contracts import RunRequest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate-tiers", nargs="+", choices=("frontier", "mid_tier", "open_source"),
                        help="Validation-only subset; choose two tiers for an incremental comparison.")
    parser.add_argument("--max-spend-usd", default="0.50", help="Spend ceiling for the prepared request; use 0 for a no-spend dry run.")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a fresh path and run ID")
    payload = json.loads((ROOT / "input_examples" / "example_3.json").read_text(encoding="utf-8"))
    payload.update(run_id=f"m08-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}",
                   sample_mode=False, sampling_profile="validation", max_spend_usd=args.max_spend_usd,
                   evaluation_approved=True)
    if args.candidate_tiers is not None:
        payload["candidate_tiers"] = args.candidate_tiers
    request = RunRequest.model_validate(payload)
    features = request.brief.ai_features
    if (len(features) != 2 or any("text" not in f.modality or not f.rubric_checks for f in features)):
        raise ValueError("M08 profile requires two text features with pre-supplied rubric checks")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(request.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {request.run_id}: two text features, {', '.join(request.candidate_tiers or ('frontier', 'mid_tier', 'open_source'))} candidates, validation sampling, ${request.max_spend_usd} ceiling. No requests sent. {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
