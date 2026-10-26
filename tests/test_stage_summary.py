"""R9 (plan Step 12): one monthly AI total per stage, revenue, AI contribution and budget fit. Offline arithmetic."""
from decimal import Decimal

import pytest

from app.contracts import (FeatureProfile, ModelStackEntry, OpenRouterProjectionTable, Stage, StageCostRow,
                           StageCostTable, UsageAssumptions)
from app.economics import stage_totals

STAGES = [Stage(name="Launch", active_users=500), Stage(name="Scale", active_users=50000)]
FEATURES = [FeatureProfile(feature_id=f, description="d", example_input="x", mode="interactive") for f in ("a", "b")]


def row(fid, model, stage, cost, lower=False):
    return StageCostRow(feature_id=fid, stage=stage, active_users=1, model_id=model, calls_per_month=None,
                        cost_per_call_usd=None, token_basis="measured", lines=[], gross_monthly_usd=cost, levers=[],
                        monthly_with_levers_usd=None if cost is None else Decimal(cost), lower_bound=lower)


def table(fid, rows):
    return StageCostTable(feature_id=fid, stages=STAGES, rows=rows, threshold_usd=Decimal("100"))


COSTS = {("a", "big"): {"Launch": "15.00", "Scale": "1500.00"}, ("a", "small"): {"Launch": "1.00", "Scale": "100.00"},
         ("b", "big"): {"Launch": "5.00", "Scale": "500.00"}, ("b", "small"): {"Launch": "2.00", "Scale": "200.00"}}


def tables(costs=COSTS, lower=False):
    return [table(fid, [row(f, m, s, c, lower) for (f, m), by in costs.items() if f == fid for s, c in by.items()])
            for fid in ("a", "b")]


def pick(totals, scenario, stage, model=None, scope="actual_route"):
    return next(t for t in totals if t.scenario == scenario and t.stage == stage and t.model_id == model
                and t.pricing_scope == scope)


def test_known_feature_costs_add_up_per_stage_and_scenario():
    totals = stage_totals(FEATURES, STAGES, tables(), [], [])
    cheap = pick(totals, "cheapest_per_feature", "Scale")
    assert cheap.monthly_usd == Decimal("300.00") and cheap.feature_models == {"a": "small", "b": "small"}
    assert cheap.complete and not cheap.lower_bound and "quality not checked" in cheap.note
    assert pick(totals, "single_model", "Scale", "big").monthly_usd == Decimal("2000.00")
    assert pick(totals, "single_model", "Launch", "small").monthly_usd == Decimal("3.00")


def test_recommended_total_uses_only_qualified_models_and_stays_unknown_without_them():
    totals = stage_totals(FEATURES, STAGES, tables(), [], [])
    rec = pick(totals, "recommended", "Scale")
    assert rec.monthly_usd is None and not rec.complete and "no model is qualified" in rec.note
    stack = [ModelStackEntry(feature_id="a", stage="Scale", status="recommended", model_id="big", reason="r")]
    partial = pick(stage_totals(FEATURES, STAGES, tables(), [], stack), "recommended", "Scale")
    assert partial.monthly_usd == Decimal("1500.00") and not partial.complete and partial.lower_bound
    assert partial.feature_costs == {"a": Decimal("1500.00"), "b": None} and "cost unknown for b" in partial.note


def test_unknown_feature_cost_prevents_a_complete_total_and_is_never_zero():
    costs = {**COSTS, ("b", "small"): {"Launch": None, "Scale": None}}
    total = pick(stage_totals(FEATURES, STAGES, tables(costs), [], []), "single_model", "Scale", "small")
    assert total.monthly_usd == Decimal("100.00") and not total.complete and total.lower_bound
    assert total.feature_costs["b"] is None
    nothing = stage_totals([*FEATURES, FeatureProfile(feature_id="c", description="d", example_input="x", mode="interactive")],
                           STAGES, tables(), [], [])
    assert all(not t.complete for t in nothing)      # a feature with no candidate rows leaves every total incomplete


def test_a_model_that_is_not_a_candidate_for_a_feature_leaves_that_feature_unknown():
    costs = {k: v for k, v in COSTS.items() if k != ("b", "big")}
    total = pick(stage_totals(FEATURES, STAGES, tables(costs), [], []), "single_model", "Scale", "big")
    assert total.feature_models["b"] is None and "not a candidate for b" in total.note and not total.complete


@pytest.mark.parametrize("budget,stage,fit", [("1000", "Scale", "within"), ("250", "Scale", "over"),
                                              ("250", "Launch", "within"), (None, "Scale", "no_budget")])
def test_budget_fit_marks_the_first_stage_over_the_ceiling(budget, stage, fit):
    totals = stage_totals(FEATURES, STAGES, tables(), [], [], budget=None if budget is None else Decimal(budget))
    assert pick(totals, "cheapest_per_feature", stage).budget_fit == fit


def test_a_lower_bound_under_budget_is_unknown_but_above_budget_is_over():
    totals = stage_totals(FEATURES, STAGES, tables(lower=True), [], [], budget=Decimal("250"))
    assert pick(totals, "cheapest_per_feature", "Launch").budget_fit == "unknown"
    assert pick(totals, "cheapest_per_feature", "Scale").budget_fit == "over"


def test_revenue_uses_paying_fraction_of_stage_users_and_margin_is_ai_only():
    usage = UsageAssumptions(paying_fraction=Decimal("0.08"), subscription_price_usd=Decimal("15"))
    scale = pick(stage_totals(FEATURES, STAGES, tables(), [], [], usage=usage), "cheapest_per_feature", "Scale")
    assert scale.revenue_usd == Decimal("60000.00")              # 50,000 x 8% x $15, not 50,000 x $15
    assert scale.ai_contribution_usd == Decimal("59700.00") and scale.ai_contribution_margin == Decimal("0.9950")


@pytest.mark.parametrize("fraction,revenue,contribution,margin", [
    ("0", "0.00", "-300.00", None), ("1", "750000.00", "749700.00", "0.9996")])
def test_zero_and_full_paying_fraction(fraction, revenue, contribution, margin):
    usage = UsageAssumptions(paying_fraction=Decimal(fraction), subscription_price_usd=Decimal("15"))
    scale = pick(stage_totals(FEATURES, STAGES, tables(), [], [], usage=usage), "cheapest_per_feature", "Scale")
    assert scale.revenue_usd == Decimal(revenue) and scale.ai_contribution_usd == Decimal(contribution)
    assert scale.ai_contribution_margin == (None if margin is None else Decimal(margin))


def test_missing_revenue_shows_costs_only():
    scale = pick(stage_totals(FEATURES, STAGES, tables(), [], [], usage=UsageAssumptions(paying_fraction=Decimal("0.1"))),
                 "cheapest_per_feature", "Scale")
    assert scale.monthly_usd == Decimal("300.00") and scale.revenue_usd is None and scale.ai_contribution_usd is None


def test_projection_totals_are_separate_from_actual_route_totals():
    proj = [OpenRouterProjectionTable(feature_id=t.feature_id, rows=[r.model_copy(update={"model_id": "openrouter/" + r.model_id,
                                                                                           "lower_bound": True}) for r in t.rows])
            for t in tables()]
    totals = stage_totals(FEATURES, STAGES, tables(), proj, [])
    projected = pick(totals, "cheapest_per_feature", "Scale", scope="openrouter_listed_token_scenario")
    assert projected.feature_models == {"a": "openrouter/small", "b": "openrouter/small"} and projected.lower_bound
    assert not any(t.scenario == "recommended" and t.pricing_scope != "actual_route" for t in totals)


def test_decimal_precision_is_kept_until_display():
    costs = {("a", "m"): {"Launch": "0.004", "Scale": "0.004"}, ("b", "m"): {"Launch": "0.004", "Scale": "0.004"}}
    launch = pick(stage_totals(FEATURES, STAGES, tables(costs), [], []), "single_model", "Launch", "m")
    assert launch.monthly_usd == Decimal("0.01")     # 0.008 summed exactly, then rounded once (not 0.00 + 0.00)
