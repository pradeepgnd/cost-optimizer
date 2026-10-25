"""Durable paid-dispatch boundary shared by the controller and diagnostics.

Unknown outcomes are held, never retried. A request ID is correlation, not idempotency.
The ledger is authoritative across connections/process restarts; no run DB is reset.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import nullcontext
from datetime import datetime
from decimal import Decimal, ROUND_CEILING
import json
import sqlite3
import uuid
from urllib.parse import urlparse

import httpx

from app.contracts import DispatchRecord, EvidenceStatus, RateCategory, RunState, TokenUsage
from app.trace import _mask

MAX_DISPATCHES = 30
MAX_TRANSPORT_RETRIES = 2
MAX_ROLE_CALLS = {"Planner": 1, "Critic": 1, "Revision": 1}
MAX_OUTPUT_TOKENS = 1024
_SAFE_PRE_DISPATCH = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)


class DuplicateRun(Exception):
    """An existing run ID is refused without replaying paid work."""


class StopRun(Exception):
    def __init__(self, state, reason, questions=None, evidence_field=None):
        self.state, self.reason, self.questions = state, reason, questions or []
        self.evidence_field = evidence_field


def blocked(reason, field="billing_bounds"):
    return StopRun(RunState.partial, reason, evidence_field=f"dispatch.{field}")


@dataclass
class Budget:
    max_spend: Decimal
    spent: Decimal = Decimal("0")
    held: Decimal = Decimal("0")
    dispatch_count: int = 0
    transport_retries: int = 0

    def __post_init__(self):
        self.max_spend = Decimal(self.max_spend)
        if not self.max_spend.is_finite() or not 0 <= self.max_spend <= 25:
            raise ValueError("max_spend must be finite and between 0 and 25 USD")


class Checkpoints:
    """Append-before-dispatch SQLite receipts and existing run/pack checkpoints."""
    def __init__(self, path="runs.db"):
        self.conn = sqlite3.connect(path, timeout=30)
        self.conn.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, state TEXT, pack TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS events (run_id TEXT, seq INTEGER, kind TEXT, payload TEXT)")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS dispatch_operations (
            run_id TEXT NOT NULL, logical_id TEXT NOT NULL, attempt INTEGER NOT NULL,
            operation_id TEXT UNIQUE NOT NULL, record TEXT NOT NULL, response TEXT,
            PRIMARY KEY(run_id, logical_id, attempt))""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS dispatch_budgets (
            run_id TEXT PRIMARY KEY, max_spend TEXT NOT NULL)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS evidence_outbox (
            record_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, payload TEXT NOT NULL,
            status TEXT NOT NULL, source_ref TEXT, error_type TEXT)""")
        self.conn.commit()

    def claim(self, run_id):
        try:
            self.conn.execute("INSERT INTO runs (run_id, state) VALUES (?, ?)", (run_id, RunState.approved.value))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False

    def set_state(self, run_id, state):
        self.conn.execute("UPDATE runs SET state=? WHERE run_id=?", (state.value, run_id))
        self.conn.commit()

    def save_pack(self, run_id, pack):
        self.conn.execute("UPDATE runs SET pack=? WHERE run_id=?", (pack.model_dump_json(), run_id))
        self.conn.commit()

    def stage_evidence(self, run_id, record):
        payload = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        self.conn.execute("INSERT OR IGNORE INTO evidence_outbox VALUES (?, ?, ?, 'pending', NULL, NULL)", (record["id"], run_id, payload))
        existing = self.conn.execute("SELECT payload FROM evidence_outbox WHERE record_id=?", (record["id"],)).fetchone()
        if existing[0] != payload:
            self.conn.rollback()
            raise ValueError("local evidence ID conflict")
        self.conn.commit()

    def evidence_status(self, record_id, *, source=None, error=None):
        self.conn.execute("UPDATE evidence_outbox SET status=?, source_ref=?, error_type=? WHERE record_id=?",
            ("published" if source else "pending", source.model_dump_json() if source else None, error, record_id))
        self.conn.commit()

    def pending_evidence(self, run_id):
        return [json.loads(row[0]) for row in self.conn.execute(
            "SELECT payload FROM evidence_outbox WHERE run_id=? AND status='pending' ORDER BY rowid", (run_id,))]

    def operations(self, run_id):
        return [DispatchRecord.model_validate_json(row[0]) for row in self.conn.execute(
            "SELECT record FROM dispatch_operations WHERE run_id=? ORDER BY rowid", (run_id,))]

    def refresh(self, run_id, budget):
        records = self.operations(run_id)
        budget.spent = sum((r.actual_usd or Decimal("0") for r in records), Decimal("0"))
        budget.held = sum((r.reserved_usd for r in records if r.state in {"dispatching", "unknown"}), Decimal("0"))
        budget.dispatch_count = len(records)
        budget.transport_retries = sum(r.attempt > 1 for r in records)
        return records

    def reserve(self, run_id, record, budget):
        """Claim the slot AND money in a single write transaction before entering the adapter."""
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            if not self.conn.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone():
                raise blocked("run must be claimed before dispatch", "operation_claim")
            existing_budget = self.conn.execute("SELECT max_spend FROM dispatch_budgets WHERE run_id=?", (run_id,)).fetchone()
            if existing_budget and Decimal(existing_budget[0]) != budget.max_spend:
                raise blocked("persisted run budget cannot be changed on restart", "operation_claim")
            self.conn.execute("INSERT OR IGNORE INTO dispatch_budgets VALUES (?, ?)", (run_id, str(budget.max_spend)))
            records = self.refresh(run_id, budget)
            if any(r.state in {"dispatching", "unknown", "overrun"} for r in records):
                raise blocked("unresolved or exceeded operation blocks further paid dispatch; reconcile the ledger", "unknown_outcome")
            prior = [r for r in records if r.logical_id == record.logical_id]
            if record.attempt != len(prior) + 1 or any(r.state != "not_dispatched" for r in prior):
                raise blocked("logical operation already recorded; no replay permitted", "operation_claim")
            if record.attempt > 1 and budget.transport_retries >= MAX_TRANSPORT_RETRIES:
                raise blocked("global transport retry limit (2) reached", "call_limit")
            if len(records) >= MAX_DISPATCHES:
                raise blocked("total inference dispatch cap (30) reached", "call_limit")
            if record.role in MAX_ROLE_CALLS:
                logical_calls = {r.logical_id for r in records if r.role == record.role}
                if record.logical_id not in logical_calls and len(logical_calls) >= MAX_ROLE_CALLS[record.role]:
                    raise blocked(f"{record.role} call limit reached", "call_limit")
            if budget.spent + budget.held + record.reserved_usd > budget.max_spend:
                raise blocked(f"spend reservation exceeds max_spend {budget.max_spend}", "spend")
            self.conn.execute("INSERT INTO dispatch_operations VALUES (?, ?, ?, ?, ?, NULL)", (
                run_id, record.logical_id, record.attempt, record.operation_id, record.model_dump_json()))
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        self.refresh(run_id, budget)

    def finish(self, run_id, record, budget, response=None):
        self.conn.execute("UPDATE dispatch_operations SET record=?, response=? WHERE operation_id=? AND run_id=?", (
            record.model_dump_json(), None if response is None else json.dumps(_mask(response), default=str), record.operation_id, run_id))
        self.conn.commit()
        self.refresh(run_id, budget)


def _verified(source):
    try:
        date = datetime.fromisoformat(source.verified_at.replace("Z", "+00:00"))
        url = urlparse(source.origin_url)
        return (source.status == EvidenceStatus.verified and bool(source.record_id and source.version)
                and url.scheme in {"http", "https"} and bool(url.netloc) and date is not None)
    except (AttributeError, TypeError, ValueError):
        return False


def verified_rate(model, category):
    matching = [rate for rate in model.rates if rate.category == category]
    if len(matching) != 1:
        raise blocked(f"{model.model_id}: missing or ambiguous billing rate {category.value}", "rates")
    rate = matching[0]
    if (rate.unit != "1M tokens" or rate.status != EvidenceStatus.verified or not _verified(rate.source)
            or rate.usd_per_unit is None or not rate.usd_per_unit.is_finite() or rate.usd_per_unit < 0):
        raise blocked(f"{model.model_id}: unverified/unknown billing rate {category.value}", "rates")
    return rate


def request_bound(model, system, user, max_tokens):
    if not _verified(model.source):
        raise blocked(f"{model.model_id}: verified route tariff/terms source is unavailable", "rates")
    policy = model.dispatch_policy
    if not policy or not _verified(policy.source):
        raise blocked(f"{model.model_id}: cited, verified route token/billing bounds are unavailable")
    if not policy.completion_limit_includes_reasoning or policy.billing_mode != "input_output_only":
        raise blocked(f"{model.model_id}: completion/reasoning billing semantics are unconfirmed")
    if type(max_tokens) is not int or not 0 < max_tokens <= min(policy.max_output_tokens, MAX_OUTPUT_TOKENS):
        raise blocked(f"{model.model_id}: output limit exceeds the verified route bound")
    prompt_bytes = len(json.dumps([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                 ensure_ascii=False).encode("utf-8"))
    if prompt_bytes > policy.max_prompt_bytes:
        raise blocked(f"{model.model_id}: prompt exceeds the verified byte bound")
    input_bound = int((Decimal(prompt_bytes) * policy.prompt_tokens_per_byte).to_integral_value(rounding=ROUND_CEILING)) + policy.prompt_overhead_tokens
    categories = [RateCategory.input_tokens, RateCategory.output_tokens]
    if model.terms.long_context_threshold_tokens is not None and input_bound > model.terms.long_context_threshold_tokens:
        categories += [RateCategory.long_context_input_tokens, RateCategory.long_context_output_tokens]
    rates, sources = {}, [model.source, policy.source]
    for category in categories:
        rate = verified_rate(model, category)
        rates[category] = rate.usd_per_unit
        sources.append(rate.source)
    input_rate = max(rates[c] for c in categories if c in {RateCategory.input_tokens, RateCategory.long_context_input_tokens})
    output_rate = max(rates[c] for c in categories if c in {RateCategory.output_tokens, RateCategory.long_context_output_tokens})
    reserved = (Decimal(input_bound) * input_rate + Decimal(max_tokens) * output_rate) / Decimal(1_000_000)
    return input_bound, reserved, input_rate, output_rate, sources


def measured_usage(raw):
    if not isinstance(raw, dict):
        return None
    pt, ct = raw.get("prompt_tokens"), raw.get("completion_tokens")
    details = raw.get("completion_tokens_details") or {}
    if type(pt) is not int or type(ct) is not int or not isinstance(details, dict):
        return None
    reasoning = details.get("reasoning_tokens")
    if reasoning is not None and type(reasoning) is not int:
        return None
    try:
        return TokenUsage(input_tokens=pt, output_tokens=ct, reasoning_tokens=reasoning, basis="measured", method="API usage fields")
    except ValueError:
        return None


class Dispatcher:
    def __init__(self, inference, checkpoints, run_id, budget, models, trace):
        self.inference, self.ckpt, self.run_id = inference, checkpoints, run_id
        self.budget, self.models, self.trace = budget, {m.model_id: m for m in models}, trace
        self.ckpt.refresh(run_id, budget)

    def validate_routes(self, routes):
        """Reject missing route evidence before the run starts any paid role."""
        for route in routes:
            if route not in self.models or route == "meterless/auto":
                raise blocked(f"{route}: no pinned route billing profile", "rates")
            request_bound(self.models[route], "", "", MAX_OUTPUT_TOKENS)

    def call(self, *, logical_id, role, model, system, user, max_tokens=MAX_OUTPUT_TOKENS):
        profile = self.models.get(model)
        if profile is None or model == "meterless/auto":
            raise blocked(f"{model}: no pinned route billing profile; router aliases cannot bound spending", "rates")
        bound, reserved, input_rate, output_rate, sources = request_bound(profile, system, user, max_tokens)
        for attempt in range(1, MAX_TRANSPORT_RETRIES + 2):
            record = DispatchRecord(operation_id=str(uuid.uuid4()), logical_id=logical_id, attempt=attempt, role=role,
                                    requested_model=model, state="dispatching", reserved_usd=reserved,
                                    prompt_token_bound=bound, max_tokens=max_tokens, source_refs=sources)
            self.ckpt.reserve(self.run_id, record, self.budget)
            self._event(record)
            try:
                # The local receipt ID joins the adapter request trace; it does not imply provider idempotency.
                with self.inference.dispatch_context(record.operation_id) if hasattr(self.inference, "dispatch_context") else nullcontext():
                    result = self.inference.complete(role=role, model=model, system=system, user=user, max_tokens=max_tokens)
            except BaseException as error:
                safe = isinstance(error, _SAFE_PRE_DISPATCH)
                record.state = "not_dispatched" if safe else "unknown"
                record.actual_usd = Decimal("0") if safe else None
                record.error_type = type(error).__name__
                record.provider_request_id = getattr(error, "route_id", None) if isinstance(getattr(error, "route_id", None), str) else None
                record.resolved_model = getattr(error, "resolved_model", None) if isinstance(getattr(error, "resolved_model", None), str) else None
                failure_usage = getattr(error, "usage", {})
                record.usage = _mask(failure_usage) if isinstance(failure_usage, dict) else {}
                self.ckpt.finish(self.run_id, record, self.budget)
                self._event(record)
                if not isinstance(error, Exception):
                    raise
                if safe and self.budget.transport_retries < MAX_TRANSPORT_RETRIES:
                    continue
                raise blocked(f"{role} operation {record.operation_id}: {'pre-dispatch retries exhausted' if safe else 'unknown potentially charged outcome; not retried'}", "unknown_outcome") from error
            if not isinstance(result, dict) or not isinstance(result.get("text"), str):
                record.state, record.error_type = "unknown", "MalformedResponse"
                self.ckpt.finish(self.run_id, record, self.budget, result)
                self._event(record)
                raise blocked(f"{role} operation {record.operation_id}: malformed potentially charged response; not retried", "unknown_outcome")
            record.resolved_model = result.get("resolved_model") if isinstance(result.get("resolved_model"), str) else None
            record.provider_request_id = result.get("route_id") if isinstance(result.get("route_id"), str) else None
            record.usage = _mask(result.get("usage")) if isinstance(result.get("usage"), dict) else {}
            usage = measured_usage(result.get("usage"))
            if usage is None or record.resolved_model != model:
                record.state = "unknown"
                record.error_type = "UsageUnavailable" if usage is None else "UnpricedResolvedIdentity"
            else:
                # Conservative full-rate charge: provider cache/batch savings are never assumed.
                categories = (RateCategory.input_tokens, RateCategory.output_tokens)
                if profile.terms.long_context_threshold_tokens is not None and usage.input_tokens > profile.terms.long_context_threshold_tokens:
                    categories = (RateCategory.long_context_input_tokens, RateCategory.long_context_output_tokens)
                try:
                    actual_rates = [verified_rate(profile, category) for category in categories]
                except StopRun:
                    record.state, record.error_type = "unknown", "UnpricedMeasuredTariff"
                    self.ckpt.finish(self.run_id, record, self.budget, result)
                    self._event(record)
                    raise blocked(f"{role} measured tariff unavailable; charge remains reserved", "rates")
                record.actual_usd = (usage.input_tokens * actual_rates[0].usd_per_unit + usage.output_tokens * actual_rates[1].usd_per_unit) / Decimal(1_000_000)
                for rate in actual_rates:
                    if rate.source not in record.source_refs:
                        record.source_refs.append(rate.source)
                record.state = "overrun" if (usage.input_tokens > bound or usage.output_tokens > max_tokens
                                              or record.actual_usd > reserved) else "completed"
            self.ckpt.finish(self.run_id, record, self.budget, result)
            self._event(record)
            if record.state != "completed":
                raise blocked(f"{role} operation {record.operation_id}: {record.state}; further spending stopped", "unknown_outcome")
            return result
        raise blocked("global transport retry limit reached", "call_limit")

    def _event(self, record):
        if self.trace:
            self.trace.event(record.role, "dispatch_receipt", operation_id=record.operation_id,
                             requested_model=record.requested_model, model=record.resolved_model,
                             route_id=record.provider_request_id, status=record.state,
                             extra=record.model_dump(mode="json"))
