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

def test_retrospective_actuals_stay_synthetic():
    actuals = SampleDataLayer().read_sealed_actuals("any")
    assert "SYNTHETIC" in actuals["NOTE"] and actuals["total_spend"]["status"] == "synthetic"
