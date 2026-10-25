"""Live smoke test: a diagnostic only. It changes nothing in the product and writes nothing but its report.

  python scripts/smoke_live.py

Loads .env and checks each live piece separately, continuing past failures:
  Zetaris     SELECT 1, then read_models row count
  Nightshift  GET /v1/models, then one tiny completion each for the frontier, mid-tier and Nemotron routes
              found in the price snapshot (usage, resolved model, latency)
  H-MEM       the bridge self-test (node bridge.mjs --selftest)

Prints a PASS / FAIL / SKIP table with a reason per check and saves the same table to logs/smoke-<timestamp>.md.
SKIP means a prerequisite is missing (setting, earlier check, installed file); FAIL means the check ran and failed.
Secrets are never printed: values of secret-looking settings are redacted from every message.
Exit code: 0 when nothing failed, 1 otherwise.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from app.adapters.base import SetupIncomplete  # noqa: E402
from app.trace import _mask  # noqa: E402

TIERS = (("frontier", "frontier"), ("mid_tier", "mid-tier"), ("open_source", "Nemotron"))
_SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD)", re.I)

rows: list[tuple[str, str, str, str]] = []


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
    """Rows in an unconfirmed response shape: a list, or a list under a common key."""
    if isinstance(data, list):
        return str(len(data))
    if isinstance(data, dict):
        for k in ("rows", "data", "result", "results", "records"):
            if isinstance(data.get(k), list):
                return str(len(data[k]))
    return "unknown (response shape not yet mapped)"


# ------------------------------------------------------------------ Zetaris

def check_zetaris():
    try:
        from app.adapters.live_zetaris import ZetarisDataLayer
        z = ZetarisDataLayer(timeout_s=15)
    except SetupIncomplete as e:
        record("Zetaris", "SELECT 1", "SKIP", str(e))
        record("Zetaris", "read_models", "SKIP", "depends on Zetaris settings")
        return None
    try:
        body = z.select_one()
        record("Zetaris", "SELECT 1", "PASS", f"HTTP 200; {len(str(body))} bytes; rows {_row_count(body)}")
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


def check_nightshift(models):
    try:
        from app.adapters.live_nightshift import NightshiftInference
        ns = NightshiftInference(trace=None)
    except SetupIncomplete as e:
        record("Nightshift", "GET /v1/models", "SKIP", str(e))
        for _, label in TIERS:
            record("Nightshift", f"completion: {label}", "SKIP", "depends on Nightshift settings")
        return
    try:
        routes = set(ns.list_models())
        record("Nightshift", "GET /v1/models", "PASS" if routes else "FAIL", f"{len(routes)} routes offered")
    except Exception as e:
        record("Nightshift", "GET /v1/models", "FAIL", _err(e))
        for _, label in TIERS:
            record("Nightshift", f"completion: {label}", "SKIP", "depends on GET /v1/models")
        return
    source = "Zetaris price snapshot"
    if models is None:
        from app.adapters.sample import SampleDataLayer
        models, source = SampleDataLayer().read_models(), "bundled sample price snapshot (Zetaris read unavailable)"
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
        try:
            res = ns.complete(role="smoke", model=route, system="Connectivity check. Reply with the single word OK.",
                              user="OK?", max_tokens=8, timeout_s=60)
        except Exception as e:
            record("Nightshift", name, "FAIL", f"{route}: {_err(e)}")
            continue
        u = res.get("usage") or {}
        pt, ct = u.get("prompt_tokens"), u.get("completion_tokens")
        rt = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
        detail = (f"requested {route}; resolved {res.get('resolved_model')}; latency {round(time.time() - t0, 2)} s; "
                  f"usage prompt={pt} completion={ct} reasoning={rt}")
        if not isinstance(pt, int) or not isinstance(ct, int):
            record("Nightshift", name, "FAIL", detail + "; no prompt_tokens/completion_tokens in usage")
        elif isinstance(rt, int) and rt > ct:
            record("Nightshift", name, "FAIL", detail + "; reasoning exceeds completion: confirm usage semantics")
        else:
            record("Nightshift", name, "PASS", detail)


# ------------------------------------------------------------------ H-MEM

def check_hmem():
    from app.engines.hmem import bridge as b
    missing = [p.name for p in (b.BRIDGE, b.PIN, b.HERE / "reference") if not p.exists()]
    if missing:
        record("H-MEM", "bridge self-test", "SKIP", f"bridge not installed: missing {', '.join(missing)} in app/engines/hmem/")
        return
    try:
        out = subprocess.run(["node", str(b.BRIDGE), "--selftest"], capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        record("H-MEM", "bridge self-test", "FAIL", "node is not on PATH")
        return
    except subprocess.TimeoutExpired:
        record("H-MEM", "bridge self-test", "FAIL", "self-test timed out after 20 s")
        return
    ok = out.returncode == 0 and '"status": "ok"' in out.stdout.replace("'", '"')
    rev = b.PIN.read_text().strip()
    record("H-MEM", "bridge self-test", "PASS" if ok else "FAIL",
           f"revision {rev}; exit {out.returncode}" + ("" if ok else f"; {(out.stderr or out.stdout)[:200]}"))


# ------------------------------------------------------------------ report

def table() -> str:
    head = ["| Component | Check | Result | Detail |", "|---|---|---|---|"]
    return "\n".join(head + [f"| {c} | {k} | {r} | {d.replace('|', '/')} |" for c, k, r, d in rows])


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    load_dotenv(ROOT / ".env")
    started = datetime.now(timezone.utc)
    for step in (lambda: check_nightshift(check_zetaris()), check_hmem):
        try:
            step()
        except Exception as e:  # a bug in one check must not hide the others
            record("smoke", "unexpected error", "FAIL", _err(e))
    counts = {r: sum(row[2] == r for row in rows) for r in ("PASS", "FAIL", "SKIP")}
    report = (f"# Live smoke test\n\n{started.strftime('%Y-%m-%d %H:%M:%S')} UTC. Diagnostic only; secrets redacted.\n\n"
              f"{table()}\n\n{counts['PASS']} pass, {counts['FAIL']} fail, {counts['SKIP']} skip.\n")
    print(report)
    out = ROOT / "logs" / f"smoke-{started.strftime('%Y%m%dT%H%M%SZ')}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"Saved {out.relative_to(ROOT)}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
