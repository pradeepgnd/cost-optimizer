from decimal import Decimal

import pytest

from app.adapters.sample import SampleDataLayer
from app.contracts import (ApproachProfile, EvidenceStatus, FounderBrief, Rate, RateCategory, RiskCause, SourceRef)
from app.controller import Controller
from app.economics import build_ledger

def _src(i, status=EvidenceStatus.verified): return SourceRef(source_set="pricing_snapshots", record_id=i, version="t", status=status)

def _ctl():
    return Controller.__new__(Controller)   # helpers under test use no adapters

def _approach(i, usd, status=EvidenceStatus.verified, devops="none"):
    return ApproachProfile(approach_id=i, name=i, requires_devops=devops, tokens_per_task_class={"M": Decimal("1000000")},
                           rates=[Rate(category=RateCategory.input_tokens, unit="1M", usd_per_unit=usd, status=status, source=_src(f"{i}-in", status)),
                                  Rate(category=RateCategory.output_tokens, unit="1M", usd_per_unit=usd, status=status, source=_src(f"{i}-out", status))],
                           source=_src(i, status))

def _rank(brief, approaches):
    panel = _ctl()._build_panel(brief, approaches, [build_ledger(a, brief.features_v1) for a in approaches])
    return panel.ranked_approach_ids, panel

def _brief(constraints: dict, features=None):
    return FounderBrief.model_validate({"brief_id": "b", "brief_version": "1", "product_concept": "p", "target_user": "u",
                                        "features_v1": features or [{"feature_id": "F1", "title": "t", "size_class": "M"}],
                                        "constraints": constraints})

def test_risks_come_from_general_signals_only():
    d = SampleDataLayer()
    brief = _brief({"cash_budget_usd": None, "devops_capacity": "none", "status": "verified"},
                   [{"feature_id": "F1", "title": "a", "size_class": "L", "compute_heavy": True},
                    {"feature_id": "F2", "title": "b", "size_class": "S"}])
    approaches = d.read_approaches()
    risks = _ctl()._risks(brief, approaches, [build_ledger(a, brief.features_v1) for a in approaches])
    by = {}
    for r in risks:
        by.setdefault(r.cause_class, []).append(r)
    # only the two DevOps-free approaches are eligible; both carry unverified or unknown rates
    assert len(by[RiskCause.pricing_unverified]) == 2
    assert by[RiskCause.compute_cost][0].triggered_by == ["features_v1:F1"] and by[RiskCause.compute_cost][0].severity == "high"
    assert by[RiskCause.rework][0].triggered_by == ["build_ledgers.rework_multiplier"]
    gaps = {r.triggered_by[0]: r for r in by[RiskCause.requirements_gap]}
    assert gaps["constraints.cash_budget_usd"].severity == "high"          # stated as null -> unknown
    assert "constraints.time_budget_weeks" in gaps                         # never stated -> unknown
    assert "constraints.technical_skill" in gaps and "constraints.team_size" in gaps   # schema defaults -> assumed
    assert "constraints.devops_capacity" not in gaps                       # stated and verified
    assert {r.cause_class for r in risks} <= set(RiskCause)

def test_stated_verified_constraints_raise_no_requirements_gap():
    brief = _brief({"cash_budget_usd": "500", "time_budget_weeks": "2", "team_size": 1, "technical_skill": "scripting",
                    "devops_capacity": "basic", "status": "verified"})
    assert not [r for r in _ctl()._risks(brief, [], []) if r.cause_class == RiskCause.requirements_gap]

STATED = {"cash_budget_usd": "3", "time_budget_weeks": "2", "team_size": 1, "technical_skill": "scripting",
          "devops_capacity": "basic", "status": "verified"}

def test_verified_within_budget_outranks_earlier_unverified_and_over_budget():
    # base build for one M feature at 1M tokens: $1/M -> 1.00, $5/M -> 5.00 against a $3 budget
    ids, panel = _rank(_brief(STATED), [_approach("unverified", Decimal("1"), EvidenceStatus.unverified),
                                        _approach("over", Decimal("5")), _approach("fits", Decimal("1")),
                                        _approach("needs-full", Decimal("1"), devops="full")])
    assert ids == ["fits", "over", "unverified"]
    assert "fits budget" in panel.reasons[1] and "exceeds budget" in panel.reasons[1]
    assert panel.questions == []

def test_no_verified_pricing_adds_question_and_keeps_snapshot_order():
    ids, panel = _rank(_brief(STATED), [_approach("a", Decimal("1"), EvidenceStatus.unverified),
                                        _approach("b", None, EvidenceStatus.unknown)])
    assert ids == ["a", "b"]
    assert any("snapshot order" in r for r in panel.reasons)
    assert len(panel.questions) == 1 and "would change the ranking" in panel.questions[0]

def test_unstated_budget_with_verified_pricing_asks_for_budget():
    _, panel = _rank(_brief({**STATED, "cash_budget_usd": None}), [_approach("v", Decimal("1"))])
    assert panel.questions and "cash budget" in panel.questions[0]

def test_assumed_devops_capacity_that_changes_eligibility_asks_and_does_not_stop():
    unstated = {k: v for k, v in STATED.items() if k != "devops_capacity"}
    ids, panel = _rank(_brief(unstated), [_approach("managed", Decimal("1")), _approach("self-hosted", Decimal("1"), devops="basic")])
    assert ids == [] and panel.questions[0].startswith("Build panel:") and "DevOps" in panel.questions[0]
    assert panel.eligible_by_devops_capacity == {"none": ["managed"], "basic": ["managed", "self-hosted"],
                                                 "full": ["managed", "self-hosted"]}

def test_assumed_devops_capacity_that_changes_nothing_still_ranks():
    unstated = {k: v for k, v in STATED.items() if k != "devops_capacity"}
    ids, _ = _rank(_brief(unstated), [_approach("managed", Decimal("1"))])
    assert ids == ["managed"]
