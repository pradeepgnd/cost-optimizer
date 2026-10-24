"""Retrospective comparison per Planning/06-Retrospective-Case-Study-Design.md §6.

Reads a frozen DecisionPack and the sealed actuals and reports agreement with history on one case.
Nothing here is a savings figure: both numbers are shown and no difference is presented as a result.

  python scripts/compare_retrospective.py --pack result.json --actuals actuals.json [--brief input.json] [--json-out cmp.json]

--brief accepts a RunRequest (input_examples/*.json) or a FounderBrief; it supplies the founder's own list of
alternatives. Without it, alternatives are listed but not classified as inside or outside the founder's set.

Exit codes: 0 report printed; 2 invalid input; 4 refused (pack status is not complete or frozen, or the
report would contain savings language).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError  # noqa: E402

from app.contracts import DecisionPack, EvidenceStatus, FounderBrief, RunState  # noqa: E402

ALLOWED_STATUS = {RunState.complete, RunState.frozen}
QUARTERS = (25, 50, 75)
_SAVINGS = re.compile(r"\bsav(e|ed|es|ing|ings)\b", re.IGNORECASE)


class Refused(Exception):
    """The pack is not frozen. Comparing earlier would let actuals inform a recommendation still in progress."""


# ------------------------------------------------------------------ loading

def load_pack(data: dict) -> DecisionPack:
    pack = DecisionPack.model_validate(data)
    if pack.status not in ALLOWED_STATUS:
        raise Refused(f"pack status is '{pack.status.value}'; comparison runs only on a complete or frozen pack")
    return pack


def load_brief(data: dict) -> FounderBrief:
    return FounderBrief.model_validate(data["brief"] if "brief" in data else data)


def _pct(part: Decimal, whole: Decimal) -> Optional[Decimal]:
    if not whole:
        return None
    return (part / whole * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _unit_kind(unit: str) -> str:
    u = unit.lower()
    return "credits" if "credit" in u else ("USD" if "usd" in u else u)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _ledger(pack: DecisionPack, approach_id: str):
    return next((l for l in pack.build_ledgers if l.approach_id == approach_id), None)


def _candidates(pack: DecisionPack) -> list[str]:
    return [c.approach_id for c in (pack.recommended_config, pack.alternate_config) if c is not None]


# ------------------------------------------------------------------ metrics

def approach_coverage(pack: DecisionPack, actuals: dict) -> dict:
    taken = actuals["approach_taken"]
    cands = _candidates(pack)
    return {"approach_taken": taken, "candidates": cands, "named": taken in cands,
            "priced": _ledger(pack, taken) is not None}


def build_range(pack: DecisionPack, actuals: dict) -> dict:
    taken = actuals["approach_taken"]
    total = Decimal(str(actuals["total_spend"]["amount"]))
    out = {"approach_taken": taken, "actual_total": total, "actual_unit": actuals["total_spend"]["unit"]}
    ledger = _ledger(pack, taken)
    if ledger is None:
        return {**out, "result": "not_priced"}
    e = ledger.expected_build_cost
    out.update(low=e.low, base=e.base, high=e.high, ledger_unit=e.unit)
    if None in (e.low, e.base, e.high):
        return {**out, "result": "range_unknown"}
    if _unit_kind(e.unit) != _unit_kind(out["actual_unit"]):
        return {**out, "result": "units_differ"}
    if total < e.low:
        return {**out, "result": "below_low", "pct_beyond": _pct(e.low - total, e.low)}
    if total > e.high:
        return {**out, "result": "above_high", "pct_beyond": _pct(total - e.high, e.high)}
    closest = min((("low", e.low), ("base", e.base), ("high", e.high)), key=lambda kv: abs(total - kv[1]))[0]
    return {**out, "result": "bracketed", "closest_scenario": closest}


def checkpoint_timing(pack: DecisionPack, actuals: dict) -> dict:
    """Counterfactual: a gate fires when cumulative actual spend reaches its base-scenario threshold."""
    taken = actuals["approach_taken"]
    total = Decimal(str(actuals["total_spend"]["amount"]))
    ledger = _ledger(pack, taken)
    if ledger is None:
        return {"result": "not_priced", "gates": []}
    if _unit_kind(ledger.expected_build_cost.unit) != _unit_kind(actuals["total_spend"]["unit"]):
        return {"result": "units_differ", "gates": []}
    cum, running = [], Decimal("0")
    for row in sorted(actuals.get("monthly_profile", []), key=lambda r: r["month"]):
        running += Decimal(str(row["spend"]))
        cum.append((row["month"], running))
    gates = []
    for i, cp in enumerate(ledger.checkpoints, 1):
        t = cp.cumulative_spend.base
        fired = None if t is None else t <= total
        month = next((m for m, c in cum if c >= t), None) if fired else None
        gates.append({"gate": i, "milestone": cp.milestone, "threshold_base": t, "fired": fired, "month": month,
                      "fraction_of_actual_total": _pct(t, total) if fired else None})
    fired = [g for g in gates if g["fired"]]
    before = {q: any(g["threshold_base"] <= total * q / 100 for g in fired) for q in QUARTERS}
    return {"result": "ok", "gates": gates, "first_fired": fired[0]["gate"] if fired else None, "fired_before": before}


def risk_surfacing(pack: DecisionPack, actuals: dict) -> dict:
    """Exact phrase match of each rework cause class (underscores or spaces) in the pack's gaps and risk text."""
    sections = {
        "risks": [f"{r.cause_class.value} {r.description}" for r in pack.risks],
        "evidence_gaps": [f"{g.field} {g.note}" for g in pack.evidence_gaps],
        "critique_findings": [f.claim for c in pack.critiques for f in c.findings],
        "limitations": list(pack.limitations),
        "reasons": list(pack.reasons),
    }
    classes = list(dict.fromkeys(r["cause_class"] for r in actuals.get("rework_incidents", [])))
    where = {}
    for cc in classes:
        phrases = {cc.lower(), cc.lower().replace("_", " ")}
        where[cc] = [s for s, items in sections.items() if any(p in t.lower() for t in items for p in phrases)]
    return {"cause_classes": classes, "named": [c for c in classes if where[c]],
            "missed": [c for c in classes if not where[c]], "where": where}


def alternative_surfacing(pack: DecisionPack, actuals: dict, brief: Optional[FounderBrief]) -> dict:
    taken = actuals["approach_taken"]
    alts = [a for a in _candidates(pack) if a != taken]
    if brief is None:
        return {"named_alternatives": alts, "founder_list": None, "founder_list_status": None, "outside_founder_list": None}
    known = {_norm(x) for x in brief.alternatives_considered} | {_norm(taken)}
    status = brief.field_status.get("alternatives_considered", EvidenceStatus.verified)
    return {"named_alternatives": alts, "founder_list": list(brief.alternatives_considered),
            "founder_list_status": status.value, "outside_founder_list": [a for a in alts if _norm(a) not in known]}


def compare(pack: DecisionPack, actuals: dict, brief: Optional[FounderBrief] = None) -> dict:
    return {
        "run_id": pack.run_id, "execution_mode": pack.execution_mode, "pack_status": pack.status.value,
        "actuals_status": actuals.get("total_spend", {}).get("status"),
        "approach_coverage": approach_coverage(pack, actuals),
        "build_range": build_range(pack, actuals),
        "checkpoint_timing": checkpoint_timing(pack, actuals),
        "risk_surfacing": risk_surfacing(pack, actuals),
        "alternative_surfacing": alternative_surfacing(pack, actuals, brief),
    }


# ------------------------------------------------------------------ report

def assert_no_savings_language(text: str) -> None:
    if _SAVINGS.search(text):
        raise RuntimeError("report contains savings language; case-study design section 6 forbids it")


def render(r: dict) -> str:
    lines = ["Retrospective comparison: agreement with history on one case (N=1). No difference is reported as a result.",
             f"Pack {r['run_id']} ({r['execution_mode']}, status {r['pack_status']}); actuals status: {r['actuals_status']}."]
    if r["execution_mode"] == "sample":
        lines.append("SAMPLE/OFFLINE pack: rule-based policies. This comparison exercises the script; it is not evidence.")
    if r["actuals_status"] == "synthetic":
        lines.append("Actuals are SYNTHETIC, not the founder's figures.")

    ac = r["approach_coverage"]
    lines.append(f"1. Approach coverage: {'named' if ac['named'] else 'not named'}. Approach taken: {ac['approach_taken']}; "
                 f"agent candidates: {', '.join(ac['candidates']) or 'none'}"
                 f"{'' if ac['named'] or not ac['priced'] else ' (priced in build ledgers, but not a candidate)'}.")

    br = r["build_range"]
    verdict = {
        "not_priced": "no build ledger for the approach taken",
        "range_unknown": "the agent's range for this approach is unknown",
        "units_differ": "not comparable: the range and the actual total are in different units",
        "below_low": f"actual fell below the low scenario by {br.get('pct_beyond')}%",
        "above_high": f"actual exceeded the high scenario by {br.get('pct_beyond')}%",
        "bracketed": f"bracketed, closest to the {br.get('closest_scenario')} scenario",
    }[br["result"]]
    lines.append(f"2. Build-range bracketing: {verdict}.")
    if "low" in br:
        lines.append(f"   Agent range for {br['approach_taken']}: low {br['low']} / base {br['base']} / high {br['high']} "
                     f"[{br['ledger_unit']}]; actual total {br['actual_total']} [{br['actual_unit']}].")
        if br["result"] not in ("units_differ", "range_unknown") and br["ledger_unit"] != br["actual_unit"]:
            lines.append(f"   Compared as {_unit_kind(br['ledger_unit'])}; the raw unit labels differ.")

    ct = r["checkpoint_timing"]
    lines.append("3. Checkpoint timing (counterfactual; base-scenario thresholds, monthly actuals):")
    if ct["result"] != "ok":
        lines.append(f"   not computed: {ct['result'].replace('_', ' ')}.")
    elif not ct["gates"]:
        lines.append("   the agent proposed no checkpoints for this approach.")
    else:
        for g in ct["gates"]:
            if g["fired"] is None:
                lines.append(f"   gate {g['gate']} {g['milestone']}: threshold unknown.")
            elif g["fired"]:
                when = f"in month {g['month']}" if g["month"] is not None else "(month not recorded)"
                lines.append(f"   gate {g['gate']} {g['milestone']}: threshold {g['threshold_base']}; would have fired {when}, "
                             f"at ~{g['fraction_of_actual_total']}% of total actual spend.")
            else:
                lines.append(f"   gate {g['gate']} {g['milestone']}: threshold {g['threshold_base']}; would not have fired.")
        lines.append("   Gate fired before " + "; ".join(f"{q}% of total actual spend: {'yes' if v else 'no'}"
                                                       for q, v in ct["fired_before"].items()) + ".")

    rs = r["risk_surfacing"]
    if rs["cause_classes"]:
        lines.append(f"4. Risk surfacing: {len(rs['named'])} of {len(rs['cause_classes'])} cause classes named"
                     + (f" ({', '.join(f'{c} in {'/'.join(rs['where'][c])}' for c in rs['named'])})" if rs["named"] else "")
                     + (f"; {len(rs['missed'])} missed: {', '.join(rs['missed'])}." if rs["missed"] else "."))
    else:
        lines.append("4. Risk surfacing: actuals record no rework cause classes.")

    al = r["alternative_surfacing"]
    if al["outside_founder_list"] is None:
        lines.append(f"5. Alternative surfacing: agent named {', '.join(al['named_alternatives']) or 'no alternatives'}; "
                     "founder's list not supplied (--brief), so none can be classified as outside it.")
    else:
        n = len(al["outside_founder_list"])
        lines.append(f"5. Alternative surfacing: named {n} alternative{'' if n == 1 else 's'} outside the founder's set"
                     + (f" ({', '.join(al['outside_founder_list'])})" if n else "")
                     + f". Founder's list: {', '.join(al['founder_list']) or 'empty'} (status {al['founder_list_status']}).")
    lines.append("Operating-ledger drift is not computed by this script.")
    text = "\n".join(lines)
    assert_no_savings_language(text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--actuals", required=True)
    ap.add_argument("--brief")
    ap.add_argument("--json-out")
    args = ap.parse_args()
    try:
        pack = load_pack(json.loads(Path(args.pack).read_text(encoding="utf-8")))
        actuals = json.loads(Path(args.actuals).read_text(encoding="utf-8"))
        brief = load_brief(json.loads(Path(args.brief).read_text(encoding="utf-8"))) if args.brief else None
        result = compare(pack, actuals, brief)
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 4
    except (OSError, json.JSONDecodeError, ValidationError, KeyError, TypeError) as e:
        print(f"invalid input: {type(e).__name__}: {str(e)[:300]}", file=sys.stderr)
        return 2
    try:
        report = render(result)
    except RuntimeError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 4
    print(report)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
