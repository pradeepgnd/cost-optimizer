"""Fixed, bounded mappings for the observed JSON-envelope Zetaris schema."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid

import httpx

from app.adapters.base import DataLayer, SetupIncomplete
from app.contracts import ApproachProfile, DevTaskCase, EvidenceStatus, FounderBrief, ModelProfile, SourceRef


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value):
        raise ValueError("Invalid Zetaris namespace identifier")
    return value


def record_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}", value):
        raise ValueError("Invalid record identifier")
    return value


def table_rows(result, limit=50):
    if (not isinstance(result, dict) or result.get("error") or result.get("errors")
            or not isinstance(result.get("headers"), list) or not isinstance(result.get("data"), list)):
        raise SetupIncomplete("Zetaris returned an invalid SQL table response.")
    headers, rows = result["headers"], result["data"]
    if not all(isinstance(h, str) for h in headers) or len(set(headers)) != len(headers) or len(rows) > limit:
        raise SetupIncomplete("Zetaris response exceeded its bound or has ambiguous columns.")
    if any(not isinstance(row, list) or len(row) != len(headers) for row in rows):
        raise SetupIncomplete("Zetaris returned malformed SQL rows.")
    return [dict(zip(headers, row)) for row in rows]


class ZetarisDataLayer(DataLayer):
    def __init__(self, trace=None, timeout_s=45, s3_client=None):
        def required(name):
            value = os.getenv(name)
            if not value or value.startswith("your-"):
                raise SetupIncomplete(f"{name} is not configured in private local configuration.")
            return value
        self.base = required("ZETARIS_REST_URL").rstrip("/")
        self.org, self.key = required("ZETARIS_ORG_ID"), required("ZETARIS_API_KEY")
        self.src = identifier(os.getenv("ZETARIS_SOURCE", "oah_localstack"))
        self.sealed_src = identifier(os.getenv("ZETARIS_SEALED_SOURCE", "oah_localstack_sealed"))
        if self.src == self.sealed_src:
            raise SetupIncomplete("Ordinary and sealed Zetaris namespaces must be separate.")
        self.trace, self.client = trace, httpx.Client(timeout=timeout_s)
        self.fixture_records, self.unapproved_records = set(), set()
        self.s3 = s3_client
        self._evidence_rows, self._evidence_etags = {}, {}

    def _run_sql(self, sql, limit=50):
        qid, started = str(uuid.uuid4()), time.monotonic()
        headers = {"Authorization": f"Bearer {self.key}", "X-Org-ID": self.org,
                   "X-Request-ID": str(uuid.uuid4()), "Content-Type": "application/json"}
        response = self.client.post(f"{self.base}/sql-editor/sqls/run", headers=headers,
                                    json={"queryId": qid, "sql": sql, "source": "SqlEditor", "limit": limit})
        response.raise_for_status()
        data = response.json()
        if self.trace:
            # CREATE statements may carry source credentials: never trace raw SQL.
            self.trace.event("Analyst", "zetaris_query", query_id=qid,
                input_summary=f"{sql.split()[0]} fixed query; row limit {limit}",
                output_summary=f"HTTP {response.status_code}; {time.monotonic()-started:.2f}s")
        return data

    def _records(self, table, contract, identity, source_set, where="", sealed=False, limit=50):
        namespace = self.sealed_src if sealed else self.src
        sql = f"SELECT * FROM {namespace}.{table}{where} LIMIT {limit + 1}"
        rows = table_rows(self._run_sql(sql, limit + 1), limit)
        found, seen = [], set()
        for row in rows:
            payload = json.loads(row["payload_json"])
            value = contract.model_validate(payload)
            rid = record_id(row["record_id"])
            if rid != getattr(value, identity) or row.get(identity) != rid or rid in seen:
                raise SetupIncomplete("Record identity mismatch or duplicate in Zetaris data.")
            seen.add(rid)
            if row.get("source_version") is None or not str(row["source_version"]).strip():
                raise SetupIncomplete("Every Zetaris record requires a nonempty source version.")
            fixture = row.get("setup_fixture") in (True, "true", "True")
            if fixture:
                self.fixture_records.add(rid)
            if fixture or row.get("approved_for_evaluation") not in (True, "true", "True"):
                self.unapproved_records.add(rid)
            status = EvidenceStatus(row["evidence_status"])
            if fixture and status == EvidenceStatus.verified:
                status = EvidenceStatus.unverified
            ref = SourceRef(source_set=source_set, record_id=rid, version=str(row["source_version"]),
                            origin_url=f"zetaris://{namespace}.{table}/{rid}", status=status)
            value.source = ref
            found.append(value)
            if self.trace:
                self.trace.event("Analyst", "zetaris_record", evidence_ids=[rid],
                    output_summary=f"{namespace}.{table}; version={ref.version}; status={status.value}; fixture={fixture}")
        return found

    def read_brief(self, brief_id):
        rows = self._records("founder_briefs", FounderBrief, "brief_id", "founder_briefs",
                             f" WHERE brief_id = '{record_id(brief_id)}'", limit=1)
        if not rows:
            raise KeyError("Founder brief not found in Zetaris")
        if rows[0].brief_id != brief_id:
            raise SetupIncomplete("Zetaris returned a different founder brief than requested.")
        return rows[0], rows[0].source

    def read_approaches(self):
        return self._records("pricing_snapshots_approaches", ApproachProfile, "approach_id", "pricing_snapshots")

    def read_models(self):
        return self._records("pricing_snapshots_models", ModelProfile, "model_id", "pricing_snapshots")

    def read_task_cases(self, split):
        if split not in {"development", "holdout"}:
            raise ValueError("Task split must be development or holdout")
        table = "dev_task_cases" if split == "development" else "dev_task_cases_holdout"
        cases = self._records(table, DevTaskCase, "task_id", "dev_task_cases",
                              f" WHERE split = '{split}'", sealed=split == "holdout", limit=20)
        if any(case.split != split for case in cases):
            raise SetupIncomplete("Task payload split does not match the requested split.")
        return cases

    def read_sealed_actuals(self, project_id):
        pid = record_id(project_id)
        rows = table_rows(self._run_sql(
            f"SELECT * FROM {self.sealed_src}.retrospective_actuals WHERE project_id = '{pid}' LIMIT 2", 2), 1)
        if not rows:
            raise KeyError("Private retrospective actuals not registered")
        payload = json.loads(rows[0]["payload_json"])
        if rows[0].get("project_id") != pid or payload.get("project_id") != pid:
            raise SetupIncomplete("Actuals project does not match the frozen pack.")
        if rows[0].get("consented_for_retrospective") not in (True, "true", "True"):
            raise SetupIncomplete("Private actuals require explicit retrospective consent metadata.")
        payload["source"] = SourceRef(source_set="retrospective_actuals", record_id=record_id(rows[0]["record_id"]),
            version=str(rows[0]["source_version"]), status=EvidenceStatus(rows[0]["evidence_status"]),
            origin_url=f"zetaris://{self.sealed_src}.retrospective_actuals/{pid}").model_dump(mode="json")
        return payload

    def write_evidence(self, record):
        """S3 ingestion + the already verified file-table registration path + exact readback.

        One append-only-in-process JSON array per run, optimistic S3 writes, one dedicated table.
        Other storage topologies require a verified writer rather than invented INSERT support.
        """
        if self.src != "oah_localstack":
            raise SetupIncomplete("Evidence ingestion is verified for oah_localstack; configure a supported writer for other sources.")
        run_id, rid = record_id(record["run_id"]), record_id(record["id"])
        namespace = self.src
        suffix = hashlib.sha256(run_id.encode()).hexdigest()[:24]
        table, bucket = f"evaluation_evidence_{suffix}", "cost-optimizer-data"
        key = f"cost-optimizer/v1/evidence/{suffix}.json"
        previous = self._evidence_rows.get(run_id, [])
        if any(row["record_id"] == rid for row in previous):
            raise SetupIncomplete("Duplicate evaluation evidence ID refused.")
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        rows = previous + [{"record_id": rid, "source_version": run_id, "payload_json": payload}]
        if self.s3 is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError:
                raise SetupIncomplete("Install project requirements for S3 evidence ingestion.") from None
            self.s3 = boto3.client("s3", endpoint_url="http://127.0.0.1:4566", region_name="us-east-1",
                aws_access_key_id="test", aws_secret_access_key="test",
                config=Config(retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=15,
                              s3={"addressing_style": "path"}))
        condition = {"IfMatch": self._evidence_etags[run_id]} if previous else {"IfNoneMatch": "*"}
        try:
            result = self.s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(rows).encode(),
                                       ContentType="application/json", **condition)
        except Exception:
            raise SetupIncomplete("S3 evidence ingestion failed; no verified writeback was produced.") from None
        self._evidence_rows[run_id], self._evidence_etags[run_id] = rows, result["ETag"]
        if not previous:
            sql = (f'CREATE LIGHTNING FILESTORE TABLE {table} FROM {namespace} FORMAT JSON OPTIONS ('
                   f'PATH "s3a://{bucket}/{key}", s3Endpoint "http://cost-optimizer-localstack:4566", '
                   'inferSchema "true", multiLine "true", useS3PathStyleAccess "true", '
                   'AWSACCESSKEYID "test", AWSSECRETACCESSKEY "test")')
            created = self._run_sql(sql)
            if created.get("error") or created.get("errors"):
                raise SetupIncomplete("Zetaris evidence registration failed.")
        readback = table_rows(self._run_sql(
            f"SELECT * FROM {namespace}.{table} WHERE record_id = '{rid}' LIMIT 2", 2), 1)
        if len(readback) != 1 or readback[0].get("record_id") != rid or readback[0].get("payload_json") != payload:
            raise SetupIncomplete("Zetaris evidence readback did not match the written record.")
        ref = SourceRef(source_set="evaluation_evidence", record_id=rid, version=run_id,
                        origin_url=f"zetaris://{namespace}.{table}/{rid}")
        if self.trace:
            self.trace.event("Analyst", "evidence_writeback", evidence_ids=[rid], output_summary="S3 ingest and exact Zetaris readback verified")
        return ref

    def select_one(self):
        return self._run_sql("SELECT 1 AS one", limit=1)
