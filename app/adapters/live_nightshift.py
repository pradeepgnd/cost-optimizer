"""Live Meterless Nightshift adapter. Written against the Participant Setup Guide; the response
shape MUST be confirmed against the installed runtime (GET /v1/models output) before it is
trusted. It fails visibly when config is absent."""
from __future__ import annotations

import time

import httpx

from app.adapters.base import Inference, InferenceResult, require_env as _env


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

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60, max_tokens=None) -> InferenceResult:
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.2}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
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
