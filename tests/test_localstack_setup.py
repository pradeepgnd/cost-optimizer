import hashlib
import json
from types import SimpleNamespace

import httpx
import pytest

from scripts.prepare_localstack_data import prepare
from scripts.register_localstack_sources import SOURCE, SEALED_SOURCE, TABLES, apply, rows, table_sql, update_json_reader


def test_exports_keep_holdout_separate_and_preserve_unverified_prices(tmp_path):
    manifest = prepare(tmp_path)
    assert manifest["setup_fixtures_only"] is True
    for entry in manifest["objects"]:
        content = (tmp_path / entry["key"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
    development = json.loads((tmp_path / "inputs/dev_task_cases_development.json").read_text())
    holdout = json.loads((tmp_path / "sealed/dev_task_cases_holdout.json").read_text())
    assert {row["task_id"] for row in development} == {"T1", "T2", "T3"}
    assert {row["task_id"] for row in holdout} == {"T4", "T5", "T6"}
    assert all(row["split"] == "development" for row in development)
    assert all(row["split"] == "holdout" for row in holdout)
    pricing = json.loads((tmp_path / "inputs/pricing_snapshots_approaches.json").read_text())
    assert all(row["setup_fixture"] and row["evidence_status"] == "unverified" for row in pricing)
    assert all(rate["status"] == "unverified" for row in pricing for rate in json.loads(row["payload_json"])["rates"])
    assert not list(tmp_path.rglob("*actuals*"))
    assert not list(tmp_path.rglob("*evaluation_evidence*"))


def test_registration_reuses_existing_tables_and_never_queries_sealed_content():
    class ExistingSources:
        def __init__(self):
            self.queries = []

        def _run_sql(self, sql):
            self.queries.append(sql)
            if sql == "SHOW LIGHTNING DATABASES":
                return {"headers": ["name"], "data": [[SOURCE], [SEALED_SOURCE], ["NY_TAXI"]]}
            if sql.startswith("SHOW LIGHTNING TABLES"):
                source = sql.split()[-1]
                return {"headers": ["name"], "data": [[table] for namespace, table, *_ in TABLES if namespace == source]}
            if "COUNT(*)" in sql:
                table = sql.split(".")[-1]
                counts = {"connectivity_check": 1, "founder_briefs": 3, "pricing_snapshots_approaches": 4,
                          "pricing_snapshots_models": 2, "dev_task_cases": 3}
                return {"headers": ["record_count"], "data": [[str(counts[table])]]}
            if sql == f"SELECT id, message FROM {SOURCE}.connectivity_check LIMIT 1":
                return {"headers": ["id", "message"], "data": [["1", "localstack_connection_ok"]]}
            raise AssertionError(f"Unexpected SQL: {sql}")

    layer = ExistingSources()
    result = apply(layer)
    assert result["status"] == "passed" and len(result["registered"]) == 6
    assert not any(sql.startswith(("CREATE", "DROP", "ALTER")) for sql in layer.queries)
    assert not any(SEALED_SOURCE in sql for sql in layer.queries if sql.startswith("SELECT"))
    assert not any("NY_TAXI." in sql for sql in layer.queries)


def test_registration_rejects_error_envelope_and_unplanned_objects():
    assert 'multiLine "true"' in table_sql(*TABLES[1])
    with pytest.raises(ValueError):
        rows({"error": "registration failed"})
    with pytest.raises(ValueError):
        table_sql("unrelated_source", "anything", "unapproved.json", "JSON")


def test_json_reader_migration_preserves_source_settings_and_updates_array_path():
    methods = []

    def handle(request):
        methods.append(request.method)
        assert request.headers["Authorization"] == "Bearer test-private-credential"
        assert request.url.path.endswith("/oah_localstack/file-store-tables/founder_briefs")
        if request.method == "GET":
            return httpx.Response(200, json={"name": "founder_briefs", "format": "json",
                "path": "s3a://cost-optimizer-data/cost-optimizer/v1/inputs/founder_briefs.jsonl",
                "parameters": {"inferSchema": "true"}, "s3Settings": {"awsAccessKeyId": "test"}})
        body = json.loads(request.content)
        assert body["path"].endswith("/inputs/founder_briefs.json")
        assert body["parameters"] == {"inferSchema": "true", "multiLine": "true"}
        assert body["s3Settings"] == {"awsAccessKeyId": "test"}
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        layer = SimpleNamespace(client=client, base="http://zetaris.test/api/v1.0", key="test-private-credential", org="1")
        update_json_reader(layer, SOURCE, "founder_briefs")
    assert methods == ["GET", "PATCH"]
