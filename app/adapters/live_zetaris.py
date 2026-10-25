"""Live Zetaris adapter. Written against the Participant Setup Guide; the request/response
shapes MUST be confirmed against the installed instance (docs/zetaris_select1_response.json)
before it is trusted. It fails visibly when config is absent."""
from __future__ import annotations

import os
import time
import uuid

import httpx

from app.adapters.base import DataLayer, require_env as _env


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
                   "X-Request-ID": str(uuid.uuid4()), "Content-Type": "application/json"}
        body = {"queryId": qid, "sql": sql, "limit": limit}   # confirm field names against installed schema
        t0 = time.time()
        r = self.client.post(f"{self.base}/sql-editor/sqls/run", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        if self.trace:
            self.trace.event("Analyst", "zetaris_query", query_id=qid,
                             input_summary=sql[:200], output_summary=f"HTTP {r.status_code}, {len(str(data))} bytes, {round(time.time()-t0,2)}s")
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
