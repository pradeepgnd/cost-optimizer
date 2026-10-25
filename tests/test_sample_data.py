from app.adapters.sample import SampleDataLayer
from app.contracts import EvidenceStatus

def test_task_cases_split_three_development_three_holdout():
    d = SampleDataLayer()
    dev, hold = d.read_task_cases("development"), d.read_task_cases("holdout")
    assert [t.task_id for t in dev] == ["T1", "T2", "T3"]
    assert [t.task_id for t in hold] == ["T4", "T5", "T6"]

def test_four_approaches_all_rates_unverified():
    approaches = SampleDataLayer().read_approaches()
    assert len(approaches) == 4
    assert all(r.status == EvidenceStatus.unverified for a in approaches for r in a.rates)
    assert all(a.source.status == EvidenceStatus.unverified for a in approaches)

def test_three_candidate_models_by_tier_all_unverified_placeholders():
    models = SampleDataLayer().read_models()
    assert [m.tier for m in models] == ["frontier", "mid_tier", "open_source"]
    assert all("placeholder" in m.model_id for m in models)
    assert all(r.status == EvidenceStatus.unverified for m in models for r in m.rates)
    assert all(m.source.status == EvidenceStatus.unverified for m in models)

def test_sample_stage_table_is_estimated_and_never_claims_a_switch():
    from decimal import Decimal
    from app.contracts import FeatureProfile, RubricCheck
    from app.economics import stage_cost_table
    f = FeatureProfile(feature_id="plan", description="90-day plan", example_input="PM to Program Manager in 90 days",
                       mode="interactive", uses_per_user_month=Decimal("4"), static_prefix_tokens=1500,
                       expected_output_words=900, rubric_checks=[RubricCheck(check_id="specific", description="specific")])
    t = stage_cost_table(f, SampleDataLayer().read_models())
    assert len(t.rows) == 12 and all(r.token_basis == "estimated" and r.lower_bound for r in t.rows)
    assert t.switch_points == []          # no measured quality offline

def test_retrospective_actuals_stay_synthetic():
    actuals = SampleDataLayer().read_sealed_actuals("any")
    assert "SYNTHETIC" in actuals["NOTE"] and actuals["total_spend"]["status"] == "synthetic"
