"""Live Meterless Nightshift adapter. Written against the Participant Setup Guide; the response
shape MUST be confirmed against the installed runtime (GET /v1/models output) before it is
trusted. It fails visibly when config is absent."""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import time
import uuid

import httpx

from app.adapters.base import Inference, InferenceResult, SetupIncomplete, require_env as _env
from app.adapters.validation import parse_model_discovery

ADAPTER_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class NightshiftInference(Inference):
    """OpenAI-compatible HTTP to Nightshift. Logs requested and resolved model for every call."""

    def __init__(self, trace=None):
        base = _env("METERLESS_BASE_URL").rstrip("/")
        while base.endswith("/v1/v1"):
            base = base[:-3]
        self.base = base if base.endswith("/v1") else base + "/v1"
        self.token = _env("METERLESS_RUNTIME_TOKEN")
        self.trace = trace
        self._dispatch_operation = ContextVar("nightshift_dispatch_operation", default=None)
        self.headers = {"Authorization": f"Bearer {self.token}", "meterless-app": "llm-cost-intelligence",
                        "meterless-scope": "user", "Content-Type": "application/json"}

    def _request(self, *, role, action, method, path, timeout, body=None):
        operation_id = self._dispatch_operation.get() or str(uuid.uuid4())
        config_ref = hashlib.sha256(json.dumps({"base": self.base, "path": path, "timeout": timeout,
                                                "request": body}, sort_keys=True).encode()).hexdigest()
        context = {"adapter_revision": ADAPTER_REVISION, "configuration_ref": config_ref}
        requested = (body or {}).get("model")
        kind = "live_inference" if body is not None else "live_discovery"

        def event(name, status, **kwargs):
            if self.trace:
                self.trace.event(role, name, status=status, operation_id=operation_id, requested_model=requested,
                                 execution_kind=kind, **kwargs)

        event(action + "_attempt", "pending", extra=context)
        started = time.monotonic()
        response, data = None, None
        try:
            headers = {**self.headers, "X-Request-ID": operation_id}
            if method == "GET":
                response = httpx.get(f"{self.base}{path}", headers=headers, timeout=timeout)
            else:
                response = httpx.post(f"{self.base}{path}", headers=headers, json=body, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if body is None:
                result = parse_model_discovery(data)
            else:
                if not isinstance(data, dict) or data.get("error"):
                    raise ValueError("Completion response must be an object without errors")
                text = data["choices"][0]["message"]["content"]
                if not isinstance(text, str):
                    raise ValueError("Completion content must be text")
                resolved = data.get("model")
                if resolved is not None and (not isinstance(resolved, str) or not resolved.strip()):
                    raise ValueError("Completion model identity must be a nonblank string when present")
                usage = data.get("usage") or {}
                if not isinstance(usage, dict):
                    raise ValueError("Completion usage must be an object")
                result = InferenceResult(text=text, requested_model=requested, resolved_model=resolved,
                                         route_id=response.headers.get("x-request-id") or data.get("id"),
                                         operation_id=operation_id, usage=usage,
                                         elapsed_s=round(time.monotonic() - started, 3), execution_kind=kind)
        except Exception as error:
            payload = data if isinstance(data, dict) else {}
            error.route_id = (response.headers.get("x-request-id") or payload.get("id")) if response is not None else None
            error.resolved_model = payload.get("model")
            error.usage = payload.get("usage", {})
            event(action, "error", model=payload.get("model"),
                  route_id=(response.headers.get("x-request-id") or payload.get("id")) if response is not None else None,
                  output_summary=f"{type(error).__name__}: {error}",
                  extra={**context, "elapsed_s": round(time.monotonic() - started, 3),
                         "http_status": response.status_code if response is not None else None,
                         "usage": payload.get("usage", {})})
            raise
        payload = data if isinstance(data, dict) else {}
        event(action, "success", model=payload.get("model"),
              route_id=response.headers.get("x-request-id") or payload.get("id"),
              output_summary=f"{len(result)} {'routes' if body is None else 'result fields'}",
              extra={**context, "elapsed_s": round(time.monotonic() - started, 3),
                     "http_status": response.status_code, "usage": payload.get("usage", {})})
        return result

    def list_models(self) -> list[str]:
        return self._request(role="Controller", action="nightshift_models", method="GET", path="/models", timeout=20)

    @contextmanager
    def dispatch_context(self, operation_id):
        context = self._dispatch_operation.set(operation_id)
        try:
            yield
        finally:
            self._dispatch_operation.reset(context)

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60, max_tokens=None) -> InferenceResult:
        if not self._dispatch_operation.get():
            raise SetupIncomplete("Paid Nightshift requests require the durable Dispatcher reservation context")
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("Every paid request requires a positive output-token limit")
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.2}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}
        return self._request(role=role, action="nightshift_request", method="POST", path="/chat/completions",
                             timeout=timeout_s, body=body)
