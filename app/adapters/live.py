"""Live adapters. Written against the Participant Setup Guide; the request/response
shapes MUST be confirmed against the installed instances (docs/zetaris_select1_response.json,
GET /v1/models output) before these are trusted. They fail visibly when config is absent."""
from __future__ import annotations

import os
import time
import uuid
from typing import Optional

import httpx

from app.adapters.base import DataLayer, Inference, InferenceResult, SetupIncomplete


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v or v.startswith("your-"):
        raise SetupIncomplete(f"{name} is not configured. Copy .env.example to .env and fill real values.")
    return v


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

    # The row->model mapping below depends on how Isoma registers the sources; finalize after first real query.
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


class NightshiftInference(Inference):
    """OpenAI-compatible HTTP to Nightshift. Logs requested and resolved model for every call."""

    def __init__(self, trace=None):
        base = _env("METERLESS_BASE_URL").rstrip("/")
        while base.endswith("/v1/v1"):
            base = base[:-3]
        self.base = base if base.endswith("/v1") else base + "/v1"
        self.token = _env("METERLESS_RUNTIME_TOKEN")
        self.trace = trace
        self.headers = {"Authorization": f"Bearer {self.token}", "meterless-app": "llm-cost-intelligence",
                        "meterless-scope": "user", "Content-Type": "application/json"}

    def list_models(self) -> list[str]:
        r = httpx.get(f"{self.base}/models", headers=self.headers, timeout=20)
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60) -> InferenceResult:
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.2}
        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}
        t0 = time.time()
        r = httpx.post(f"{self.base}/chat/completions", headers=self.headers, json=body, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        resolved = data.get("model")  # may be an alias; corroborate with the Nightshift receipt/log
        route_id = r.headers.get("x-request-id") or data.get("id")
        res = InferenceResult(text=data["choices"][0]["message"]["content"], requested_model=model,
                              resolved_model=resolved, route_id=route_id, usage=data.get("usage", {}),
                              elapsed_s=round(time.time() - t0, 2), execution_kind="live_inference")
        if self.trace:
            self.trace.event(role, "nightshift_request", model=resolved, requested_model=model, route_id=route_id,
                             input_summary=user[:200], output_summary=f"{len(res['text'])} chars, {res['elapsed_s']}s",
                             execution_kind="live_inference", extra={"usage": res["usage"]})
        return res
