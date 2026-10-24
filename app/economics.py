"""Deterministic economics. Decimal only. Unknown stays unknown.

Two ledgers, never summed:
  build_ledger      — AI-assisted development cost before launch (PRD §7.1)
  operating_ledger  — post-launch monthly cost and unit economics (PRD §7.2)
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.contracts import (
    ApproachProfile, BuildLedger, Checkpoint, EvidenceStatus, FeatureItem,
    ModelProfile, OperatingLedger, RateCategory, Scenario, UsageAssumptions,
)

CENT = Decimal("0.01")
DEFAULT_REWORK = {"low": Decimal("1.3"), "base": Decimal("1.8"), "high": Decimal("2.5")}
SIZE_MULTIPLIER = {"S": Decimal("1"), "M": Decimal("2.5"), "L": Decimal("6"), "XL": Decimal("12")}


def _q(x: Optional[Decimal]) -> Optional[Decimal]:
    return None if x is None else x.quantize(CENT, rounding=ROUND_HALF_UP)


def _scale(s: Scenario, k: Decimal) -> Scenario:
    return Scenario(
        low=_q(None if s.low is None else s.low * k),
        base=_q(None if s.base is None else s.base * k),
        high=_q(None if s.high is None else s.high * k),
        unit=s.unit, warnings=list(s.warnings),
    )


def _mul(a: Scenario, b: Scenario) -> Scenario:
    def m(x, y):
        return None if x is None or y is None else _q(x * y)
    return Scenario(low=m(a.low, b.low), base=m(a.base, b.base), high=m(a.high, b.high),
                    unit=a.unit, warnings=list(dict.fromkeys(a.warnings + b.warnings)))


def _rate(profile, category: RateCategory):
    for r in profile.rates:
        if r.category == category:
            return r
    return None


# ------------------------------------------------------------------ build

def build_ledger(approach: ApproachProfile, features: list[FeatureItem],
                 rework: Optional[dict[str, Decimal]] = None,
                 founder_hours: Optional[Decimal] = None) -> BuildLedger:
    """Σ_tasks unit_cost × size multiplier, then × rework multiplier (assumed, labeled)."""
    rework = rework or DEFAULT_REWORK
    warnings: list[str] = []
    rate_ids: list[str] = []
    unit = "USD"

    units_total = sum((SIZE_MULTIPLIER[f.size_class] for f in features), Decimal("0"))

    base: Optional[Decimal] = None
    if approach.credits_per_task_class is not None:
        credits = sum((approach.credits_per_task_class.get(f.size_class, Decimal("0")) for f in features), Decimal("0"))
        r = _rate(approach, RateCategory.credits)
        if r is not None:
            rate_ids.append(r.source.record_id)
        if r is None or r.usd_per_unit is None:
            base = credits
            unit = "credits (USD conversion unverified)"
            warnings.append("Platform credit price not verified; range is denominated in credits.")
        else:
            base = credits * r.usd_per_unit
            if r.status != EvidenceStatus.verified:
                warnings.append(f"Credit rate status is {r.status.value}.")
    elif approach.tokens_per_task_class is not None:
        tokens = sum((approach.tokens_per_task_class.get(f.size_class, Decimal("0")) for f in features), Decimal("0"))
        rin, rout = _rate(approach, RateCategory.input_tokens), _rate(approach, RateCategory.output_tokens)
        for r in (rin, rout):
            if r is not None:
                rate_ids.append(r.source.record_id)
        if rin is None or rout is None or rin.usd_per_unit is None or rout.usd_per_unit is None:
            warnings.append("Token rates incomplete; build cost unknown for this approach.")
        else:
            # assume 40/60 input/output split for spec-level generation; disclosed
            blended = (rin.usd_per_unit * Decimal("0.4") + rout.usd_per_unit * Decimal("0.6")) / Decimal("1000000")
            base = tokens * blended
            warnings.append("Token split assumed 40% input / 60% output.")
    else:
        warnings.append("No per-task unit cost recorded for this approach; build cost unknown.")

    seat = _rate(approach, RateCategory.seat_month)
    if seat is not None and seat.usd_per_unit is not None:
        rate_ids.append(seat.source.record_id)
        warnings.append(f"Seat fee {seat.usd_per_unit}/month not included in per-task base; add per month of build.")

    base_s = Scenario(low=_q(base), base=_q(base), high=_q(base), unit=unit, warnings=warnings)
    rework_s = Scenario(low=rework["low"], base=rework["base"], high=rework["high"], unit="x",
                        warnings=["Rework multiplier is assumed; no project-specific evidence."])
    expected = _mul(base_s, rework_s)

    # Checkpoints at 25/50/75% of planned feature units (by size), cumulative expected spend
    checkpoints: list[Checkpoint] = []
    if units_total > 0 and expected.base is not None:
        cum = Decimal("0")
        thresholds = [Decimal("0.25"), Decimal("0.5"), Decimal("0.75")]
        marks = 0
        for f in features:
            cum += SIZE_MULTIPLIER[f.size_class]
            frac = cum / units_total
            while marks < len(thresholds) and frac >= thresholds[marks]:
                checkpoints.append(Checkpoint(
                    milestone=f"after {f.feature_id} ({int(thresholds[marks]*100)}% of planned work)",
                    cumulative_spend=_scale(expected, frac),
                    gate_question="Is a usable slice live, and is spend inside the base scenario? If not, stop and reassess approach.",
                ))
                marks += 1

    return BuildLedger(
        approach_id=approach.approach_id, base_build_cost=base_s, rework_multiplier=rework_s,
        expected_build_cost=expected, founder_time_hours=founder_hours,
        checkpoints=checkpoints, rate_ids=rate_ids,
    )


# -------------------------------------------------------------- operating

def operating_ledger(model: ModelProfile, usage: UsageAssumptions,
                     tokens_in_per_call: Decimal, tokens_out_per_call: Decimal,
                     extra_attempt_rate: Decimal = Decimal("0.1"),
                     other_monthly_cash: Decimal = Decimal("0"),
                     volume_multipliers=(Decimal("0.5"), Decimal("1"), Decimal("10"))) -> OperatingLedger:
    warnings: list[str] = []
    rin, rout = _rate(model, RateCategory.input_tokens), _rate(model, RateCategory.output_tokens)
    rate_ids = [r.source.record_id for r in (rin, rout) if r is not None]

    if usage.active_users is None or usage.workflows_per_user_month is None or usage.calls_per_workflow is None:
        return OperatingLedger(
            monthly_cash_cost=Scenario(low=None, base=None, high=None, warnings=["Usage assumptions missing; cost-only report not possible."]),
            per_workflow_cost=Scenario(low=None, base=None, high=None), rate_ids=rate_ids, cost_only=True,
        )
    if rin is None or rout is None or rin.usd_per_unit is None or rout.usd_per_unit is None:
        return OperatingLedger(
            monthly_cash_cost=Scenario(low=None, base=None, high=None, warnings=["Model rate unknown; cost unknown, not zero."]),
            per_workflow_cost=Scenario(low=None, base=None, high=None), rate_ids=rate_ids, cost_only=True,
        )

    per_call = (tokens_in_per_call * rin.usd_per_unit + tokens_out_per_call * rout.usd_per_unit) / Decimal("1000000")
    per_workflow = per_call * usage.calls_per_workflow * (Decimal("1") + extra_attempt_rate)
    base_calls = Decimal(usage.active_users) * usage.workflows_per_user_month
    costs = [_q(per_workflow * base_calls * m + other_monthly_cash) for m in volume_multipliers]
    monthly = Scenario(low=costs[0], base=costs[1], high=costs[2], warnings=warnings)
    pw = Scenario(low=_q(per_workflow), base=_q(per_workflow), high=_q(per_workflow))

    revenue = contribution = margin = None
    cost_only = usage.paying_fraction is None or usage.subscription_price_usd is None
    if not cost_only:
        revs = [_q(Decimal(usage.active_users) * m * usage.paying_fraction * usage.subscription_price_usd) for m in volume_multipliers]
        revenue = Scenario(low=revs[0], base=revs[1], high=revs[2])
        contribs = [_q(r - c) for r, c in zip(revs, costs)]
        contribution = Scenario(low=contribs[0], base=contribs[1], high=contribs[2])
        margins = [None if r == 0 else (c / r).quantize(Decimal("0.0001")) for r, c in zip(revs, contribs)]
        margin = Scenario(low=margins[0], base=margins[1], high=margins[2], unit="ratio",
                          warnings=["Margin undefined when revenue is zero."] if any(m is None for m in margins) else [])
    else:
        warnings.append("No revenue assumptions: cost-only report; no viability verdict.")

    return OperatingLedger(monthly_cash_cost=monthly, per_workflow_cost=pw, revenue=revenue,
                           contribution=contribution, margin=margin, rate_ids=rate_ids, cost_only=cost_only)
