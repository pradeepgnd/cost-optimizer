"""Live Zetaris adapter. Written against the Participant Setup Guide; the request/response
shapes MUST be confirmed against the installed instance (docs/zetaris_select1_response.json)
before it is trusted. It fails visibly when config is absent."""
from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
import time
import uuid
import re

import httpx

from app.adapters.base import DataLayer, SetupIncomplete, require_env as _env
from app.adapters.validation import sql_rows, table_rows, validate_select_one
from app.contracts import ApproachProfile, DevTaskCase, EvidenceStatus, FounderBrief, ModelProfile, SourceRef
from app.source_contracts import CatalogModel, RecordEnvelope, SourceBindings
from app.source_snapshots import canonical, digest, json_load

ADAPTER_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_CREDENTIAL_OPTION = re.compile(r'\b(AWSACCESSKEYID|AWSSECRETACCESSKEY)(\s+)"[^"]*"', re.I)


def redact_sql(sql: str) -> str:
    """Mask credential options so source-registration statements never reach traces or hashes."""
    return _CREDENTIAL_OPTION.sub(r'\1\2"...redacted"', sql)


class ZetarisDataLayer(DataLayer):
    """REST read path. One validated SQL template per source set; bounded rows; no model-generated SQL."""

    TEMPLATES = {
        "founder_briefs": "SELECT * FROM {src}.founder_briefs WHERE brief_id = '{brief_id}' LIMIT 1",
        "pricing_approaches": "SELECT * FROM {src}.pricing_snapshots_approaches LIMIT 50",
        "pricing_models": "SELECT * FROM {src}.pricing_snapshots_models LIMIT 50",
        "dev_task_cases": "SELECT * FROM {src}.dev_task_cases WHERE split = '{split}' LIMIT 20",
        "retrospective_actuals": "SELECT * FROM {sealed_src}.retrospective_actuals WHERE project_id = '{project_id}' LIMIT 1",
    }

    def __init__(self, trace=None, timeout_s: int = 45, *, bindings=None, evidence_writer=None):
        self.base = _env("ZETARIS_REST_URL").rstrip("/")
        self.org = _env("ZETARIS_ORG_ID")
        self.key = _env("ZETARIS_API_KEY")
        self.src = identifier(os.getenv("ZETARIS_SOURCE", "oah"))
        self.sealed_src = identifier(os.getenv("ZETARIS_SEALED_SOURCE", "oah_sealed"))
        if self.src == self.sealed_src:
            raise SetupIncomplete("ordinary and sealed namespaces must be separate")
        if bindings is None and os.getenv("ZETARIS_BINDINGS_FILE"):
            bindings = SourceBindings.model_validate_json(Path(os.environ["ZETARIS_BINDINGS_FILE"]).read_text())
        self.bindings = bindings
        if bindings:
            self.src = bindings.namespace
            if self.src == self.sealed_src:
                raise SetupIncomplete("source bindings cannot target the sealed namespace")
        self.evidence_writer = evidence_writer
        self.last_query_id = None
        self.trace = trace
        self.client = httpx.Client(timeout=timeout_s)

    def _run_sql(self, sql: str, limit: int = 50) -> dict:
        qid = str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {self.key}", "X-Org-ID": self.org,
                   "X-Request-ID": qid, "Content-Type": "application/json"}
        body = {"queryId": qid, "sql": sql, "source": "SqlEditor", "limit": limit}
        self.last_query_id = qid
        config_ref = hashlib.sha256(json.dumps({"base": self.base, "org": self.org, "limit": limit,
                                                "source": self.src, "sql": redact_sql(sql)}, sort_keys=True).encode()).hexdigest()
        context = {"adapter_revision": ADAPTER_REVISION, "configuration_ref": config_ref}

        def event(action, status, **kwargs):
            if self.trace:
                self.trace.event("Analyst", action, status=status, query_id=qid, operation_id=qid,
                                 input_summary=sql if sql.lstrip().upper().startswith("SELECT") else f"{sql.split()[0]} fixed source statement",
                                 execution_kind="live_data", **kwargs)

        event("zetaris_query_attempt", "pending", extra=context)
        t0 = time.monotonic()
        response = None
        try:
            response = self.client.post(f"{self.base}/sql-editor/sqls/run", headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            sql_rows(data)
            if sql.strip().upper() == "SELECT 1":
                validate_select_one(data)
        except Exception as error:
            event("zetaris_query", "error", output_summary=f"{type(error).__name__}: {error}",
                  route_id=response.headers.get("x-request-id") if response is not None else None,
                  extra={**context, "elapsed_s": round(time.monotonic() - t0, 3),
                         "http_status": response.status_code if response is not None else None})
            raise
        event("zetaris_query", "success", output_summary=f"HTTP {response.status_code}; {len(sql_rows(data))} rows",
              route_id=response.headers.get("x-request-id"),
              extra={**context, "elapsed_s": round(time.monotonic() - t0, 3), "http_status": response.status_code})
        return data

    def _bound_table(self, key):
        if not self.bindings or not self.bindings.registered or key not in self.bindings.tables:
            raise SetupIncomplete(f"No registered pinned {key} binding; run scripts/register_sources.py first")
        return f"{self.src}.{self.bindings.tables[key]}"

    def _records(self, key, contract, identity, *, rid=None):
        table = self._bound_table(key)
        expected = self.bindings.expected_counts[key]
        if expected > 20_000:
            raise SetupIncomplete("source record count exceeds the configured bound")
        predicate = f"snapshot_id = '{record_id(self.bindings.snapshot_id)}'"
        if rid is not None:
            predicate += f" AND record_id = '{record_id(rid)}'"
        bound = 1 if rid is not None else expected
        # Fetch one extra row to detect bound violations; never silently LIMIT 50 over a whole catalog.
        raw = table_rows(self._run_sql(f"SELECT * FROM {table} WHERE {predicate} LIMIT {bound + 1}", bound + 1), bound)
        values, seen = [], set()
        for item in raw:
            row, payload = decode_envelope(item)
            if digest(canonical(row.model_dump(mode="json"))) != self.bindings.expected_row_sha256[key].get(row.record_id):
                raise ValueError("Zetaris row differs from the pinned release hash")
            value = contract.model_validate(payload)
            if row.snapshot_id != self.bindings.snapshot_id or getattr(value, identity) != row.record_id or row.record_id in seen:
                raise ValueError("Zetaris source identity/version mismatch or duplicate")
            if rid is not None and row.record_id != rid:
                raise ValueError("Zetaris returned a different record than requested")
            seen.add(row.record_id)
            transport = SourceRef(source_set=row.source_set, record_id=row.record_id, version=row.snapshot_id,
                status=EvidenceStatus.unverified if row.integration_test_fixture else EvidenceStatus.verified,
                origin_url=f"zetaris://{table}/{row.record_id}", transport_ref=f"zetaris://{table}/{row.record_id}",
                query_id=self.last_query_id, content_sha256=row.payload_sha256, snapshot_id=row.snapshot_id)
            if key == "catalog":
                transport.origin_url = self.bindings.catalog_source_url
                transport.verified_at = self.bindings.catalog_retrieved_at if self.bindings.catalog_acquisition == "https_api" else None
                if self.bindings.catalog_acquisition != "https_api":
                    transport.status = EvidenceStatus.unverified
            elif key == "briefs":
                transport.status = value.source.status if value.source else EvidenceStatus.assumed
            if hasattr(value, "source") and value.source:
                # Keep the original published tariff URL/date/status for billing validation.
                value.source = attach_transport(value.source, transport, row.integration_test_fixture)
                if isinstance(value, ModelProfile):
                    value.rates = [rate.model_copy(update={"source": attach_transport(rate.source, transport, row.integration_test_fixture),
                        "status": EvidenceStatus.unverified if row.integration_test_fixture else rate.status}) for rate in value.rates]
                    if row.integration_test_fixture:
                        value.dispatch_policy = None
            values.append((value, transport))
        if rid is None and seen != set(self.bindings.expected_ids[key]):
            raise ValueError("Zetaris source is incomplete or contains unexpected IDs")
        return values

    def read_brief(self, brief_id):
        records = self._records("briefs", FounderBrief, "brief_id", rid=brief_id)
        if not records:
            raise KeyError("founder brief not found")
        value, transport = records[0]
        return value, value.source or transport

    def read_approaches(self):
        if self.bindings and "approaches" not in self.bindings.tables:
            return []  # optional build data is independent of operating economics
        return [value for value, _ in self._records("approaches", ApproachProfile, "approach_id")]

    def read_models(self):
        return [value for value, _ in self._records("models", ModelProfile, "model_id")]

    def read_catalog(self, catalog_id):
        records = self._records("catalog", CatalogModel, "catalog_id", rid=catalog_id)
        if not records:
            raise KeyError("catalog model not found")
        return records[0]

    def read_task_cases(self, split):
        raise SetupIncomplete("Shelved task sources are not bound by the v4 source pipeline")

    def read_sealed_actuals(self, project_id):
        raise SetupIncomplete("Sealed retrospective source remains unbound; the controller allowlist is unchanged")

    def write_evidence(self, record):
        if self.evidence_writer is not None:
            return self.evidence_writer(record)
        url, token = os.getenv("SOURCE_INGEST_URL"), os.getenv("SOURCE_INGEST_TOKEN")
        if not url or not token:
            raise SetupIncomplete("Evidence ingestion is not configured; local outbox is retained")
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if (parsed.scheme not in {"http", "https"} or parsed.username or parsed.password
                or parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}):
            raise SetupIncomplete("Evidence ingestion requires HTTPS or a loopback endpoint")
        response = self.client.post(url.rstrip("/") + "/evidence", headers={"Authorization": f"Bearer {token}"}, json=record)
        response.raise_for_status()
        return SourceRef.model_validate(response.json()["source"])

    def read_evidence(self, rid):
        # One deterministic source table per run; it is populated only by the separate publisher process.
        if not self.bindings:
            raise SetupIncomplete("evidence readback requires source bindings")
        run_id = rid.split("/", 1)[0]
        table = f"{self.src}.evidence_{digest(run_id.encode())[:20]}"
        rows = table_rows(self._run_sql(f"SELECT * FROM {table} WHERE record_id = '{record_id(rid)}' LIMIT 2", 2), 1)
        if not rows:
            raise KeyError("published evidence not found")
        row, payload = decode_envelope(rows[0])
        if (row.record_id != rid or payload.get("id") != rid or payload.get("run_id") != run_id
                or row.source_set != "evaluation_evidence" or row.snapshot_id != self.bindings.snapshot_id):
            raise ValueError("evidence readback identity mismatch")
        return payload, SourceRef(source_set="evaluation_evidence", record_id=rid, version=row.payload_sha256,
            status=EvidenceStatus.unverified if row.integration_test_fixture else EvidenceStatus.verified,
            origin_url=f"zetaris://{table}/{rid}", transport_ref=f"zetaris://{table}/{rid}", query_id=self.last_query_id,
            content_sha256=row.payload_sha256, snapshot_id=row.snapshot_id)

    def select_one(self) -> dict:
        """Spine proof: SELECT 1. Save the raw body as docs/zetaris_select1_response.json."""
        return self._run_sql("SELECT 1", limit=1)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value):
        raise ValueError("invalid Zetaris identifier")
    return value


def record_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9~][A-Za-z0-9._:/~@+-]{0,511}", value):
        raise ValueError("invalid record ID")
    return value


def decode_envelope(item):
    # Spark may stringify boolean columns in REST results; accept only the two explicit values.
    item = dict(item)
    flag = item.get("integration_test_fixture", False)
    if type(flag) is not bool and flag not in ("true", "false"):
        raise ValueError("ambiguous fixture flag")
    if flag in ("true", "false"):
        item["integration_test_fixture"] = flag == "true"
    row = RecordEnvelope.model_validate(item)
    if digest(row.payload_json.encode("utf-8")) != row.payload_sha256:
        raise ValueError("Zetaris payload content hash mismatch")
    return row, json_load(row.payload_json)


def attach_transport(original, transport, fixture):
    return original.model_copy(update={"transport_ref": transport.transport_ref, "query_id": transport.query_id,
        "content_sha256": transport.content_sha256, "snapshot_id": transport.snapshot_id,
        "status": EvidenceStatus.unverified if fixture else original.status})
