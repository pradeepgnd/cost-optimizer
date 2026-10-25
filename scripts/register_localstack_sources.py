"""Register LocalStack setup fixtures in Zetaris and verify ordinary records.

  python scripts/register_localstack_sources.py             # show SQL plan
  python scripts/register_localstack_sources.py --apply     # register and verify

Requires an activated LocalStack instance with the prepared objects uploaded.
Only dedicated oah_localstack namespaces are used. Holdout content is registered
under a separate namespace and never queried by this script. There are no real
actuals, benchmark executions, or changes to existing NY_TAXI/TPCDS sources.
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

SOURCE = "oah_localstack"
SEALED_SOURCE = "oah_localstack_sealed"
ENDPOINT = "http://cost-optimizer-localstack:4566"
BUCKET = "cost-optimizer-data"
PREFIX = "cost-optimizer/v1"
TABLES = [
    (SOURCE, "connectivity_check", "connectivity_check.csv", "CSV"),
    (SOURCE, "founder_briefs", "inputs/founder_briefs.json", "JSON"),
    (SOURCE, "pricing_snapshots_approaches", "inputs/pricing_snapshots_approaches.json", "JSON"),
    (SOURCE, "pricing_snapshots_models", "inputs/pricing_snapshots_models.json", "JSON"),
    (SOURCE, "dev_task_cases", "inputs/dev_task_cases_development.json", "JSON"),
    (SEALED_SOURCE, "dev_task_cases_holdout", "sealed/dev_task_cases_holdout.json", "JSON"),
]


def table_sql(source: str, table: str, key: str, format_name: str) -> str:
    if (source, table, key, format_name) not in TABLES:
        raise ValueError("Only the fixed LocalStack setup tables may be registered.")
    json_options = 'multiLine "true", ' if format_name == "JSON" else ""
    return (f'CREATE LIGHTNING FILESTORE TABLE {table} FROM {source} FORMAT {format_name} OPTIONS ('
            f'PATH "s3a://{BUCKET}/{PREFIX}/{key}", s3Endpoint "{ENDPOINT}", '
            f'inferSchema "true", header "true", {json_options}useS3PathStyleAccess "true", '
            'AWSACCESSKEYID "test", AWSSECRETACCESSKEY "test")')


def rows(result: dict) -> list[dict]:
    if not isinstance(result, dict) or not isinstance(result.get("headers"), list) or not isinstance(result.get("data"), list):
        raise ValueError("Zetaris did not return a SQL table response.")
    return [dict(zip(result["headers"], row)) for row in result["data"]]


def update_json_reader(layer: ZetarisDataLayer, source: str, table: str) -> None:
    """Use the installed metadata API; keep stored source settings and S3 files."""
    if not any(s == source and t == table and fmt == "JSON" for s, t, _, fmt in TABLES):
        raise ValueError("Only the dedicated JSON fixture readers may be updated.")
    endpoint = f"{layer.base}/lightning-database/databases/{source}/file-store-tables/{table}"
    headers = {"Authorization": f"Bearer {layer.key}", "X-Org-ID": layer.org,
               "X-Request-ID": str(uuid.uuid4())}
    response = layer.client.get(endpoint, headers=headers)
    response.raise_for_status()
    metadata = response.json()
    if not isinstance(metadata, dict) or metadata.get("format", "").lower() != "json":
        raise ValueError("Unexpected JSON file-source metadata.")
    parameters = metadata.get("parameters") or {}
    if not isinstance(parameters, dict):
        raise ValueError("Unexpected JSON reader parameters.")
    metadata["parameters"] = {**parameters, "multiLine": "true"}
    entry = next(entry for entry in TABLES if entry[0] == source and entry[1] == table)
    metadata["path"] = f"s3a://{BUCKET}/{PREFIX}/{entry[2]}"
    headers["X-Request-ID"] = str(uuid.uuid4())
    response = layer.client.patch(endpoint, headers=headers, json=metadata)
    response.raise_for_status()


def apply(layer: ZetarisDataLayer, refresh_json: bool = False) -> dict:
    report = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "status": "in_progress", "storage": "LocalStack S3 emulation", "setup_fixtures_only": True,
              "registered": [], "verified": [], "sealed_content_queried": False}
    existing = {str(r.get("name", "")).lower() for r in rows(layer._run_sql("SHOW LIGHTNING DATABASES"))}
    for source in (SOURCE, SEALED_SOURCE):
        if source.lower() not in existing:
            layer._run_sql(f'CREATE LIGHTNING DATABASE {source} DESCRIBE BY "Cost optimizer LocalStack setup fixtures"')
    for source, table, key, format_name in TABLES:
        available = rows(layer._run_sql(f"SHOW LIGHTNING TABLES {source}"))
        table_names = {str(row["name"]).lower() for row in available}
        if refresh_json and format_name == "JSON" and table.lower() in table_names:
            update_json_reader(layer, source, table)
        if table.lower() not in table_names:
            layer._run_sql(table_sql(source, table, key, format_name))
        report["registered"].append({"table": f"{source}.{table}", "s3_key": f"{PREFIX}/{key}",
                                     "sealed": source == SEALED_SOURCE})
    for table, expected in (("connectivity_check", 1), ("founder_briefs", 3),
                            ("pricing_snapshots_approaches", 4), ("pricing_snapshots_models", 2), ("dev_task_cases", 3)):
        result = rows(layer._run_sql(f"SELECT COUNT(*) AS record_count FROM {SOURCE}.{table}"))
        if len(result) != 1 or int(result[0]["record_count"]) != expected:
            raise ValueError(f"Unexpected record count for {SOURCE}.{table}.")
        report["verified"].append({"table": f"{SOURCE}.{table}", "rows": expected})
    probe = rows(layer._run_sql(f"SELECT id, message FROM {SOURCE}.connectivity_check LIMIT 1"))
    if len(probe) != 1 or str(probe[0].get("id")) != "1" or probe[0].get("message") != "localstack_connection_ok":
        raise ValueError("LocalStack probe row did not match the uploaded CSV.")
    report["probe_row"] = probe[0]
    report["status"] = "passed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Perform the authorized source registration and query checks")
    parser.add_argument("--refresh-json", action="store_true",
                        help="Update existing dedicated JSON fixture reader options without dropping tables")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/localstack_registration_check.json")
    args = parser.parse_args()
    if not args.apply:
        print("-- LocalStack-only test credentials; the account activation token is never part of SQL.")
        for source in (SOURCE, SEALED_SOURCE):
            print(f'CREATE LIGHTNING DATABASE {source} DESCRIBE BY "Cost optimizer LocalStack setup fixtures";')
        for entry in TABLES:
            print(table_sql(*entry) + ";")
        return 0
    load_dotenv(ROOT / ".env")
    layer = None
    try:
        layer = ZetarisDataLayer(timeout_s=60)
        trace = Trace("localstack-register-" + uuid.uuid4().hex[:12], "live", log_dir=str(ROOT / "logs"))
        layer.trace = trace
        report = apply(layer, refresh_json=args.refresh_json)
        report["trace_path"] = str(trace.path)
        events = [json.loads(line) for line in trace.path.read_text(encoding="utf-8").splitlines()]
        report["query_ids"] = [event["query_id"] for event in events if event.get("query_id")]
        code = 0
    except (SetupIncomplete, httpx.HTTPError, ValueError) as error:
        # Exclude auth headers, private configuration, and raw server responses.
        report = {"status": "failed", "error_type": type(error).__name__,
                  "message": "LocalStack registration did not complete; inspect the running services and registered source metadata."}
        code = 3
    finally:
        if layer is not None:
            layer.client.close()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
