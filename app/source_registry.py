"""Publisher-side S3/Lightning integration. Never constructed by the application runtime.

AWS credentials belong to this separate publishing process and Zetaris. LocalStack uses
explicit test credentials and a dedicated namespace; no existing data sources are replaced.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import threading

from app.adapters.base import SetupIncomplete
from app.adapters.live_zetaris import identifier, record_id, decode_envelope
from app.adapters.validation import table_rows
from app.source_contracts import SourceBindings, StorageConfig
from app.source_snapshots import canonical, digest, envelope, json_load, validate_bundle


def storage_client(config: StorageConfig):
    import boto3
    from botocore.config import Config
    options = {"region_name": config.region, "config": Config(connect_timeout=5, read_timeout=30,
        retries={"total_max_attempts": 3}, s3={"addressing_style": "path"})}
    if config.backend == "localstack":
        options.update(endpoint_url=config.publisher_endpoint, aws_access_key_id="test", aws_secret_access_key="test")
    return boto3.client("s3", **options)


def _not_found(error):
    return getattr(error, "response", {}).get("Error", {}).get("Code") in {"404", "NoSuchKey", "NoSuchBucket", "NotFound"}


def _precondition(error):
    return getattr(error, "response", {}).get("Error", {}).get("Code") in {"412", "PreconditionFailed", "ConditionalRequestConflict"}


def put_immutable(client, bucket, key, raw):
    """Create-only publication; identical content is reusable, differing content is a conflict."""
    try:
        result = client.put_object(Bucket=bucket, Key=key, Body=raw, ContentType="application/json", IfNoneMatch="*")
        return {"key": key, "sha256": digest(raw), "version_id": result.get("VersionId"), "reused": False}
    except Exception as error:
        if not _precondition(error):
            raise
        existing = client.get_object(Bucket=bucket, Key=key)
        observed = existing["Body"].read(len(raw) + 1)
        if observed != raw:
            raise ValueError(f"immutable object conflict: {key}") from None
        return {"key": key, "sha256": digest(raw), "version_id": existing.get("VersionId"), "reused": True}


AWS_KEY_ID_ENV = "ZETARIS_S3_ACCESS_KEY_ID"
AWS_SECRET_ENV = "ZETARIS_S3_SECRET_ACCESS_KEY"
_AWS_KEY_ID = re.compile(r"AKIA[A-Z0-9]{16}")
_AWS_SECRET = re.compile(r"[A-Za-z0-9/+=]{40}")
PLACEHOLDER_CREDENTIALS = ("<key id>", "<secret>")


def aws_source_credentials():
    """Read-only S3 key for Zetaris, taken from the publishing process environment only.

    The local Zetaris build reads S3 file stores only with credentials in the table OPTIONS;
    per-bucket fs.s3a settings in spark-defaults.conf are ignored (verified 2026-10-26).
    Zetaris stores datasource credentials encrypted. Never put these values in .env or the repo.
    """
    key_id = os.getenv(AWS_KEY_ID_ENV, "").strip()
    secret = os.getenv(AWS_SECRET_ENV, "").strip()
    if not key_id or not secret:
        raise SetupIncomplete(f"AWS registration needs {AWS_KEY_ID_ENV} and {AWS_SECRET_ENV} "
                              "in the publishing process environment (not .env)")
    # Shape checks also keep the values from breaking out of the SQL string literals.
    if not _AWS_KEY_ID.fullmatch(key_id) or not _AWS_SECRET.fullmatch(secret):
        raise SetupIncomplete("AWS registration credentials are malformed; expected a long-lived IAM user access key")
    return key_id, secret


def table_sql(config, table, key, *, credentials=None):
    """CREATE statement for one file-store table. AWS statements carry placeholders unless real
    credentials are passed, so previews and reports never contain a key."""
    identifier(table)
    if config.backend == "localstack":
        extra = (f', s3Endpoint "{config.zetaris_endpoint}", useS3PathStyleAccess "true", '
                 'AWSACCESSKEYID "test", AWSSECRETACCESSKEY "test"')
    else:
        key_id, secret = credentials or PLACEHOLDER_CREDENTIALS
        extra = f', AWSACCESSKEYID "{key_id}", AWSSECRETACCESSKEY "{secret}"'
    return (f'CREATE LIGHTNING FILESTORE TABLE {table} FROM {config.namespace} FORMAT JSON OPTIONS ('
            f'PATH "s3a://{config.bucket}/{key}", inferSchema "true", multiLine "true"{extra})')


def ensure_namespace(layer, namespace):
    available = table_rows(layer._run_sql("SHOW LIGHTNING DATABASES", 500), 500)
    if namespace.lower() not in {str(row.get("name", "")).lower() for row in available}:
        layer._run_sql(f'CREATE LIGHTNING DATABASE {identifier(namespace)} DESCRIBE BY "Versioned cost advisor sources"')


def ensure_table(layer, config, table, key, *, credentials=None):
    available = table_rows(layer._run_sql(f"SHOW LIGHTNING TABLES {config.namespace}", 20_000), 20_000)
    names = {str(row.get("name", "")).lower() for row in available}
    if table.lower() not in names:
        if config.backend == "aws" and credentials is None:
            credentials = aws_source_credentials()
        layer._run_sql(table_sql(config, table, key, credentials=credentials))
        return "created"
    # Reuse only a source whose physical path/format matches; never PATCH or DROP a conflicting table.
    response = layer.client.get(f"{layer.base}/lightning-database/databases/{config.namespace}/file-store-tables/{table}",
        headers={"Authorization": f"Bearer {layer.key}", "X-Org-ID": layer.org})
    response.raise_for_status()
    metadata = response.json()
    if (metadata.get("path") != f"s3a://{config.bucket}/{key}" or str(metadata.get("format", "")).lower() != "json"
            or str((metadata.get("parameters") or {}).get("multiLine", "")).lower() != "true"):
        raise ValueError(f"registered source conflict: {config.namespace}.{table}")
    return "reused"


def bundle_plan(bundle_dir: Path, config: StorageConfig):
    manifest = validate_bundle(bundle_dir)
    sid = manifest["bundle_id"]
    tables = {name.removesuffix(".json"): f"{name.removesuffix('.json')}_{sid}" for name in manifest["files"]}
    bindings = SourceBindings(namespace=config.namespace, snapshot_id=sid, tables=tables,
        expected_counts=manifest["counts"], expected_ids=manifest["ids"], catalog_acquisition=manifest["catalog_acquisition"],
        catalog_retrieved_at=manifest["retrieved_at"], expected_row_sha256={kind: {
            row["record_id"]: digest(canonical(row)) for row in json_load((bundle_dir / f"{kind}.json").read_bytes())}
            for kind in tables})
    return {"mode": "dry_run", "storage": config.backend, "bucket": config.bucket, "namespace": config.namespace,
        "snapshot_id": sid, "tables": [{"kind": kind, "table": table, "object_key": f"{config.prefix}/bundles/{sid}/{kind}.json",
            "sha256": manifest["files"][f"{kind}.json"], "expected_rows": manifest["counts"][kind],
            "statement": table_sql(config, table, f"{config.prefix}/bundles/{sid}/{kind}.json")} for kind, table in tables.items()],
        "bindings": bindings.model_dump(mode="json"), "mutations_performed": False,
        "credential_mode": "LocalStack test credentials" if config.backend == "localstack" else
            f"publisher SDK chain for S3 writes; read-only Zetaris key from {AWS_KEY_ID_ENV}/{AWS_SECRET_ENV} in table OPTIONS"}


def register_bundle(layer, bundle_dir, config, *, client=None):
    # Fail before any publication when the Zetaris read key is missing.
    credentials = aws_source_credentials() if config.backend == "aws" else None
    plan = bundle_plan(bundle_dir, config)
    client = client or storage_client(config)
    manifest = validate_bundle(bundle_dir)
    publications = []
    # Publish data before a release marker; a failed registration never promotes a current pointer.
    for name in [*manifest["files"], *manifest["source_catalog_files"], "manifest.json"]:
        publications.append(put_immutable(client, config.bucket, f"{config.prefix}/bundles/{manifest['bundle_id']}/{name}",
                                          (bundle_dir / name).read_bytes()))
    ensure_namespace(layer, config.namespace)
    registration = []
    for entry in plan["tables"]:
        state = ensure_table(layer, config, entry["table"], entry["object_key"], credentials=credentials)
        result = table_rows(layer._run_sql(f"SELECT COUNT(*) AS record_count FROM {config.namespace}.{entry['table']}", 2), 1)
        if len(result) != 1 or int(result[0]["record_count"]) != entry["expected_rows"]:
            raise ValueError("registered source row count does not match the pinned bundle")
        registration.append({"kind": entry["kind"], "table": entry["table"], "state": state, "rows": entry["expected_rows"]})
    # Verify full IDs and content hashes through Zetaris, not just COUNT(*).
    bindings = SourceBindings.model_validate(plan["bindings"]).model_copy(update={"registered": True})
    for kind, table in bindings.tables.items():
        limit = bindings.expected_counts[kind]
        result = table_rows(layer._run_sql(f"SELECT * FROM {bindings.namespace}.{table} LIMIT {limit + 1}", limit + 1), limit)
        expected_rows = {row["record_id"]: row for row in json_load((bundle_dir / f"{kind}.json").read_bytes())}
        if {row.get("record_id") for row in result} != set(expected_rows) or len(result) != len(expected_rows):
            raise ValueError("registered source IDs are incomplete")
        for raw in result:
            row, _ = decode_envelope(raw)
            if row.model_dump(mode="json") != expected_rows[row.record_id]:
                raise ValueError("registered source content differs from the published bundle")
    release = {"snapshot_id": bindings.snapshot_id, "bindings": bindings.model_dump(mode="json"),
               "bundle_manifest_sha256": digest((bundle_dir / "manifest.json").read_bytes())}
    publications.append(put_immutable(client, config.bucket, f"{config.prefix}/releases/{bindings.snapshot_id}.json", canonical(release)))
    return {"status": "pass", "storage": config.backend, "bindings": bindings.model_dump(mode="json"),
            "publications": publications, "registration": registration, "current_pointer_updated": False}


class EvidencePublisher:
    """Separate ingestion process: append-only IDs, durable CAS and exact Zetaris readback."""
    def __init__(self, layer, config, bindings, *, client=None):
        if config.namespace != bindings.namespace or not bindings.registered:
            raise ValueError("publisher needs registered bindings for its dedicated namespace")
        self.layer, self.config, self.bindings = layer, config, bindings
        self.credentials = aws_source_credentials() if config.backend == "aws" else None
        self.client = client or storage_client(config)
        self.lock = threading.Lock()

    def write(self, record):
        if not isinstance(record, dict) or not {"id", "run_id", "kind", "payload"}.issubset(record):
            raise ValueError("evidence needs id, run_id, kind and payload")
        run_id, rid = record_id(record["run_id"]), record_id(record["id"])
        if "/" in run_id or not rid.startswith(run_id + "/"):
            raise ValueError("evidence ID must be scoped to its exact run")
        if record["kind"] not in {"feature_sample", "decision_evidence", "integration_test_fixture"}:
            raise ValueError("unsupported evidence kind")
        raw = canonical(record)
        if len(raw) > 1024 * 1024:
            raise ValueError("evidence exceeded 1 MiB bound")
        fixture = record["kind"] == "integration_test_fixture"
        row = envelope(rid, self.bindings.snapshot_id, record, "evaluation_evidence", fixture).model_dump(mode="json")
        suffix = digest(run_id.encode())[:20]
        key = f"{self.config.prefix}/evidence/{suffix}.json"
        table = f"evidence_{suffix}"
        with self.lock:
            for attempt in range(3):
                try:
                    previous = self.client.get_object(Bucket=self.config.bucket, Key=key)
                    body = previous["Body"].read(8 * 1024 * 1024 + 1)
                    if len(body) > 8 * 1024 * 1024:
                        raise ValueError("run evidence exceeded 8 MiB bound")
                    rows, etag = json_load(body), previous["ETag"]
                except Exception as error:
                    if not _not_found(error):
                        raise
                    rows, etag = [], None
                seen = {}
                for existing in rows:
                    decoded, payload = decode_envelope(existing)
                    if decoded.record_id in seen or payload.get("run_id") != run_id:
                        raise ValueError("invalid existing evidence collection")
                    seen[decoded.record_id] = existing
                if rid in seen:
                    if seen[rid] != row:
                        raise ValueError("evidence ID conflict; a published output cannot be replaced")
                    break
                if len(rows) >= 1000:
                    raise ValueError("run evidence count bound reached")
                condition = {"IfMatch": etag} if etag else {"IfNoneMatch": "*"}
                try:
                    self.client.put_object(Bucket=self.config.bucket, Key=key, Body=canonical([*rows, row]),
                        ContentType="application/json", **condition)
                    break
                except Exception as error:
                    if not _precondition(error) or attempt == 2:
                        raise
            ensure_table(self.layer, self.config, table, key, credentials=self.credentials)
            payload, ref = self.layer.read_evidence(rid)
            if canonical(payload) != raw or ref.content_sha256 != row["payload_sha256"]:
                raise ValueError("published evidence readback differs; publication is not verified")
            return ref
