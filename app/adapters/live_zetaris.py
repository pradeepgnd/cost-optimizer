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

import httpx

from app.adapters.base import DataLayer, require_env as _env
from app.adapters.validation import sql_rows, validate_select_one

ADAPTER_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class ZetarisDataLayer(DataLayer):
    """REST read path. One validated SQL template per source set; bounded rows; no model-generated SQL."""

    TEMPLATES = {
        "founder_briefs": "SELECT * FROM {src}.founder_briefs WHERE brief_id = '{brief_id}' LIMIT 1",
        "pricing_approaches": "SELECT * FROM {src}.pricing_snapshots_approaches LIMIT 50",
        "pricing_models": "SELECT * FROM {src}.pricing_snapshots_models LIMIT 50",
        "dev_task_cases": "SELECT * FROM {src}.dev_task_cases WHERE split = '{split}' LIMIT 20",
        "retrospective_actuals": "SELECT * FROM {sealed_src}.retrospective_actuals WHERE project_id = '{project_id}' LIMIT 1",
    }

    def __init__(self, trace=None, timeout_s: int = 45):
        self.base = _env("ZETARIS_REST_URL").rstrip("/")
        self.org = _env("ZETARIS_ORG_ID")
        self.key = _env("ZETARIS_API_KEY")
        self.src = os.getenv("ZETARIS_SOURCE", "oah")
        self.sealed_src = os.getenv("ZETARIS_SEALED_SOURCE", "oah_sealed")
        self.trace = trace
        self.client = httpx.Client(timeout=timeout_s)

    def _run_sql(self, sql: str, limit: int = 50) -> dict:
        qid = str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {self.key}", "X-Org-ID": self.org,
                   "X-Request-ID": qid, "Content-Type": "application/json"}
        body = {"queryId": qid, "sql": sql, "limit": limit}   # confirm field names against installed schema
        config_ref = hashlib.sha256(json.dumps({"base": self.base, "org": self.org, "limit": limit,
                                                "source": self.src, "sql": sql}, sort_keys=True).encode()).hexdigest()
        context = {"adapter_revision": ADAPTER_REVISION, "configuration_ref": config_ref}

        def event(action, status, **kwargs):
            if self.trace:
                self.trace.event("Analyst", action, status=status, query_id=qid, operation_id=qid,
                                 input_summary=sql, execution_kind="live_data", **kwargs)

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

    # The row->model mapping below depends on how Isioma registers the sources; finalize after first real query.
    def read_brief(self, brief_id):
        raise NotImplementedError("map rows after first real query; see docs/zetaris_select1_response.json")

    def read_approaches(self):
        raise NotImplementedError

    def read_models(self):
        raise NotImplementedError

    def read_task_cases(self, split):
        raise NotImplementedError

    def read_sealed_actuals(self, project_id):
        raise NotImplementedError

    def write_evidence(self, record):
        raise NotImplementedError("use the supported registration/ingestion path confirmed in W02")

    def select_one(self) -> dict:
        """Spine proof: SELECT 1. Save the raw body as docs/zetaris_select1_response.json."""
        return self._run_sql("SELECT 1", limit=1)
