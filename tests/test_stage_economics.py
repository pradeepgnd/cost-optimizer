from decimal import Decimal
from app.contracts import *
from app.economics import (build_ledger, cost_per_call, detect_switch_points, estimate_feature_tokens, estimate_tokens,
                           operating_ledger, recommend_model_stack, stage_cost_row, stage_cost_table)

def _src(i): return SourceRef(source_set="pricing_snapshots", record_id=i, version="t")
def _r(cat, usd): return Rate(category=cat, unit="1M tokens", usd_per_unit=None if usd is None else Decimal(usd),
                              status=EvidenceStatus.verified, source=_src(cat.value))

def _model(mid="f", tier="frontier", p_in="10", p_out="20", read="1", write="12.5", lc_in="20", lc_out="30",
           batch=True, threshold=100000, audio_in="40", audio_out="80", audio=True):
    rates = [_r(RateCategory.input_tokens, p_in), _r(RateCategory.output_tokens, p_out)]
    for cat, v in ((RateCategory.cached_input_tokens, read), (RateCategory.cache_write_tokens, write),
                   (RateCategory.long_context_input_tokens, lc_in), (RateCategory.long_context_output_tokens, lc_out),
                   (RateCategory.audio_input_tokens, audio_in), (RateCategory.audio_output_tokens, audio_out)):
        if v is not None:
            rates.append(_r(cat, v))
    conv = AudioConversion(input_tokens_per_second=Decimal("10"), output_tokens_per_second=Decimal("20"),
                           source=_src("audio-conv")) if audio else None
    return ModelProfile(model_id=mid, provider_label="x", tier=tier, rates=rates, source=_src(mid), audio=conv,
                        terms=ModelPricingTerms(cache_min_prefix_tokens=1024, cache_ttl_minutes=Decimal("5"),
                                                batch_available=batch, batch_discount=Decimal("0.5"),
                                                long_context_threshold_tokens=threshold))

CHECKS = [RubricCheck(check_id="specific", description="plan is specific"),
          RubricCheck(check_id="no_invented_facts", description="no invented employer facts"),
          RubricCheck(check_id="tone", description="encouraging tone", critical=False)]

def _feature(mode="interactive", uses="10", calls="1", prefix=0, words=300):
    return FeatureProfile(feature_id="plan", description="generate a 90-day plan", example_input="PM to Program Manager",
                          mode=mode, uses_per_user_month=Decimal(uses), calls_per_use=Decimal(calls),
                          static_prefix_tokens=prefix, expected_output_words=words, rubric_checks=CHECKS)

def _tok(i=1000, o=500, reasoning=100, basis="measured"):
    return TokenUsage(input_tokens=i, output_tokens=o, reasoning_tokens=reasoning, basis=basis, method="api usage")

def _lever(row, name): return next(l for l in row.levers if l.lever == name)

STAGE = Stage(name="Launch", active_users=100)


# ---------------------------------------------------------------- stage math

def test_default_stages_are_assumed_and_editable():
    s = default_stages()
    assert [x.active_users for x in s] == [50, 500, 5000, 50000]
    assert all(x.status == EvidenceStatus.assumed for x in s)
    t = stage_cost_table(_feature(), [_model()], {"f": _tok()}, stages=[Stage(name="Pilot", active_users=7)])
    assert [r.stage for r in t.rows] == ["Pilot"]

def test_stage_math_calls_cost_per_call_and_retries_line():
    row = stage_cost_row(_feature(uses="10", calls="2"), _model(), STAGE, _tok())
    assert row.calls_per_month == Decimal("2000")                  # 100 users × 10 uses × 2 calls
    lines = {l.name: l.monthly_usd for l in row.lines}
    # reasoning (100 of the 500 output tokens) is a breakdown, not a second charge
    assert lines == {"input": Decimal("20.00"), "output": Decimal("20.00"), "reasoning": Decimal("4.00"), "retries": Decimal("4.00")}
    assert row.gross_monthly_usd == Decimal("44.00")
    assert row.cost_per_call_usd == Decimal("0.020000")         # cost_call excludes retries, per the 07 formula
    assert row.monthly_with_levers_usd == Decimal("44.00") and not row.lower_bound

def test_per_call_cost_keeps_full_precision():
    t = TokenUsage(input_tokens=1500, output_tokens=600, basis="measured", method="api usage")
    exact = Decimal("0.00156")                                     # 1500×0.40/1M + 600×1.60/1M
    assert cost_per_call(t, Decimal("0.40"), Decimal("1.60")) == exact
    m = _model(p_in="0.40", p_out="1.60")
    row = stage_cost_row(_feature(), m, STAGE, t)
    assert row.cost_per_call_usd == exact and row.cost_per_call_usd != Decimal("0.00")
    assert row.cost_per_call_usd.as_tuple().exponent <= -6        # shown with at least 6 decimal places
    assert row.gross_monthly_usd == Decimal("1.72")                 # 1,000 calls × 0.00156 × 1.1 = 1.716, rounded once
    u = UsageAssumptions(active_users=1, workflows_per_user_month=Decimal("1"), calls_per_workflow=Decimal("1"))
    led = operating_ledger(m, u, Decimal("1500"), Decimal("600"), extra_attempt_rate=Decimal("0"))
    assert led.per_workflow_cost.base == exact

def test_rounding_happens_once_at_display():
    # base 5,000 tokens × $1/M = $0.005; rounding it first would give 0.01 × 1.8 = 0.02, exact is 0.009 -> 0.01
    a = ApproachProfile(approach_id="t", name="t", tokens_per_task_class={"S": Decimal("5000")},
        rates=[_r(RateCategory.input_tokens, "1"), _r(RateCategory.output_tokens, "1")], source=_src("a"))
    assert build_ledger(a, [FeatureItem(feature_id="f", title="t", size_class="S")]).expected_build_cost.base == Decimal("0.01")

def test_output_tokens_billed_once_reasoning_is_breakdown():
    with_r = stage_cost_row(_feature(), _model(), STAGE, _tok(o=500, reasoning=300))
    without = stage_cost_row(_feature(), _model(), STAGE, _tok(o=500, reasoning=None))
    assert with_r.gross_monthly_usd == without.gross_monthly_usd == Decimal("22.00")   # 1,000 calls × $0.02 × 1.1
    reasoning = next(l for l in with_r.lines if l.name == "reasoning")
    assert reasoning.monthly_usd == Decimal("6.00") and not reasoning.billed
    billed = sum(l.monthly_usd for l in with_r.lines if l.billed)
    assert billed == with_r.gross_monthly_usd
    assert not without.lower_bound                                 # measured output already includes reasoning
    import pytest
    with pytest.raises(ValueError):
        _tok(o=500, reasoning=600)

def test_caching_and_batch_labeled_projected():
    row = stage_cost_row(_feature(mode="background"), _model(), STAGE, _tok())
    labels = {l.lever: l.label for l in row.levers}
    assert labels["prompt_caching"] == labels["batch_api"] == "projected (production setup)"
    assert labels["output_cap"] is None and labels["long_context_cliff"] is None

def _reuse(rate, distinct=None, mode="interactive"):
    return _feature(mode=mode).model_copy(update={"output_reuse_rate": None if rate is None else Decimal(rate),
                                                  "distinct_outputs": distinct})

def test_output_reuse_removes_the_share_and_is_labeled_projected():
    row = stage_cost_row(_reuse("0.9", 2000), _model(), STAGE, _tok(reasoning=0))
    r = _lever(row, "output_reuse")
    assert r.applies and r.label == "projected (production setup)"
    assert row.gross_monthly_usd == Decimal("22.00")                # 1,000 calls × $0.02 × 1.1
    assert r.monthly_delta_usd == Decimal("-19.80") and row.monthly_with_levers_usd == Decimal("2.20")

def test_one_time_cache_fill_is_shown_and_never_added_to_a_monthly_total():
    row = stage_cost_row(_reuse("0.9", 2000), _model(), STAGE, _tok(reasoning=0))
    assert _lever(row, "output_reuse").one_time_usd == Decimal("44.00")   # 2,000 outputs × $0.02 × 1.1
    assert row.monthly_with_levers_usd == Decimal("2.20")
    unknown = _lever(stage_cost_row(_reuse("0.9"), _model(), STAGE, _tok(reasoning=0)), "output_reuse")
    assert unknown.applies and unknown.one_time_usd is None and "distinct_outputs not given" in unknown.reason

def test_output_reuse_applies_after_the_other_levers():
    row = stage_cost_row(_reuse("0.9", mode="background"), _model(), STAGE, _tok(reasoning=0))
    assert _lever(row, "batch_api").monthly_delta_usd == Decimal("-11.00")
    assert _lever(row, "output_reuse").monthly_delta_usd == Decimal("-9.90")   # 0.9 × (22.00 − 11.00)
    assert row.monthly_with_levers_usd == Decimal("1.10")

def test_no_reuse_rate_means_no_reuse_line_effect():
    for f in (_feature(), _reuse("0")):
        lv = _lever(stage_cost_row(f, _model(), STAGE, _tok(reasoning=0)), "output_reuse")
        assert not lv.applies and lv.monthly_delta_usd is None and lv.one_time_usd is None

def test_reuse_inputs_are_validated():
    import pytest
    for upd in ({"output_reuse_rate": Decimal("1.2")}, {"output_reuse_rate": Decimal("-0.1")}, {"distinct_outputs": 0}):
        with pytest.raises(ValueError):
            FeatureProfile.model_validate({**_feature().model_dump(), **upd})

def test_audio_output_reuse_removes_audio_cost_too():
    f = _feature().model_copy(update={"modality": ["text", "audio_out"], "audio_seconds_per_use": Decimal("3"),
                                      "output_reuse_rate": Decimal("0.9"), "distinct_outputs": 2000})
    row = stage_cost_row(f, _model(), STAGE, _tok(reasoning=0))
    # 1,000 calls: text $20.00 + audio (3 s × 20 tok/s × $80/M = $0.0048 a call) $4.80, × 1.1 retries
    assert row.gross_monthly_usd == Decimal("27.28")
    assert row.monthly_with_levers_usd == Decimal("2.73")           # 10% of 27.28, rounded once

def test_unknown_usage_or_rate_stays_unknown():
    f = _feature().model_copy(update={"uses_per_user_month": None})
    assert stage_cost_row(f, _model(), STAGE, _tok()).gross_monthly_usd is None
    row = stage_cost_row(_feature(), _model(p_in=None), STAGE, _tok())
    assert row.gross_monthly_usd is None and any("not zero" in w for w in row.warnings)

def test_offline_tokens_use_four_thirds_rule_and_are_labeled_estimated():
    assert estimate_tokens("one two three") == 4
    assert estimate_tokens("four words here now") == 6             # ceil(16/3)
    t = estimate_feature_tokens(_feature(prefix=1200, words=300))
    assert t.basis == "estimated" and t.input_tokens == 1200 + 6 and t.output_tokens == 400
    assert t.reasoning_tokens is None
    row = stage_cost_row(_feature(), _model(), STAGE, t)
    assert row.token_basis == "estimated" and row.lower_bound
    assert any("estimated" in w for w in row.warnings) and any("lower bound" in w for w in row.warnings)
    assert estimate_feature_tokens(_feature(words=None)) is None


# ---------------------------------------------------------------- levers

def test_caching_applies_when_prefix_long_and_repeated_within_ttl():
    big = Stage(name="Traction", active_users=5000)                 # 50,000 calls, 55,000 with retries
    row = stage_cost_row(_feature(prefix=2000), _model(), big, _tok(i=3000))
    c = _lever(row, "prompt_caching")
    # 8,760 five-minute windows: writes 8,760 at 12.5, reads 46,240 at 1, instead of 55,000 at 10
    assert c.applies and c.monthly_delta_usd == Decimal("-788.52")
    assert row.monthly_with_levers_usd == row.gross_monthly_usd + c.monthly_delta_usd

def test_caching_not_eligible_below_minimum_or_without_repeats_or_rates():
    big = Stage(name="Traction", active_users=5000)
    assert not _lever(stage_cost_row(_feature(prefix=1000), _model(), big, _tok(i=3000)), "prompt_caching").applies
    low = stage_cost_row(_feature(prefix=2000), _model(), Stage(name="Prototype", active_users=50), _tok(i=3000))
    assert not _lever(low, "prompt_caching").applies and "TTL" in _lever(low, "prompt_caching").reason
    norate = stage_cost_row(_feature(prefix=2000), _model(read=None), big, _tok(i=3000))
    assert not _lever(norate, "prompt_caching").applies and "rate unknown" in _lever(norate, "prompt_caching").reason

def test_batch_only_for_background_features_with_provider_batch():
    bg = stage_cost_row(_feature(mode="background"), _model(), STAGE, _tok())
    b = _lever(bg, "batch_api")
    assert b.applies and b.monthly_delta_usd == -bg.gross_monthly_usd / 2
    assert not _lever(stage_cost_row(_feature(mode="interactive"), _model(), STAGE, _tok()), "batch_api").applies
    unk = _lever(stage_cost_row(_feature(mode="background"), _model(batch=None), STAGE, _tok()), "batch_api")
    assert not unk.applies and "unknown" in unk.reason

def test_output_cap_needs_critic_finding_and_measured_rerun():
    cap = OutputCapRerun(feature_id="plan", model_id="f", critic_flagged=True, rerun=_tok(o=300))
    row = stage_cost_row(_feature(uses="10", calls="2"), _model(), STAGE, _tok(), output_cap=cap)
    assert _lever(row, "output_cap").monthly_delta_usd == Decimal("-8.80")   # 2,200 calls × −200 tokens × $20/M
    est = cap.model_copy(update={"rerun": _tok(o=300, basis="estimated")})
    assert not _lever(stage_cost_row(_feature(), _model(), STAGE, _tok(), output_cap=est), "output_cap").applies
    unflagged = cap.model_copy(update={"critic_flagged": False})
    assert not _lever(stage_cost_row(_feature(), _model(), STAGE, _tok(), output_cap=unflagged), "output_cap").applies
    assert not _lever(stage_cost_row(_feature(), _model(), STAGE, _tok()), "output_cap").applies

def test_long_context_cliff_is_a_whole_request_surcharge_warning():
    row = stage_cost_row(_feature(uses="10", calls="2"), _model(), STAGE, _tok(i=150000))
    lc = _lever(row, "long_context_cliff")
    # 2,200 calls × ((20−10)×150,000 + (30−20)×500) / 1M; the 500 output tokens already include reasoning
    assert lc.applies and lc.monthly_delta_usd == Decimal("3311.00") and "WARNING" in lc.reason
    assert not _lever(stage_cost_row(_feature(), _model(), STAGE, _tok(i=1000)), "long_context_cliff").applies
    norate = stage_cost_row(_feature(), _model(lc_in=None), STAGE, _tok(i=150000))
    assert _lever(norate, "long_context_cliff").applies and _lever(norate, "long_context_cliff").monthly_delta_usd is None
    assert norate.lower_bound


# ---------------------------------------------------------------- switch points

MODELS = [_model("f", "frontier"), _model("cheap", "open_source", p_in="1", p_out="2")]
TOKENS = {"f": _tok(reasoning=0), "cheap": _tok(reasoning=0)}

def _results(cheap_checks, kind="live_inference"):
    return [RubricResult(feature_id="plan", model_id="f", checks={"specific": True, "no_invented_facts": True, "tone": True},
                         execution_kind=kind),
            RubricResult(feature_id="plan", model_id="cheap", checks=cheap_checks, execution_kind=kind)]

def test_switch_point_is_first_stage_meeting_threshold_with_passing_quality():
    # per-user difference $0.198/month: Prototype $9.90, Launch $99.00 (< $100), Traction $990.00
    t = stage_cost_table(_feature(), MODELS, TOKENS,
                         rubric_results=_results({"specific": True, "no_invented_facts": True, "tone": False}))
    assert [(s.stage, s.monthly_difference_usd) for s in t.switch_points] == [("Traction", Decimal("990.00"))]
    sp = t.switch_points[0]
    assert sp.quality_qualified and sp.quality_to == "2/3" and sp.quality_from == "3/3"
    assert "Test on your own data before switching." in sp.statement and "saved" not in sp.statement.lower()

def test_switch_threshold_is_editable():
    t = stage_cost_table(_feature(), MODELS, TOKENS, threshold_usd=Decimal("50"),
                         rubric_results=_results({"specific": True, "no_invented_facts": True, "tone": True}))
    assert t.switch_points[0].stage == "Launch"

def test_no_switch_point_when_cheaper_model_fails_a_critical_check():
    t = stage_cost_table(_feature(), MODELS, TOKENS,
                         rubric_results=_results({"specific": True, "no_invented_facts": False, "tone": True}))
    assert t.switch_points == []
    assert t.pending_switch_points[0].stage == "Traction" and "no_invented_facts" in t.pending_switch_points[0].statement

def test_rule_policy_or_missing_quality_is_not_switch_evidence():
    t = stage_cost_table(_feature(), MODELS, TOKENS,
                         rubric_results=_results({"specific": True, "no_invented_facts": True, "tone": True}, kind="rule_policy"))
    assert t.switch_points == [] and not t.pending_switch_points[0].quality_qualified
    assert stage_cost_table(_feature(), MODELS, TOKENS).switch_points == []

# ---------------------------------------------------------------- model stack

ALL_PASS = {"specific": True, "no_invented_facts": True, "tone": True}
NO_TONE = {"specific": True, "no_invented_facts": True, "tone": False}

def _stack(cheap_checks, frontier_checks=ALL_PASS, threshold="100", feature=None, models=MODELS):
    f = feature or _feature()
    res = [RubricResult(feature_id="plan", model_id="f", checks=frontier_checks, execution_kind="live_inference"),
           RubricResult(feature_id="plan", model_id="cheap", checks=cheap_checks, execution_kind="live_inference")]
    t = stage_cost_table(f, models, TOKENS, rubric_results=res, threshold_usd=Decimal(threshold))
    return {e.stage: e for e in recommend_model_stack(f, t, models, res)}

def test_stack_picks_cheapest_qualified_not_frontier_by_name():
    s = _stack(ALL_PASS)
    assert {e.model_id for e in s.values()} == {"cheap"} and s["Scale"].alternate_model_id == "f"

def test_stack_keeps_higher_quality_only_below_the_threshold():
    # frontier passes 3/3, cheap 2/3; difference is $9.90, $99.00, $990, $9,900 by stage against $100
    s = _stack(NO_TONE)
    assert [s[x].model_id for x in ("Prototype", "Launch", "Traction", "Scale")] == ["f", "f", "cheap", "cheap"]
    assert "kept over cheaper cheap" in s["Launch"].reason

def test_stack_never_picks_a_model_losing_money_per_use_when_a_qualified_one_does_not():
    # cost per use: frontier $0.022, cheap $0.0022; revenue $0.01 per use
    f = _feature().model_copy(update={"revenue_per_use": Decimal("0.01")})
    s = _stack(NO_TONE, feature=f)
    assert {e.model_id for e in s.values()} == {"cheap"} and "exceeds revenue per use" in s["Prototype"].reason

def test_stack_says_so_when_no_candidate_passes():
    s = _stack({"specific": False, "no_invented_facts": True, "tone": True},
               frontier_checks={"specific": True, "no_invented_facts": False, "tone": True})
    assert {e.status for e in s.values()} == {"no_candidate_passes"} and s["Scale"].model_id is None

def test_pending_critical_human_review_blocks_until_reviewed():
    s = _stack({"specific": True, "tone": True})          # no_invented_facts still pending
    assert {e.model_id for e in s.values()} == {"f"}

def test_no_frontier_means_no_switch_points():
    q, p, w = detect_switch_points(_feature(), default_stages(), [], [MODELS[1]])
    assert q == [] and p == [] and "No frontier" in w[0]


# ---------------------------------------------------------------- audio

def _audio(modality, seconds="60", calls="1"):
    return _feature(calls=calls).model_copy(update={"modality": modality,
                                                    "audio_seconds_per_use": None if seconds is None else Decimal(seconds)})

def test_audio_input_priced_from_per_second_conversion_and_labeled_estimated():
    row = stage_cost_row(_audio(["text", "audio_in"]), _model(), STAGE, _tok())
    lines = {l.name: l.monthly_usd for l in row.lines}
    assert lines["audio_input"] == Decimal("24.00")              # 1,000 calls × 60 s × 10 tok/s × $40/M
    assert "audio_output" not in lines
    assert row.gross_monthly_usd == Decimal("48.40")             # (10 + 10 + 24) × 1.1
    assert row.token_basis == "estimated" and any("per-second conversion" in w for w in row.warnings)
    assert "audio-conv" in row.rate_ids

def test_audio_output_and_seconds_split_across_calls_per_use():
    out = stage_cost_row(_audio(["text", "audio_out"]), _model(), STAGE, _tok())
    assert {l.name: l.monthly_usd for l in out.lines}["audio_output"] == Decimal("96.00")   # 60 s × 20 tok/s × $80/M
    split = stage_cost_row(_audio(["text", "audio_in"], calls="2"), _model(), STAGE, _tok())
    assert {l.name: l.monthly_usd for l in split.lines}["audio_input"] == Decimal("24.00")  # 2,000 calls × 30 s

def test_measured_audio_tokens_override_the_conversion():
    t = _tok().model_copy(update={"audio_input_tokens": 100})
    row = stage_cost_row(_audio(["text", "audio_in"]), _model(), STAGE, t)
    assert {l.name: l.monthly_usd for l in row.lines}["audio_input"] == Decimal("4.00")
    assert row.token_basis == "measured"

def test_audio_cost_unknown_without_conversion_seconds_or_rate():
    for row in (stage_cost_row(_audio(["text", "audio_in"]), _model(audio=False), STAGE, _tok()),
                stage_cost_row(_audio(["text", "audio_in"], seconds=None), _model(), STAGE, _tok()),
                stage_cost_row(_audio(["text", "audio_out"]), _model(audio_out=None), STAGE, _tok())):
        assert row.gross_monthly_usd is None and any("not zero" in w for w in row.warnings)

def test_text_only_feature_has_no_audio_lines():
    row = stage_cost_row(_feature(), _model(), STAGE, _tok())
    assert not {"audio_input", "audio_output"} & {l.name for l in row.lines}


# ---------------------------------------------------------------- revenue share

def _rev(usd): return _feature().model_copy(update={"revenue_per_use": Decimal(usd)})

def test_revenue_share_reported_per_use():
    row = stage_cost_row(_rev("0.05"), _model(), STAGE, _tok(reasoning=0))
    assert row.cost_per_use_usd == Decimal("0.022000")           # (1000×10 + 500×20)/1M × 1.1
    assert row.revenue_per_use_usd == Decimal("0.05") and row.revenue_share == Decimal("0.4400")

def test_high_risk_when_ai_cost_exceeds_revenue_per_use():
    t = stage_cost_table(_rev("0.01"), [_model()], {"f": _tok(reasoning=0)})
    assert len(t.risks) == 1
    r = t.risks[0]
    assert r.severity == "high" and r.cause_class == RiskCause.unit_economics and "220%" in r.description
    assert "ai_features:plan.revenue_per_use" in r.triggered_by

def test_no_revenue_risk_below_100_percent_or_without_revenue():
    assert stage_cost_table(_rev("0.05"), [_model()], {"f": _tok(reasoning=0)}).risks == []
    t = stage_cost_table(_feature(), [_model()], {"f": _tok(reasoning=0)})
    assert t.risks == [] and all(r.revenue_share is None for r in t.rows)
