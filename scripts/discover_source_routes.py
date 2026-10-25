"""Retain free Nightshift route discovery for source mapping. Never calls a completion."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.adapters.live_nightshift import NightshiftInference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-dotenv", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("use a new output path; retained discovery is not overwritten")
    if not args.no_dotenv:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    try:
        adapter = NightshiftInference()
        routes = adapter.list_models()
        result = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source_url": adapter.base + "/models",
                  "routes": routes, "completion_requests": 0}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": "pass", "route_count": len(routes), "output": str(args.output), "completion_requests": 0}))
        return 0
    except Exception as error:
        print(json.dumps({"status": "fail", "error_type": type(error).__name__, "completion_requests": 0}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
