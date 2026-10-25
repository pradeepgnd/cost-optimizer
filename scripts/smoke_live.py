"""Live smoke diagnostic with opt-in bounded completions and a durable operation ledger.

  python scripts/smoke_live.py

Loads .env and checks each live piece separately, continuing past failures:
  Zetaris     SELECT 1, then read_models row count
  Nightshift  GET /v1/models; with a positive --max-spend-usd and verified billing/token bounds,
              one tiny completion each for the frontier, mid-tier and Nemotron routes
  H-MEM       the bridge self-test (node bridge.mjs --selftest)

Prints a PASS / FAIL / SKIP table with a reason per check and saves the same table to logs/smoke-<timestamp>.md.
SKIP means a prerequisite is missing (setting, earlier check, installed file); FAIL means the check ran and failed.
Secrets are never printed: values of secret-looking settings are redacted from every message.
Exit code: 0 only when every required diagnostic passes, 1 otherwise (including required SKIP).
Diagnostic readiness is separate from end-to-end sponsor readiness.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from app.adapters.base import SetupIncomplete  # noqa: E402
from app.adapters.validation import sql_rows, validate_select_one, validate_model_ids  # noqa: E402
from app.contracts import ReadinessCheck, ReadinessResult  # noqa: E402
from app.trace import Trace, _mask  # noqa: E402
from app.dispatch import Budget, Checkpoints, Dispatcher, StopRun  # noqa: E402

TIERS = (("frontier", "frontier"), ("mid_tier", "mid-tier"), ("open_source", "Nemotron"))
_SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD)", re.I)

rows: list[tuple[str, str, str, str]] = []
REQUIRED = (("Zetaris", "SELECT 1"), ("Zetaris", "read_models"), ("Nightshift", "GET /v1/models"),
            *(("Nightshift", f"completion: {label}") for _, label in TIERS), ("H-MEM", "bridge self-test"))


def _secrets() -> list[str]:
    return sorted((v for k, v in os.environ.items() if _SECRET_NAME.search(k) and v and len(v) >= 4), key=len, reverse=True)


def clean(text: str) -> str:
    """One line, secrets redacted, bounded length."""
    s = " ".join(str(text).split())
    for v in _secrets():
        s = s.replace(v, "...redacted")
    return str(_mask(s))[:300]


def record(component: str, check: str, result: str, detail: str):
    rows.append((component, check, result, clean(detail)))


def _err(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"


def _row_count(data) -> str:
    return str(len(sql_rows(data)))


# ------------------------------------------------------------------ Zetaris

def check_zetaris(trace=None):
    try:
        from app.adapters.live_zetaris import ZetarisDataLayer
        z = ZetarisDataLayer(trace=trace, timeout_s=15)
    except SetupIncomplete as e:
        record("Zetaris", "SELECT 1", "SKIP", str(e))
        record("Zetaris", "read_models", "SKIP", "depends on Zetaris settings")
        return None
    try:
        body = z.select_one()
        validate_select_one(body)
        record("Zetaris", "SELECT 1", "PASS", "Validated exactly one cell with value 1")
    except Exception as e:
        record("Zetaris", "SELECT 1", "FAIL", _err(e))
        record("Zetaris", "read_models", "SKIP", "depends on SELECT 1")
        return None
    try:
        models = z.read_models()
        record("Zetaris", "read_models", "PASS" if models else "FAIL", f"{len(models)} model rows")
        return models or None
    except NotImplementedError:
        try:
            raw = z._run_sql(z.TEMPLATES["pricing_models"].format(src=z.src))
            extra = f"; raw pricing_models query returned rows {_row_count(raw)}"
        except Exception as e:
            extra = f"; raw pricing_models query failed: {_err(e)}"
        record("Zetaris", "read_models", "FAIL", "read_models not implemented yet (row mapping pending)" + extra)
    except Exception as e:
        record("Zetaris", "read_models", "FAIL", _err(e))
    return None


# ------------------------------------------------------------------ Nightshift

def _pick(models, tier: str, routes: set[str]):
    """The route the controller would use for a tier, limited to routes Nightshift offers."""
    from app.controller import Controller
    in_tier = [(i, m) for i, m in enumerate(models) if m.tier == tier]
    if tier == "open_source":
        pinned = os.getenv("METERLESS_OPEN_MODEL", "")
        if pinned and not pinned.startswith("your-"):
            return pinned, "METERLESS_OPEN_MODEL"
        req = next((m for _, m in in_tier if m.required), None)
        if req is not None:
            return req.model_id, "snapshot row marked required"
    offered = [(i, m) for i, m in in_tier if m.model_id in routes]
    if not offered:
        return None, f"none of {len(in_tier)} {tier} snapshot rows is a Nightshift route"
    return min(offered, key=lambda im: Controller._rank_key(im[1], im[0]))[1].model_id, "top-ranked snapshot route"


def check_nightshift(models, trace=None, *, allowance=Decimal("0"), checkpoints=None, run_id=None):
    allowance = Decimal(allowance)
    if not allowance.is_finite() or not 0 <= allowance <= 1:
        raise ValueError("diagnostic allowance must be between 0 and 1 USD")
    try:
        from app.adapters.live_nightshift import NightshiftInference
        ns = NightshiftInference(trace=trace)
    except SetupIncomplete as e:
        record("Nightshift", "GET /v1/models", "SKIP", str(e))
        for _, label in TIERS:
            record("Nightshift", f"completion: {label}", "SKIP", "depends on Nightshift settings")
        return
    try:
        routes = set(validate_model_ids(ns.list_models()))
        record("Nightshift", "GET /v1/models", "PASS", f"{len(routes)} routes offered")
    except Exception as e:
        record("Nightshift", "GET /v1/models", "FAIL", _err(e))
        for _, label in TIERS:
            record("Nightshift", f"completion: {label}", "SKIP", "depends on GET /v1/models")
        return
    source = "Zetaris price snapshot"
    if models is None:
        from app.adapters.sample import SampleDataLayer
        models, source = SampleDataLayer().read_models(), "bundled sample price snapshot (Zetaris read unavailable)"
    if allowance == 0:
        for _, label in TIERS:
            record("Nightshift", f"completion: {label}", "SKIP", "paid diagnostic execution disabled; set a positive --max-spend-usd allowance with verified billing evidence")
        return
    if checkpoints is None:
        (ROOT / "logs").mkdir(exist_ok=True)
        checkpoints = Checkpoints(str(ROOT / "logs" / "smoke-operations.db"))
    run_id = run_id or f"smoke-{time.time_ns()}"
    if not checkpoints.claim(run_id):
        for _, label in TIERS:
            record("Nightshift", f"completion: {label}", "SKIP", "diagnostic run ID already exists; no paid requests replayed")
        return
    budget = Budget(allowance)
    dispatcher = Dispatcher(ns, checkpoints, run_id, budget, models, trace)
    for tier, label in TIERS:
        route, why = _pick(models, tier, routes)
        name = f"completion: {label}"
        if route is None:
            record("Nightshift", name, "SKIP", f"{why} ({source})")
            continue
        if route not in routes:
            record("Nightshift", name, "FAIL" if tier == "open_source" else "SKIP",
                   f"route {route} ({why}) is not offered by Nightshift ({source})")
            continue
        t0 = time.time()
        dispatched_before = budget.dispatch_count
        try:
            res = dispatcher.call(logical_id=f"diagnostic/{tier}", role="Diagnostic", model=route,
                                  system="Connectivity check. Reply with the single word OK.", user="OK?", max_tokens=8)
        except StopRun as e:
            record("Nightshift", name, "FAIL" if budget.dispatch_count > dispatched_before else "SKIP", e.reason)
            continue
        except Exception as e:
            record("Nightshift", name, "FAIL", f"{route}: {_err(e)}")
            continue
        u = res.get("usage") or {}
        if not isinstance(u, dict) or not isinstance(u.get("completion_tokens_details") or {}, dict):
            record("Nightshift", name, "FAIL", f"{route}: malformed usage/details object")
            continue
        pt, ct = u.get("prompt_tokens"), u.get("completion_tokens")
        rt = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
        detail = (f"requested {route}; resolved {res.get('resolved_model')}; latency {round(time.time() - t0, 2)} s; "
                  f"usage prompt={pt} completion={ct} reasoning={rt}")
        resolved = res.get("resolved_model")
        request_id = res.get("route_id")
        if type(pt) is not int or type(ct) is not int or pt < 0 or ct < 0:
            record("Nightshift", name, "FAIL", detail + "; no prompt_tokens/completion_tokens in usage")
        elif rt is not None and (type(rt) is not int or rt < 0 or rt > ct):
            record("Nightshift", name, "FAIL", detail + "; invalid reasoning count or reasoning exceeds completion: confirm usage semantics")
        elif not isinstance(resolved, str) or not resolved.strip() or not isinstance(request_id, str) or not request_id.strip():
            record("Nightshift", name, "FAIL", detail + "; resolved identity and response request ID are required")
        elif tier == "open_source" and (not re.search(r"(?:^|[/_.-])nemotron(?:$|[/_.-]|\d)", resolved, re.I) or resolved not in routes):
            record("Nightshift", name, "FAIL", detail + "; Nemotron identity is not corroborated by explicit discovery and response; aliases need receipt verification")
        else:
            record("Nightshift", name, "PASS", detail + f"; request ID {request_id}; diagnostic evidence only")


# ------------------------------------------------------------------ H-MEM

def check_hmem():
    from app.engines.hmem import bridge as b
    try:
        b.bridge_selftest()
        record("H-MEM", "bridge self-test", "PASS", f"pinned revision {b.PIN.read_text().strip()}; JSON status ok; persistence not checked")
    except SetupIncomplete as error:
        record("H-MEM", "bridge self-test", "SKIP", str(error))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        record("H-MEM", "bridge self-test", "FAIL", _err(error))


# ------------------------------------------------------------------ report

def table() -> str:
    head = ["| Component | Check | Result | Detail |", "|---|---|---|---|"]
    return "\n".join(head + [f"| {c} | {k} | {r} | {d.replace('|', '/')} |" for c, k, r, d in rows])


def readiness_result() -> ReadinessResult:
    observed = {(component, check): (result.lower(), detail) for component, check, result, detail in rows}
    names = list(dict.fromkeys([*REQUIRED, *observed]))
    return ReadinessResult(scope="live_diagnostic", checks=[
        ReadinessCheck(name=f"{component}/{check}", status=observed.get((component, check), ("not_verified", ""))[0],
                       detail=observed.get((component, check), ("", "Required check was not executed"))[1])
        for component, check in names
    ])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-dotenv", action="store_true", help="Ignore private dotenv settings.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "logs", help="Directory for diagnostic artifacts.")
    parser.add_argument("--max-spend-usd", default="0", help="Separate diagnostic allowance, 0–1 USD; defaults to no paid calls.")
    parser.add_argument("--operations-db", type=Path, help="Durable diagnostic operation ledger; defaults to output-dir/smoke-operations.db.")
    parser.add_argument("--run-id", help="Diagnostic idempotency key; an existing key is refused for paid work.")
    args = parser.parse_args(argv)
    try:
        allowance = Decimal(args.max_spend_usd)
        if not allowance.is_finite() or not 0 <= allowance <= 1:
            raise ValueError
    except (InvalidOperation, ValueError):
        parser.error("--max-spend-usd must be finite and between 0 and 1 USD")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if not args.no_dotenv:
        load_dotenv(ROOT / ".env")
    rows.clear()
    started = datetime.now(timezone.utc)
    stamp = started.strftime('%Y%m%dT%H%M%S%fZ')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace = Trace(f"smoke-{stamp}", "live", log_dir=str(args.output_dir), echo=False)
    checkpoints = Checkpoints(str(args.operations_db or args.output_dir / "smoke-operations.db"))
    diagnostic_id = args.run_id or f"smoke-{stamp}"
    for step in (lambda: check_nightshift(check_zetaris(trace), trace, allowance=allowance,
                                        checkpoints=checkpoints, run_id=diagnostic_id), check_hmem):
        try:
            step()
        except Exception as e:  # a bug in one check must not hide the others
            record("smoke", "unexpected error", "FAIL", _err(e))
    counts = {r: sum(row[2] == r for row in rows) for r in ("PASS", "FAIL", "SKIP")}
    readiness = readiness_result()
    report = (f"# Live smoke test\n\n{started.strftime('%Y-%m-%d %H:%M:%S')} UTC. Diagnostic only; secrets redacted.\n\n"
              f"Required diagnostic readiness: **{readiness.status}**. End-to-end sponsor readiness remains unverified.\n\n"
              f"{table()}\n\n{counts['PASS']} pass, {counts['FAIL']} fail, {counts['SKIP']} skip.\n")
    print(report)
    out = args.output_dir / f"smoke-{stamp}.md"
    out.write_text(report, encoding="utf-8")
    diagnostic_budget = Budget(allowance)
    operations = checkpoints.refresh(diagnostic_id, diagnostic_budget)
    out.with_suffix(".json").write_text(json.dumps({"checked_at": started.isoformat(),
        "readiness": readiness.model_dump(mode="json"), "trace": str(trace.path), "counts": counts,
        "run_id": diagnostic_id, "max_spend_usd": str(allowance), "spend_usd": str(diagnostic_budget.spent),
        "reserved_spend_usd": str(diagnostic_budget.held), "dispatch_count": diagnostic_budget.dispatch_count,
        "operations": [operation.model_dump(mode="json") for operation in operations]}, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {out}")
    return 0 if readiness.status == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
