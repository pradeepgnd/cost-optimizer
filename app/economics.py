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
    ModelProfile, ModelStackEntry, OperatingLedger, OutputCapRerun, RateCategory, Risk, RiskCause, RubricResult, Scenario, Stage,
    StageCostRow, StageCostTable, SwitchPoint, TokenUsage, UsageAssumptions, default_stages,
)

CENT = Decimal("0.01")
MICRO = Decimal("0.000001")                   # per-call display: at least 6 decimal places
DISPLAY_FINE = Decimal("1E-10")                # per-call display ceiling for non-terminating quotients
PROJECTED = "projected (production setup)"     # caching and batch are not measured in our runs (07 §5.1)
M = Decimal("1000000")
MONTH_MINUTES = Decimal("730") * 60            # 730 hours per month
DEFAULT_RETRY_RATE = Decimal("0.1")            # assumed, labeled on the retries line
DEFAULT_SWITCH_THRESHOLD = Decimal("100")      # USD/month, founder-editable
AUDIO_RATE = {"audio_in": RateCategory.audio_input_tokens, "audio_out": RateCategory.audio_output_tokens}
AUDIO_FIELD = {"audio_in": "audio_input_tokens", "audio_out": "audio_output_tokens"}
AUDIO_TPS = {"audio_in": "input_tokens_per_second", "audio_out": "output_tokens_per_second"}
AUDIO_LINE = {"audio_in": "audio_input", "audio_out": "audio_output"}
DEFAULT_REWORK = {"low": Decimal("1.3"), "base": Decimal("1.8"), "high": Decimal("2.5")}
SIZE_MULTIPLIER = {"S": Decimal("1"), "M": Decimal("2.5"), "L": Decimal("6"), "XL": Decimal("12")}


def _q(x: Optional[Decimal]) -> Optional[Decimal]:
    return None if x is None else x.quantize(CENT, rounding=ROUND_HALF_UP)


def _display(exact: dict[str, Optional[Decimal]], k: Decimal = Decimal("1"), **kw) -> Scenario:
    """Round an exact low/base/high triple (optionally scaled) to cents, only at the point of display."""
    return Scenario(**{s: _q(None if v is None else v * k) for s, v in exact.items()}, **kw)


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
    if not features:
        warnings.append("No build features listed; build cost unknown, not zero.")
    elif approach.credits_per_task_class is not None:
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
    exact = {s: None if base is None else base * rework[s] for s in ("low", "base", "high")}
    expected = _display(exact, unit=unit, warnings=list(dict.fromkeys(base_s.warnings + rework_s.warnings)))

    # Checkpoints at 25/50/75% of planned feature units (by size), cumulative expected spend
    checkpoints: list[Checkpoint] = []
    if units_total > 0 and base is not None:
        cum = Decimal("0")
        thresholds = [Decimal("0.25"), Decimal("0.5"), Decimal("0.75")]
        marks = 0
        for f in features:
            cum += SIZE_MULTIPLIER[f.size_class]
            frac = cum / units_total
            while marks < len(thresholds) and frac >= thresholds[marks]:
                checkpoints.append(Checkpoint(
                    milestone=f"after {f.feature_id} ({int(thresholds[marks]*100)}% of planned work)",
                    cumulative_spend=_display(exact, frac, unit=expected.unit, warnings=list(expected.warnings)),
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

    # Exact Decimal throughout; per-workflow keeps >= 6 decimal places, monthly figures round to cents for display.
    per_call = (tokens_in_per_call * rin.usd_per_unit + tokens_out_per_call * rout.usd_per_unit) / M
    per_workflow = per_call * usage.calls_per_workflow * (Decimal("1") + extra_attempt_rate)
    base_calls = Decimal(usage.active_users) * usage.workflows_per_user_month
    costs = [per_workflow * base_calls * m + other_monthly_cash for m in volume_multipliers]
    monthly = Scenario(low=_q(costs[0]), base=_q(costs[1]), high=_q(costs[2]), warnings=warnings)
    pw = Scenario(low=_per_call(per_workflow), base=_per_call(per_workflow), high=_per_call(per_workflow))

    revenue = contribution = margin = None
    cost_only = usage.paying_fraction is None or usage.subscription_price_usd is None
    if not cost_only:
        revs = [Decimal(usage.active_users) * m * usage.paying_fraction * usage.subscription_price_usd for m in volume_multipliers]
        revenue = Scenario(low=_q(revs[0]), base=_q(revs[1]), high=_q(revs[2]))
        contribs = [r - c for r, c in zip(revs, costs)]
        contribution = Scenario(low=_q(contribs[0]), base=_q(contribs[1]), high=_q(contribs[2]))
        margins = [None if r == 0 else (c / r).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) for r, c in zip(revs, contribs)]
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


def _per_call(x: Optional[Decimal]) -> Optional[Decimal]:
    """Display form of a per-call or per-use cost: at least 6 decimal places, never rounded to cents."""
    if x is None:
        return None
    x = x.normalize()
    if x.as_tuple().exponent >= -6:
        return x.quantize(MICRO)
    return x.quantize(DISPLAY_FINE, rounding=ROUND_HALF_UP).normalize()


def cost_per_call(tokens: TokenUsage, p_in: Decimal, p_out: Decimal) -> Decimal:
    """Exact text cost of one call. Output tokens already include reasoning tokens, so reasoning is not added."""
    return (tokens.input_tokens * p_in + tokens.output_tokens * p_out) / M


# Each lever returns (display line, exact delta). Exact deltas feed totals; only the line is rounded.

def _lever(lever, reason, delta=None, applies=True):
    return LeverLine(lever=lever, applies=applies, reason=reason, monthly_delta_usd=_q(delta),
                     label=PROJECTED if lever in ("prompt_caching", "batch_api") else None), (delta if applies else None)


def _caching(feature, model, tokens, calls_eff, rates):
    t = model.terms
    prefix = min(feature.static_prefix_tokens, tokens.input_tokens)
    p_in, p_read, p_write = rates["in"], _usd(rates["read"]), _usd(rates["write"])
    no = lambda why: _lever("prompt_caching", why, applies=False)
    if t.cache_min_prefix_tokens is None or t.cache_ttl_minutes is None:
        return no("provider cache minimum or TTL unknown")
    if prefix < t.cache_min_prefix_tokens:
        return no(f"static prefix {prefix} tokens is below provider minimum {t.cache_min_prefix_tokens}")
    windows = MONTH_MINUTES / t.cache_ttl_minutes
    if calls_eff <= windows:
        return no(f"{_q(calls_eff)} calls/month do not repeat within the {t.cache_ttl_minutes}-minute TTL on average")
    if p_read is None or p_write is None:
        return no("eligible, but cache read or write rate unknown")
    writes = windows                      # one write per TTL window with traffic, spread uniformly
    reads = calls_eff - writes
    delta = Decimal(prefix) * (writes * p_write + reads * p_read - calls_eff * p_in) / M
    if delta >= 0:
        return no("eligible, but write premium exceeds read discount at this volume")
    return _lever("prompt_caching", f"{prefix}-token prefix: ~{_q(writes)} writes at write rate, "
                                    f"~{_q(reads)} reads at cache-read rate", delta)


def _batch(feature, model, base_cost, caching_delta):
    t = model.terms
    no = lambda why: _lever("batch_api", why, applies=False)
    if feature.mode != "background":
        return no("feature is interactive")
    if t.batch_available is not True:
        return no("provider offers no batch API" if t.batch_available is False else "provider batch availability unknown")
    if t.batch_discount is None:
        return no("batch discount unknown")
    return _lever("batch_api", f"background feature; {int(t.batch_discount * 100)}% off input and output (after caching)",
                  -t.batch_discount * (base_cost + caching_delta))


def _output_cap(feature, model, tokens, calls_eff, p_out, cap: Optional[OutputCapRerun]):
    no = lambda why: _lever("output_cap", why, applies=False)
    if cap is None or not cap.critic_flagged:
        return no("no critic finding that output exceeds what the rubric needs")
    if cap.rerun.basis != "measured":
        return no("capped re-run not measured")
    if cap.rerun.output_tokens >= tokens.output_tokens:
        return no("capped re-run was not shorter")
    return _lever("output_cap", f"measured re-run with cap: {cap.rerun.output_tokens} vs {tokens.output_tokens} output tokens",
                  calls_eff * Decimal(cap.rerun.output_tokens - tokens.output_tokens) * p_out / M)


def _long_context(model, tokens, calls_eff, rates):
    thr = model.terms.long_context_threshold_tokens
    if thr is None or tokens.input_tokens <= thr:
        return _lever("long_context_cliff", "no provider threshold recorded" if thr is None
                      else f"input {tokens.input_tokens} <= threshold {thr}", applies=False)
    lc_in, lc_out = _usd(rates["lc_in"]), _usd(rates["lc_out"])
    warn = f"WARNING: {tokens.basis} input {tokens.input_tokens} tokens exceeds {thr}; surcharge applies to the whole request"
    if lc_in is None or lc_out is None:
        return _lever("long_context_cliff", warn + "; long-context rate unknown")
    # output tokens already include reasoning tokens
    return _lever("long_context_cliff", warn, calls_eff * ((lc_in - rates["in"]) * tokens.input_tokens
                                                          + (lc_out - rates["out"]) * tokens.output_tokens) / M)


def stage_cost_row(feature: FeatureProfile, model: ModelProfile, stage: Stage, tokens: Optional[TokenUsage],
                   retry_rate: Decimal = DEFAULT_RETRY_RATE, output_cap: Optional[OutputCapRerun] = None) -> StageCostRow:
    """calls = users × uses × calls_per_use; cost_call = (in·p_in + out·p_out)/1e6, where output already includes
    reasoning; retries shown as their own line; levers applied only when eligible, each as its own line.
    Full Decimal precision throughout; values are rounded only when placed on the row."""
    r = {"in": _rate(model, RateCategory.input_tokens), "out": _rate(model, RateCategory.output_tokens),
         "read": _rate(model, RateCategory.cached_input_tokens), "write": _rate(model, RateCategory.cache_write_tokens),
         "lc_in": _rate(model, RateCategory.long_context_input_tokens), "lc_out": _rate(model, RateCategory.long_context_output_tokens)}
    audio_dirs = [d for d in ("audio_in", "audio_out") if d in feature.modality]
    r.update({d: _rate(model, AUDIO_RATE[d]) for d in audio_dirs})
    rate_ids = [x.source.record_id for x in r.values() if x is not None]
    if audio_dirs and model.audio is not None and model.audio.source is not None:
        rate_ids.append(model.audio.source.record_id)
    row = dict(feature_id=feature.feature_id, stage=stage.name, active_users=stage.active_users, model_id=model.model_id,
               tier=model.tier, rate_ids=rate_ids, token_basis=tokens.basis if tokens else "estimated",
               revenue_per_use_usd=feature.revenue_per_use)
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
    audio_tokens: dict[str, Decimal] = {}
    for d in audio_dirs:
        n, why = _audio_tokens_per_call(feature, model, tokens, d)
        if why:
            unknown.append(why)
        elif _usd(r[d]) is None:
            unknown.append(f"{d} rate unknown")
        else:
            audio_tokens[d] = n
            if tokens is None or getattr(tokens, AUDIO_FIELD[d]) is None:
                row["token_basis"] = "estimated"
                warnings.append(f"{d} tokens estimated from per-second conversion ({model.audio.status.value}), not measured.")
    if unknown:
        return StageCostRow(**row, calls_per_month=calls, cost_per_call_usd=None, lines=[], gross_monthly_usd=None,
                            levers=[], monthly_with_levers_usd=None, warnings=warnings + [f"Cost unknown, not zero: {'; '.join(unknown)}."])

    call = cost_per_call(tokens, p_in, p_out) + sum((n * _usd(r[d]) / M for d, n in audio_tokens.items()), Decimal("0"))
    cin = calls * tokens.input_tokens * p_in / M
    cout = calls * tokens.output_tokens * p_out / M
    creason = None if tokens.reasoning_tokens is None else calls * tokens.reasoning_tokens * p_out / M
    caudio = {d: calls * n * _usd(r[d]) / M for d, n in audio_tokens.items()}
    # Word-based estimates cannot see hidden reasoning; measured output tokens already include it.
    lower_bound = tokens.basis == "estimated"
    if lower_bound:
        warnings.append("Estimated output tokens exclude any hidden reasoning tokens; cost is a lower bound.")
    base = calls * call
    retries = base * retry_rate
    lines = [CostLine(name="input", monthly_usd=_q(cin)), CostLine(name="output", monthly_usd=_q(cout)),
             CostLine(name="reasoning", monthly_usd=_q(creason), billed=False,
                      note="unknown" if creason is None else "breakdown of output; already billed as output, not added")]
    lines += [CostLine(name=AUDIO_LINE[d], monthly_usd=_q(c), note=f"{_q(audio_tokens[d])} audio tokens per call")
              for d, c in caudio.items()]
    lines.append(CostLine(name="retries", monthly_usd=_q(retries), note=f"retry_rate {retry_rate} (assumed)"))
    gross = base + retries
    calls_eff = calls * (1 + retry_rate)

    p = {"in": p_in, "out": p_out, **{k: r[k] for k in ("read", "write", "lc_in", "lc_out")}}
    caching, cdelta = _caching(feature, model, tokens, calls_eff, p)
    pairs = [(caching, cdelta), _batch(feature, model, gross, cdelta or Decimal("0")),
             _output_cap(feature, model, tokens, calls_eff, p_out, output_cap), _long_context(model, tokens, calls_eff, p)]
    for lv, _ in pairs:
        if lv.applies and lv.monthly_delta_usd is None:
            lower_bound = True
            warnings.append(f"{lv.lever} applies but its amount is unknown.")
    with_levers = gross + _sum_known(d for _, d in pairs)

    uses = Decimal(stage.active_users) * feature.uses_per_user_month
    per_use = with_levers / uses if uses else None
    share = None
    if per_use is not None and feature.revenue_per_use is not None:
        if feature.revenue_per_use > 0:
            share = per_use / feature.revenue_per_use
            if share > 1 >= share.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP):
                warnings.append("Revenue share is just above 100%; the rounded figure hides it.")
        else:
            warnings.append("revenue_per_use is not positive; revenue share undefined.")
        if share is not None and lower_bound and share <= 1:
            warnings.append("Revenue share is a lower bound; unknown cost components are excluded.")

    out = StageCostRow(**row, calls_per_month=calls, cost_per_call_usd=_per_call(call), lines=lines,
                       gross_monthly_usd=_q(gross), levers=[lv for lv, _ in pairs], monthly_with_levers_usd=_q(with_levers),
                       cost_per_use_usd=_per_call(per_use),
                       revenue_share=None if share is None else share.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                       lower_bound=lower_bound, warnings=warnings)
    out._exact_with_levers, out._exact_share = with_levers, share
    return out


def _exact(row: StageCostRow, name: str):
    """Exact value kept on the row for downstream rules; falls back to the display value for rows built elsewhere."""
    v = getattr(row, f"_exact_{name}")
    return v if v is not None else getattr(row, {"with_levers": "monthly_with_levers_usd", "share": "revenue_share"}[name])


def _audio_tokens_per_call(feature, model, tokens, direction) -> tuple[Optional[Decimal], Optional[str]]:
    """Measured audio tokens when the usage fields carry them; otherwise seconds × per-second conversion."""
    measured = None if tokens is None else getattr(tokens, AUDIO_FIELD[direction])
    if measured is not None:
        return Decimal(measured), None
    if feature.audio_seconds_per_use is None:
        return None, "audio_seconds_per_use unknown"
    tps = None if model.audio is None else getattr(model.audio, AUDIO_TPS[direction])
    if tps is None:
        return None, f"{direction} per-second conversion unknown"
    return feature.audio_seconds_per_use / feature.calls_per_use * tps, None


def revenue_share_risks(feature: FeatureProfile, rows: list[StageCostRow]) -> list[Risk]:
    """High-severity risk when AI cost per use exceeds revenue per use, one per candidate model."""
    risks: list[Risk] = []
    for model_id in dict.fromkeys(r.model_id for r in rows):
        over = [r for r in rows if r.model_id == model_id and _exact(r, "share") is not None and _exact(r, "share") > 1]
        if not over:
            continue
        worst = max(over, key=lambda r: _exact(r, "share"))
        risks.append(Risk(
            description=f"{feature.feature_id} on {model_id}: AI cost per use ${worst.cost_per_use_usd} is "
                        f"{(_exact(worst, 'share') * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)}% of revenue per use ${feature.revenue_per_use} "
                        f"at {', '.join(r.stage for r in over)}; each use loses money before any other cost.",
            cause_class=RiskCause.unit_economics, severity="high",
            triggered_by=[f"ai_features:{feature.feature_id}.revenue_per_use", *worst.rate_ids]))
    return risks


def _quality(feature: FeatureProfile, result: Optional[RubricResult]) -> tuple[Optional[str], bool, str]:
    """(score, passes, reason). Only live-inference results count, and every critical check needs a result
    (machine or human review) and must pass. Non-critical checks may fail or stay pending."""
    critical = [c.check_id for c in feature.rubric_checks if c.critical]
    if result is None:
        return None, False, "quality not measured"
    score = f"{sum(result.checks.values())}/{len(feature.rubric_checks) or len(result.checks)}"
    if result.execution_kind != "live_inference":
        return score, False, "rubric result is rule_policy, not measured quality"
    if not critical:
        return score, False, "the feature has no critical rubric checks"
    missing = [c for c in critical if c not in result.checks]
    if missing:
        return score, False, f"critical checks pending human review or not run: {', '.join(missing)}"
    failed = [c for c in critical if not result.checks[c]]
    if failed:
        return score, False, f"failed critical checks: {', '.join(failed)}"
    return score, True, "passed every critical check"


def recommend_model_stack(feature: FeatureProfile, table: StageCostTable, models: list[ModelProfile],
                          rubric_results: Optional[list[RubricResult]] = None,
                          threshold_usd: Optional[Decimal] = None) -> list[ModelStackEntry]:
    """Per stage: the cheapest candidate that passed every critical check. A higher-quality qualified candidate is
    kept only when it costs less than the threshold more. A candidate whose AI cost per use exceeds revenue per use
    is never recommended while a qualified alternative within revenue exists. No frontier-by-name baseline."""
    threshold_usd = table.threshold_usd if threshold_usd is None else threshold_usd
    results = {(r.feature_id, r.model_id): r for r in (rubric_results or [])}
    quality = {m.model_id: _quality(feature, results.get((feature.feature_id, m.model_id))) for m in models}
    passed = {mid: sum(results[(feature.feature_id, mid)].checks.values()) if (feature.feature_id, mid) in results else 0
              for mid in quality}
    out: list[ModelStackEntry] = []
    for s in sorted(table.stages, key=lambda s: s.active_users):
        rows = {r.model_id: r for r in table.rows if r.stage == s.name}
        cost = {mid: _exact(r, "with_levers") for mid, r in rows.items()}
        ok = [m.model_id for m in models if quality[m.model_id][1] and cost.get(m.model_id) is not None]
        if not ok:
            why = "; ".join(f"{m.model_id}: {quality[m.model_id][2] if not quality[m.model_id][1] else 'cost unknown'}"
                            for m in models)
            out.append(ModelStackEntry(feature_id=feature.feature_id, stage=s.name, status="no_candidate_passes",
                                       reason=f"No candidate passed every critical check with a known cost ({why})."))
            continue
        within = [mid for mid in ok if _exact(rows[mid], "share") is None or _exact(rows[mid], "share") <= 1]
        pool = within or ok
        by_cost = sorted(pool, key=lambda mid: cost[mid])
        cheapest = by_cost[0]
        better = [mid for mid in pool if passed[mid] > passed[cheapest] and cost[mid] - cost[cheapest] < threshold_usd]
        pick = max(better, key=lambda mid: (passed[mid], -cost[mid])) if better else cheapest
        alternate = next((mid for mid in by_cost if mid != pick), None)
        reason = (f"{pick} passed every critical check ({quality[pick][0]}) at ~${_q(cost[pick])}/month"
                  + (f"; kept over cheaper {cheapest} (${_q(cost[cheapest])}) because it passed more checks and the "
                     f"difference is below the ${threshold_usd} threshold" if pick != cheapest
                     else "; cheapest qualified candidate"))
        excluded = [mid for mid in ok if mid not in pool]
        if excluded:
            reason += f"; excluded {', '.join(excluded)}: AI cost per use exceeds revenue per use"
        if not within:
            reason += "; every qualified candidate's AI cost per use exceeds revenue per use"
        if rows[pick].lower_bound:
            reason += "; cost is a lower bound"
        out.append(ModelStackEntry(feature_id=feature.feature_id, stage=s.name, status="recommended", model_id=pick,
                                   alternate_model_id=alternate, monthly_usd=_q(cost[pick]), reason=reason + "."))
    return out


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
            if a is None or b is None or _exact(a, "with_levers") is None or _exact(b, "with_levers") is None:
                continue
            exact_diff = _exact(a, "with_levers") - _exact(b, "with_levers")
            if exact_diff < threshold_usd:
                continue
            diff = _q(exact_diff)
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
                          switch_points=qualified, pending_switch_points=pending,
                          risks=revenue_share_risks(feature, rows), warnings=warnings)
