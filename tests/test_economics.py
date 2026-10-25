from decimal import Decimal
from app.contracts import *
from app.economics import build_ledger, operating_ledger

def _src(i): return SourceRef(source_set="pricing_snapshots", record_id=i, version="t")

def test_unknown_credit_rate_stays_unknown_in_credits():
    a = ApproachProfile(approach_id="b", name="b", credits_per_task_class={"S": Decimal("10")},
        rates=[Rate(category=RateCategory.credits, unit="credit", usd_per_unit=None, status=EvidenceStatus.unverified, source=_src("r"))], source=_src("a"))
    led = build_ledger(a, [FeatureItem(feature_id="f", title="t", size_class="S")])
    assert led.base_build_cost.base == Decimal("10.00")
    assert "credits" in led.expected_build_cost.unit
    assert any("not verified" in w for w in led.expected_build_cost.warnings)

def test_rework_multiplier_applied_and_labeled_assumed():
    a = ApproachProfile(approach_id="t", name="t", tokens_per_task_class={"M": Decimal("1000000")},
        rates=[Rate(category=RateCategory.input_tokens, unit="1M", usd_per_unit=Decimal("1"), status=EvidenceStatus.verified, source=_src("i")),
               Rate(category=RateCategory.output_tokens, unit="1M", usd_per_unit=Decimal("1"), status=EvidenceStatus.verified, source=_src("o"))], source=_src("a"))
    led = build_ledger(a, [FeatureItem(feature_id="f", title="t", size_class="M")])
    assert led.base_build_cost.base == Decimal("1.00")
    assert led.expected_build_cost.base == Decimal("1.80")
    assert led.expected_build_cost.low == Decimal("1.30") and led.expected_build_cost.high == Decimal("2.50")
    assert "assumed" in led.rework_multiplier.warnings[0]

def test_checkpoints_cover_quarters():
    a = ApproachProfile(approach_id="t", name="t", tokens_per_task_class={"S": Decimal("100000")},
        rates=[Rate(category=RateCategory.input_tokens, unit="1M", usd_per_unit=Decimal("1"), status=EvidenceStatus.verified, source=_src("i")),
               Rate(category=RateCategory.output_tokens, unit="1M", usd_per_unit=Decimal("1"), status=EvidenceStatus.verified, source=_src("o"))], source=_src("a"))
    led = build_ledger(a, [FeatureItem(feature_id=f"f{i}", title="t", size_class="S") for i in range(4)])
    assert len(led.checkpoints) == 3

def test_empty_build_plan_is_unknown_not_zero():
    a = ApproachProfile(approach_id="b", name="b", credits_per_task_class={"S": Decimal("10")},
        rates=[Rate(category=RateCategory.credits, unit="credit", usd_per_unit=Decimal("1"), status=EvidenceStatus.verified, source=_src("r"))], source=_src("a"))
    led = build_ledger(a, [])
    assert led.base_build_cost.base is None and led.expected_build_cost.base is None and led.checkpoints == []

def test_operating_missing_usage_is_cost_only_not_zero():
    m = ModelProfile(model_id="m", provider_label="x", rates=[], source=_src("m"))
    led = operating_ledger(m, UsageAssumptions(), Decimal("1"), Decimal("1"))
    assert led.cost_only and led.monthly_cash_cost.base is None

def test_operating_margin_and_zero_revenue_guard():
    m = ModelProfile(model_id="m", provider_label="x", rates=[
        Rate(category=RateCategory.input_tokens, unit="1M", usd_per_unit=Decimal("1"), status=EvidenceStatus.verified, source=_src("i")),
        Rate(category=RateCategory.output_tokens, unit="1M", usd_per_unit=Decimal("1"), status=EvidenceStatus.verified, source=_src("o"))], source=_src("m"))
    u = UsageAssumptions(active_users=100, workflows_per_user_month=Decimal("10"), calls_per_workflow=Decimal("1"),
                         paying_fraction=Decimal("0.1"), subscription_price_usd=Decimal("10"), status=EvidenceStatus.verified)
    led = operating_ledger(m, u, Decimal("1000000"), Decimal("0"), extra_attempt_rate=Decimal("0"))
    assert led.monthly_cash_cost.base == Decimal("1000.00")   # 1000 calls × $1
    assert led.revenue.base == Decimal("100.00") and led.contribution.base == Decimal("-900.00")
    assert led.margin.base == Decimal("-9.0000")
    u0 = u.model_copy(update={"paying_fraction": Decimal("0")})
    assert operating_ledger(m, u0, Decimal("1"), Decimal("1")).margin.base is None
