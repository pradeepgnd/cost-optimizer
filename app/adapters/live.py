"""Live data and inference boundaries. All inference goes through Nightshift."""
from __future__ import annotations

import os
import time
from typing import Optional

import httpx

from app.adapters.base import Inference, InferenceResult, SetupIncomplete
from app.adapters.zetaris import ZetarisDataLayer  # public compatibility import
from app.spending import MAX_OUTPUT_TOKENS


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v or v.startswith("your-"):
        raise SetupIncomplete(f"{name} is not configured. Set it in private local configuration.")
    return v


class NightshiftInference(Inference):
    """OpenAI-compatible HTTP to Nightshift. Logs requested and resolved model for every call."""

    def __init__(self, trace=None):
        base = _env("METERLESS_BASE_URL").rstrip("/")
        while base.endswith("/v1/v1"):
            base = base[:-3]
        self.base = base if base.endswith("/v1") else base + "/v1"
        self.token = _env("METERLESS_RUNTIME_TOKEN")
        self.trace = trace
        self._models = None
        self.headers = {"Authorization": f"Bearer {self.token}", "meterless-app": "llm-cost-intelligence",
                        "meterless-scope": "user", "Content-Type": "application/json"}

    def list_models(self) -> list[str]:
        r = httpx.get(f"{self.base}/models", headers=self.headers, timeout=20)
        r.raise_for_status()
        self._models = [m["id"] for m in r.json().get("data", [])]
        return list(self._models)

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60) -> InferenceResult:
        if model not in (self._models if self._models is not None else self.list_models()):
            raise SetupIncomplete("Requested model was not discovered in Nightshift; implicit routing refused.")
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.2, "max_tokens": MAX_OUTPUT_TOKENS,
                "chat_template_kwargs": {"enable_thinking": False}}
        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}
        t0 = time.time()
        r = httpx.post(f"{self.base}/chat/completions", headers=self.headers, json=body, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        meterless = data.get("meterless") or {}
        winning = meterless.get("winning_route") or {}
        resolved = winning.get("model") or data.get("model")
        if resolved and "/" not in resolved and winning.get("provider"):
            resolved = winning["provider"] + "/" + resolved
        route_id = r.headers.get("x-request-id") or data.get("id")
        res = InferenceResult(text=data["choices"][0]["message"]["content"], requested_model=model,
                              resolved_model=resolved, route_id=route_id, usage=data.get("usage", {}),
                              receipt_id=meterless.get("receipt_id"), provider=winning.get("provider"),
                              requires_review=meterless.get("requires_review", False),
                              finish_reason=data["choices"][0].get("finish_reason"),
                              elapsed_s=round(time.time() - t0, 2), execution_kind="live_inference")
        if self.trace:
            self.trace.event(role, "nightshift_request", model=resolved, requested_model=model, route_id=route_id,
                             input_summary=f"{role}; bounded structured request", output_summary=f"{len(res['text'] or '')} chars, {res['elapsed_s']}s",
                             execution_kind="live_inference", extra={"usage": res["usage"], "receipt_id": res["receipt_id"],
                                                                      "provider": res["provider"]})
        return res
