"""Live Meterless Nightshift adapter. Written against the Participant Setup Guide; the response
shape MUST be confirmed against the installed runtime (GET /v1/models output) before it is
trusted. It fails visibly when config is absent."""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import time
import uuid

import httpx

from app.adapters.base import Inference, InferenceResult, SetupIncomplete, require_env as _env
from app.adapters.validation import parse_model_discovery

ADAPTER_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def strip_inline_reasoning(text: str) -> str:
    """Some routes return their reasoning inside the content, closed by </think> (the opening tag may be missing,
    as Ultra did on 2026-10-26). The answer is what follows the last closing tag. Billing is unaffected: reasoning is
    already counted inside completion tokens."""
    _, closed, answer = text.rpartition("</think>")
    return answer.lstrip() if closed else text


def parse_completion_response(data, headers) -> dict:
    """Accept only attributable, metered OpenAI-compatible completion responses.

    The requested route is checked by the durable dispatcher against the
    resolved identity; aliases need an external receipt before pricing.
    """
    if not isinstance(data, dict) or data.get("error"):
        raise ValueError("Completion response must be an object without errors")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("Completion response must contain exactly one choice")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("Completion content must be text")
    meterless = data.get("meterless")
    if meterless is None:
        meterless = {}
    if not isinstance(meterless, dict):
        raise ValueError("Nightshift receipt metadata must be an object")
    winning = meterless.get("winning_route")
    if winning is None:
        winning = {}
    if not isinstance(winning, dict):
        raise ValueError("Nightshift winning route must be an object")
    provider = winning.get("provider")
    if provider is not None and (not isinstance(provider, str) or not provider.strip()):
        raise ValueError("Nightshift winning provider is invalid")
    receipt_id = meterless.get("receipt_id")
    if receipt_id is not None and (not isinstance(receipt_id, str) or not receipt_id.strip()):
        raise ValueError("Nightshift receipt ID is invalid")
    provider_kind = winning.get("kind")
    if provider_kind is not None and (not isinstance(provider_kind, str) or not provider_kind.strip()):
        raise ValueError("Nightshift provider kind is invalid")
    requires_review = meterless.get("requires_review", False)
    if type(requires_review) is not bool:
        raise ValueError("Nightshift review flag is invalid")
    resolved = winning.get("model") or data.get("model")
    if not isinstance(resolved, str) or not resolved.strip():
        raise ValueError("Completion model identity is missing")
    if "/" not in resolved and provider:
        resolved = f"{provider}/{resolved}"
    usage = data.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("Completion usage must be an object")
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if type(prompt) is not int or type(completion) is not int or prompt < 0 or completion < 0:
        raise ValueError("Completion usage requires non-negative prompt and completion counts")
    details = usage.get("completion_tokens_details")
    if details is None:
        details = {}
    if not isinstance(details, dict):
        raise ValueError("Completion reasoning details must be an object")
    reasoning = details.get("reasoning_tokens")
    if reasoning is not None and (type(reasoning) is not int or reasoning < 0 or reasoning > completion):
        raise ValueError("Reasoning count must be within completion tokens")
    header_id = headers.get("x-request-id") if headers is not None else None
    response_id = header_id or data.get("id")
    if not isinstance(response_id, str) or not response_id.strip():
        raise ValueError("Completion response request ID is missing")
    finish_reason = choices[0].get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise ValueError("Completion finish reason is invalid")
    return {"text": strip_inline_reasoning(message["content"]), "resolved_model": resolved,
            "response_model": data.get("model"), "receipt_id": receipt_id,
            "provider": provider, "provider_kind": provider_kind,
            "requires_review": requires_review, "finish_reason": finish_reason,
            "usage": usage, "route_id": response_id}


class NightshiftInference(Inference):
    """OpenAI-compatible HTTP to Nightshift. Logs requested and resolved model for every call."""

    def __init__(self, trace=None, *, disable_thinking: bool = False, no_thinking_roles=("Planner",)):
        base = _env("METERLESS_BASE_URL").rstrip("/")
        while base.endswith("/v1/v1"):
            base = base[:-3]
        self.base = base if base.endswith("/v1") else base + "/v1"
        self.token = _env("METERLESS_RUNTIME_TOKEN")
        self.trace = trace
        self.disable_thinking = disable_thinking
        # Roles whose route returned empty responses with thinking on (Lightning, 2026-10-26); they run with thinking off.
        env_roles = os.getenv("METERLESS_NO_THINKING_ROLES")
        self.no_thinking_roles = frozenset(item.strip() for item in env_roles.split(",") if item.strip()) \
            if env_roles is not None else frozenset(no_thinking_roles)
        # Routes that also need thinking off, from the environment (comma-separated route IDs); empty by default.
        self.request_timeout_s = float(os.getenv("METERLESS_REQUEST_TIMEOUT_S") or 60)
        self.no_thinking_models = frozenset(item.strip() for item in os.getenv("METERLESS_NO_THINKING_MODELS", "").split(",")
                                            if item.strip())
        self._dispatch_operation = ContextVar("nightshift_dispatch_operation", default=None)
        # No fixed meterless-scope: with "user", Nightshift's built-in memory injected an earlier answer into similar
        # prompts and both models copied it back (2026-10-26). Each request gets its own scope in _request, so nothing
        # is shared between evaluation calls. The app's own memory is the separate H-MEM engine.
        self.headers = {"Authorization": f"Bearer {self.token}", "meterless-app": "llm-cost-intelligence",
                        "Content-Type": "application/json"}

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
            headers = {**self.headers, "X-Request-ID": operation_id, "meterless-scope": f"eval-{uuid.uuid4().hex}"}
            if method == "GET":
                response = httpx.get(f"{self.base}{path}", headers=headers, timeout=timeout)
            else:
                response = httpx.post(f"{self.base}{path}", headers=headers, json=body, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if body is None:
                result = parse_model_discovery(data)
            else:
                parsed = parse_completion_response(data, response.headers)
                result = InferenceResult(text=parsed["text"], requested_model=requested,
                                         resolved_model=parsed["resolved_model"], route_id=parsed["route_id"],
                                         receipt_id=parsed["receipt_id"], provider=parsed["provider"],
                                         provider_kind=parsed["provider_kind"], response_model=parsed["response_model"],
                                         finish_reason=parsed["finish_reason"], requires_review=parsed["requires_review"],
                                         operation_id=operation_id, usage=parsed["usage"],
                                         elapsed_s=round(time.monotonic() - started, 3), execution_kind=kind)
        except Exception as error:
            payload = data if isinstance(data, dict) else {}
            meterless = payload.get("meterless") if isinstance(payload.get("meterless"), dict) else {}
            winning = meterless.get("winning_route") if isinstance(meterless.get("winning_route"), dict) else {}
            provider = winning.get("provider") if isinstance(winning.get("provider"), str) else None
            provider_kind = winning.get("kind") if isinstance(winning.get("kind"), str) else None
            resolved = winning.get("model") or payload.get("model")
            if isinstance(resolved, str) and "/" not in resolved and provider:
                resolved = f"{provider}/{resolved}"
            error.route_id = (response.headers.get("x-request-id") or payload.get("id")) if response is not None else None
            error.resolved_model = resolved
            error.receipt_id = meterless.get("receipt_id") if isinstance(meterless.get("receipt_id"), str) else None
            error.provider = provider
            error.provider_kind = provider_kind
            error.usage = payload.get("usage", {})
            event(action, "error", model=resolved,
                  route_id=(response.headers.get("x-request-id") or payload.get("id")) if response is not None else None,
                  output_summary=f"{type(error).__name__}: {error}",
                  extra={**context, "elapsed_s": round(time.monotonic() - started, 3),
                         "http_status": response.status_code if response is not None else None,
                         "usage": payload.get("usage", {}), "receipt_id": error.receipt_id,
                         "provider": provider, "provider_kind": provider_kind})
            raise
        payload = data if isinstance(data, dict) else {}
        event(action, "success", model=result.get("resolved_model") if isinstance(result, dict) else payload.get("model"),
              route_id=response.headers.get("x-request-id") or payload.get("id"),
              output_summary=f"{len(result)} {'routes' if body is None else 'result fields'}",
              extra={**context, "elapsed_s": round(time.monotonic() - started, 3),
                     "http_status": response.status_code, "usage": payload.get("usage", {}),
                     "receipt_id": result.get("receipt_id") if isinstance(result, dict) else None,
                     "provider": result.get("provider") if isinstance(result, dict) else None,
                     "provider_kind": result.get("provider_kind") if isinstance(result, dict) else None})
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

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=None, max_tokens=None) -> InferenceResult:
        if not self._dispatch_operation.get():
            raise SetupIncomplete("Paid Nightshift requests require the durable Dispatcher reservation context")
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("Every paid request requires a positive output-token limit")
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.2}
        if self.disable_thinking or role in self.no_thinking_roles or model in self.no_thinking_models:
            body["chat_template_kwargs"] = {"enable_thinking": False}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}
        return self._request(role=role, action="nightshift_request", method="POST", path="/chat/completions",
                             timeout=timeout_s or self.request_timeout_s, body=body)
