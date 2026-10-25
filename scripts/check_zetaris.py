"""Check Zetaris's app API-key connection without requiring Nightshift or H-MEM.

Run from any directory with the project's Python environment:
  python scripts/check_zetaris.py
  python scripts/check_zetaris.py --output docs/zetaris_connection_check.json

Reads existing private configuration; never creates or edits .env. Only SELECT 1
is executed. Reports exclude credentials, HTTP response bodies, and auth tokens.
Exit codes: 0 verified; 2 missing configuration; 3 connection/query failure.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.adapters.base import SetupIncomplete  # noqa: E402
from app.adapters.live import ZetarisDataLayer  # noqa: E402
from app.trace import Trace  # noqa: E402


def verify_connection() -> tuple[dict, int]:
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "failed",
        "authentication": "configured_bearer_credential",
        "sql": "SELECT 1 AS one",
    }
    try:
        layer = ZetarisDataLayer()
    except SetupIncomplete:
        report["code"] = "SETUP_INCOMPLETE"
        report["message"] = "Privately configure ZETARIS_REST_URL, ZETARIS_ORG_ID, and ZETARIS_API_KEY."
        return report, 2

    trace = Trace("zetaris-check-" + uuid.uuid4().hex[:12], "live", log_dir=str(ROOT / "logs"))
    layer.trace = trace
    report["trace_path"] = str(trace.path)
    try:
        result = layer.select_one()
        rows = result.get("data") if isinstance(result, dict) else None
        if not (isinstance(rows, list) and len(rows) == 1
                and isinstance(rows[0], list) and len(rows[0]) == 1
                and str(rows[0][0]) == "1"):
            report["code"] = "UNEXPECTED_SQL_RESULT"
            report["message"] = "Zetaris responded, but SELECT 1 did not return exactly one row containing 1."
            return report, 3
        report.update(status="passed", code="SQL_VERIFIED", row_count=1, value=1)
        return report, 0
    except httpx.HTTPStatusError as error:
        report["code"] = "HTTP_ERROR"
        report["http_status"] = error.response.status_code
        report["message"] = "Zetaris rejected the SQL request; check the credential, organization, and API address."
        return report, 3
    except httpx.RequestError:
        report["code"] = "CONNECTION_ERROR"
        report["message"] = "Cannot reach Zetaris; check its services and configured REST address."
        return report, 3
    except ValueError:
        report["code"] = "INVALID_JSON_RESPONSE"
        report["message"] = "Zetaris did not return a JSON SQL response."
        return report, 3
    finally:
        layer.client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional sanitized JSON report path")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    report, exit_code = verify_connection()
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
