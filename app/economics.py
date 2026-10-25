"""Deterministic economics. Decimal only. Unknown stays unknown.

Two ledgers, never summed:
  build_ledger      — AI-assisted development cost before launch (PRD §7.1)
  operating_ledger  — post-launch monthly cost and unit economics (PRD §7.2)
  stage_cost_table  — operating ledger by growth stage with levers and switch points (07 §5.1)
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Optional

from app.contracts import (
    ApproachProfile, BuildLedger, Checkpoint, CostLine, EvidenceStatus, FeatureItem, FeatureProfile, LeverLine,
    ModelProfile, OperatingLedger, OutputCapRerun, RateCategory, RubricResult, Scenario, Stage, StageCostRow,
    StageCostTable, SwitchPoint, TokenUsage, UsageAssumptions, default_stages,
)

CENT = Decimal("0.01")
MICRO = Decimal("0.000001")
M = Decimal("1000000")
MONTH_MINUTES = Decimal("730") * 60            # 730 hours per month
DEFAULT_RETRY_RATE = Decimal("0.1")            # assumed, labeled on the retries line
DEFAULT_SWITCH_THRESHOLD = Decimal("100")      # USD/month, founder-editable
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


# ------------------------------------------------- operating ledger by growth stage (07 §5.1)

def estimate_tokens(text: str) -> int:
    """4/3 rule: about four tokens per three words. An estimate, never a measurement."""
    words = len(text.split())
    return int((Decimal(words) * 4 / 3).to_integral_value(rounding=ROUND_CEILING))


def estimate_feature_tokens(feature: FeatureProfile) -> Optional[TokenUsage]:
    """Offline estimate: static prefix + example input; output from expected words. Reasoning stays unknown."""
    if feature.expected_output_words is None:
        return None
    return TokenUsage(input_tokens=feature.static_prefix_tokens + estimate_tokens(feature.example_input),
                      output_tokens=int((Decimal(feature.expected_output_words) * 4 / 3).to_integral_value(rounding=ROUND_CEILING)),
                      reasoning_tokens=None, basis="estimated", method="4/3 words rule")


def _usd(r) -> Optional[Decimal]:
    return None if r is None else r.usd_per_unit


def _sum_known(xs) -> Decimal:
    return sum((x for x in xs if x is not None), Decimal("0"))


def _caching(feature, model, tokens, calls_eff, rates) -> LeverLine:
    t = model.terms
    prefix = min(feature.static_prefix_tokens, tokens.input_tokens)
    p_in, p_read, p_write = rates["in"], _usd(rates["read"]), _usd(rates["write"])
    if t.cache_min_prefix_tokens is None or t.cache_ttl_minutes is None:
        return LeverLine(lever="prompt_caching", applies=False, reason="provider cache minimum or TTL unknown")
    if prefix < t.cache_min_prefix_tokens:
        return LeverLine(lever="prompt_caching", applies=False,
                         reason=f"static prefix {prefix} tokens is below provider minimum {t.cache_min_prefix_tokens}")
    windows = MONTH_MINUTES / t.cache_ttl_minutes
    if calls_eff <= windows:
        return LeverLine(lever="prompt_caching", applies=False,
                         reason=f"{_q(calls_eff)} calls/month do not repeat within the {t.cache_ttl_minutes}-minute TTL on average")
    if p_read is None or p_write is None:
        return LeverLine(lever="prompt_caching", applies=False, reason="eligible, but cache read or write rate unknown")
    writes = windows                      # one write per TTL window with traffic, spread uniformly
    reads = calls_eff - writes
    delta = Decimal(prefix) * (writes * p_write + reads * p_read - calls_eff * p_in) / M
    if delta >= 0:
        return LeverLine(lever="prompt_caching", applies=False, reason="eligible, but write premium exceeds read discount at this volume")
    return LeverLine(lever="prompt_caching", applies=True, monthly_delta_usd=_q(delta),
                     reason=f"{prefix}-token prefix: ~{_q(writes)} writes at write rate, ~{_q(reads)} reads at cache-read rate")


def _batch(feature, model, base_cost, caching_delta) -> LeverLine:
    t = model.terms
    if feature.mode != "background":
        return LeverLine(lever="batch_api", applies=False, reason="feature is interactive")
    if t.batch_available is not True:
        return LeverLine(lever="batch_api", applies=False,
                         reason="provider offers no batch API" if t.batch_available is False else "provider batch availability unknown")
    if t.batch_discount is None:
        return LeverLine(lever="batch_api", applies=False, reason="batch discount unknown")
    delta = -t.batch_discount * (base_cost + caching_delta)
    return LeverLine(lever="batch_api", applies=True, monthly_delta_usd=_q(delta),
                     reason=f"background feature; {int(t.batch_discount * 100)}% off input and output (after caching)")


def _output_cap(feature, model, tokens, calls_eff, p_out, cap: Optional[OutputCapRerun]) -> LeverLine:
    if cap is None or not cap.critic_flagged:
        return LeverLine(lever="output_cap", applies=False, reason="no critic finding that output exceeds what the rubric needs")
    if cap.rerun.basis != "measured":
        return LeverLine(lever="output_cap", applies=False, reason="capped re-run not measured")
    if cap.rerun.output_tokens >= tokens.output_tokens:
        return LeverLine(lever="output_cap", applies=False, reason="capped re-run was not shorter")
    delta = calls_eff * Decimal(cap.rerun.output_tokens - tokens.output_tokens) * p_out / M
    return LeverLine(lever="output_cap", applies=True, monthly_delta_usd=_q(delta),
                     reason=f"measured re-run with cap: {cap.rerun.output_tokens} vs {tokens.output_tokens} output tokens")


def _long_context(model, tokens, calls_eff, rates) -> LeverLine:
    thr = model.terms.long_context_threshold_tokens
    if thr is None or tokens.input_tokens <= thr:
        return LeverLine(lever="long_context_cliff", applies=False,
                         reason="no provider threshold recorded" if thr is None else f"input {tokens.input_tokens} <= threshold {thr}")
    lc_in, lc_out = _usd(rates["lc_in"]), _usd(rates["lc_out"])
    warn = f"WARNING: {tokens.basis} input {tokens.input_tokens} tokens exceeds {thr}; surcharge applies to the whole request"
    if lc_in is None or lc_out is None:
        return LeverLine(lever="long_context_cliff", applies=True, reason=warn + "; long-context rate unknown")
    out_tok = tokens.output_tokens + (tokens.reasoning_tokens or 0)
    delta = calls_eff * ((lc_in - rates["in"]) * tokens.input_tokens + (lc_out - rates["out"]) * out_tok) / M
    return LeverLine(lever="long_context_cliff", applies=True, monthly_delta_usd=_q(delta), reason=warn)


def stage_cost_row(feature: FeatureProfile, model: ModelProfile, stage: Stage, tokens: Optional[TokenUsage],
                   retry_rate: Decimal = DEFAULT_RETRY_RATE, output_cap: Optional[OutputCapRerun] = None) -> StageCostRow:
    """calls = users × uses × calls_per_use; cost_call = (in·p_in + out·p_out + reasoning·p_out)/1e6;
    retries shown as their own line; levers applied only when eligible, each as its own line."""
    r = {"in": _rate(model, RateCategory.input_tokens), "out": _rate(model, RateCategory.output_tokens),
         "read": _rate(model, RateCategory.cached_input_tokens), "write": _rate(model, RateCategory.cache_write_tokens),
         "lc_in": _rate(model, RateCategory.long_context_input_tokens), "lc_out": _rate(model, RateCategory.long_context_output_tokens)}
    rate_ids = [x.source.record_id for x in r.values() if x is not None]
    row = dict(feature_id=feature.feature_id, stage=stage.name, active_users=stage.active_users, model_id=model.model_id,
               tier=model.tier, rate_ids=rate_ids, token_basis=tokens.basis if tokens else "estimated")
    warnings: list[str] = []
    if any(x is not None and x.status != EvidenceStatus.verified for x in r.values()):
        warnings.append("Rates are not verified.")
    if tokens is not None and tokens.basis == "estimated":
        warnings.append(f"Tokens estimated ({tokens.method}), not measured.")

    calls = None if feature.uses_per_user_month is None else \
        Decimal(stage.active_users) * feature.uses_per_user_month * feature.calls_per_use
    p_in, p_out = _usd(r["in"]), _usd(r["out"])
    unknown = [why for cond, why in ((calls is None, "uses_per_user_month unknown"), (tokens is None, "tokens unknown"),
                                     (p_in is None or p_out is None, "input or output rate unknown")) if cond]
    if unknown:
        return StageCostRow(**row, calls_per_month=calls, cost_per_call_usd=None, lines=[], gross_monthly_usd=None,
                            levers=[], monthly_with_levers_usd=None, warnings=warnings + [f"Cost unknown, not zero: {'; '.join(unknown)}."])

    cin = calls * tokens.input_tokens * p_in / M
    cout = calls * tokens.output_tokens * p_out / M
    creason = None if tokens.reasoning_tokens is None else calls * tokens.reasoning_tokens * p_out / M
    lower_bound = creason is None
    if lower_bound:
        warnings.append("Reasoning tokens unknown; cost excludes them and is a lower bound.")
    base = _sum_known([cin, cout, creason])
    retries = base * retry_rate
    lines = [CostLine(name="input", monthly_usd=_q(cin)), CostLine(name="output", monthly_usd=_q(cout)),
             CostLine(name="reasoning", monthly_usd=_q(creason), note="unknown" if creason is None else ""),
             CostLine(name="retries", monthly_usd=_q(retries), note=f"retry_rate {retry_rate} (assumed)")]
    gross = base + retries
    calls_eff = calls * (1 + retry_rate)

    p = {"in": p_in, "out": p_out, **{k: r[k] for k in ("read", "write", "lc_in", "lc_out")}}
    caching = _caching(feature, model, tokens, calls_eff, p)
    cdelta = caching.monthly_delta_usd if caching.applies else Decimal("0")
    levers = [caching, _batch(feature, model, gross, cdelta),
              _output_cap(feature, model, tokens, calls_eff, p_out, output_cap), _long_context(model, tokens, calls_eff, p)]
    for lv in levers:
        if lv.applies and lv.monthly_delta_usd is None:
            lower_bound = True
            warnings.append(f"{lv.lever} applies but its amount is unknown.")
    with_levers = gross + _sum_known(lv.monthly_delta_usd for lv in levers if lv.applies)

    return StageCostRow(**row, calls_per_month=calls, cost_per_call_usd=(gross / calls).quantize(MICRO) if calls else None,
                        lines=lines, gross_monthly_usd=_q(gross), levers=levers, monthly_with_levers_usd=_q(with_levers),
                        lower_bound=lower_bound, warnings=warnings)


def _quality(feature: FeatureProfile, result: Optional[RubricResult]) -> tuple[Optional[str], bool, str]:
    """(score, passes, reason). Only live-inference results on the feature's full rubric count as evidence."""
    ids = {c.check_id for c in feature.rubric_checks}
    if result is None:
        return None, False, "quality not measured"
    score = f"{sum(result.checks.values())}/{len(result.checks)}"
    if result.execution_kind != "live_inference":
        return score, False, "rubric result is rule_policy, not measured quality"
    if not ids or set(result.checks) != ids:
        return score, False, "rubric result does not cover the feature's checks"
    failed = [c.check_id for c in feature.rubric_checks if c.critical and not result.checks[c.check_id]]
    if failed:
        return score, False, f"failed critical checks: {', '.join(failed)}"
    return score, True, "passed every critical check"


def detect_switch_points(feature: FeatureProfile, stages: list[Stage], rows: list[StageCostRow], models: list[ModelProfile],
                         rubric_results: Optional[list[RubricResult]] = None,
                         threshold_usd: Decimal = DEFAULT_SWITCH_THRESHOLD) -> tuple[list[SwitchPoint], list[SwitchPoint], list[str]]:
    """First stage at which moving the feature from frontier to a cheaper candidate lowers monthly cost by at least
    the threshold AND the cheaper model passed the same rubric checks. Cost-only crossovers are returned as pending."""
    frontier = next((m for m in models if m.tier == "frontier"), None)
    if frontier is None:
        return [], [], ["No frontier candidate; switch points not computed."]
    results = {(x.feature_id, x.model_id): x for x in (rubric_results or [])}
    by = {(x.model_id, x.stage): x for x in rows}
    qf, _, _ = _quality(feature, results.get((feature.feature_id, frontier.model_id)))
    frontier_measured = results.get((feature.feature_id, frontier.model_id))
    frontier_ok = frontier_measured is not None and frontier_measured.execution_kind == "live_inference"
    qualified, pending = [], []
    for m in models:
        if m.tier not in ("mid_tier", "open_source"):
            continue
        qt, passes, why = _quality(feature, results.get((feature.feature_id, m.model_id)))
        if passes and not frontier_ok:
            passes, why = False, "frontier quality not measured on the same checks"
        for s in sorted(stages, key=lambda s: s.active_users):
            a, b = by.get((frontier.model_id, s.name)), by.get((m.model_id, s.name))
            if a is None or b is None or a.monthly_with_levers_usd is None or b.monthly_with_levers_usd is None:
                continue
            diff = a.monthly_with_levers_usd - b.monthly_with_levers_usd
            if diff < threshold_usd:
                continue
            caveat = " Both costs are lower bounds." if (a.lower_bound or b.lower_bound) else ""
            basis = "estimated" if "estimated" in (a.token_basis, b.token_basis) else "measured"
            if passes:
                text = (f"From {s.name} ({s.active_users:,} users), {feature.feature_id} on {m.model_id} is projected to cost "
                        f"~${diff}/month less ({basis} tokens); measured quality {qt} checks vs {qf} on frontier. "
                        f"Test on your own data before switching.{caveat}")
            else:
                text = (f"From {s.name} ({s.active_users:,} users), {feature.feature_id} on {m.model_id} is projected to cost "
                        f"~${diff}/month less ({basis} tokens), but this is not a switch point: {why}.{caveat}")
            sp = SwitchPoint(feature_id=feature.feature_id, stage=s.name, active_users=s.active_users,
                             from_model=frontier.model_id, to_model=m.model_id, to_tier=m.tier, monthly_difference_usd=diff,
                             quality_to=qt, quality_from=qf, quality_qualified=passes, statement=text)
            (qualified if passes else pending).append(sp)
            break
    return qualified, pending, []


def stage_cost_table(feature: FeatureProfile, models: list[ModelProfile],
                     tokens_by_model: Optional[dict[str, TokenUsage]] = None, stages: Optional[list[Stage]] = None,
                     rubric_results: Optional[list[RubricResult]] = None,
                     threshold_usd: Decimal = DEFAULT_SWITCH_THRESHOLD, retry_rate: Decimal = DEFAULT_RETRY_RATE,
                     output_caps: Optional[list[OutputCapRerun]] = None) -> StageCostTable:
    """Per-stage, per-candidate monthly cost for one feature. Without measured tokens, the 4/3 estimate is used."""
    stages = stages or default_stages()
    tokens_by_model = tokens_by_model or {}
    caps = {(c.feature_id, c.model_id): c for c in (output_caps or [])}
    est = estimate_feature_tokens(feature)
    rows = [stage_cost_row(feature, m, s, tokens_by_model.get(m.model_id, est), retry_rate,
                           caps.get((feature.feature_id, m.model_id)))
            for m in models for s in stages]
    qualified, pending, warnings = detect_switch_points(feature, stages, rows, models, rubric_results, threshold_usd)
    if any(s.status != EvidenceStatus.verified for s in stages):
        warnings.append("Active users per stage are assumed and editable.")
    return StageCostTable(feature_id=feature.feature_id, stages=stages, rows=rows, threshold_usd=threshold_usd,
                          switch_points=qualified, pending_switch_points=pending, warnings=warnings)
