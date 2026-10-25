from decimal import Decimal
from app.contracts import *
from app.economics import detect_switch_points, estimate_feature_tokens, estimate_tokens, stage_cost_row, stage_cost_table

def _src(i): return SourceRef(source_set="pricing_snapshots", record_id=i, version="t")
def _r(cat, usd): return Rate(category=cat, unit="1M tokens", usd_per_unit=None if usd is None else Decimal(usd),
                              status=EvidenceStatus.verified, source=_src(cat.value))

def _model(mid="f", tier="frontier", p_in="10", p_out="20", read="1", write="12.5", lc_in="20", lc_out="30",
           batch=True, threshold=100000):
    rates = [_r(RateCategory.input_tokens, p_in), _r(RateCategory.output_tokens, p_out)]
    for cat, v in ((RateCategory.cached_input_tokens, read), (RateCategory.cache_write_tokens, write),
                   (RateCategory.long_context_input_tokens, lc_in), (RateCategory.long_context_output_tokens, lc_out)):
        if v is not None:
            rates.append(_r(cat, v))
    return ModelProfile(model_id=mid, provider_label="x", tier=tier, rates=rates, source=_src(mid),
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
    assert lines == {"input": Decimal("20.00"), "output": Decimal("20.00"), "reasoning": Decimal("4.00"), "retries": Decimal("4.40")}
    assert row.gross_monthly_usd == Decimal("48.40")
    assert row.cost_per_call_usd == Decimal("0.024200")
    assert row.monthly_with_levers_usd == Decimal("48.40") and not row.lower_bound

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
    # 2,200 calls × ((20−10)×150,000 + (30−20)×600) / 1M
    assert lc.applies and lc.monthly_delta_usd == Decimal("3313.20") and "WARNING" in lc.reason
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

def test_no_frontier_means_no_switch_points():
    q, p, w = detect_switch_points(_feature(), default_stages(), [], [MODELS[1]])
    assert q == [] and p == [] and "No frontier" in w[0]
