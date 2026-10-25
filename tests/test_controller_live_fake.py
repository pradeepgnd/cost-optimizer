"""Live-mode controller behaviour against a scripted, in-process fake Nightshift. No network."""
import json
from decimal import Decimal

import pytest

from app.adapters.base import Inference, InferenceResult
from app.adapters.sample import SampleDataLayer, SampleMemory
from app.contracts import FounderBrief, RunRequest, RunState
from app.controller import MAX_CANDIDATE_GENERATIONS, NOT_ADVICE, Budget, Checkpoints, Controller, StopRun
from app.trace import Trace

FR, MID, OS = "sample/frontier-placeholder", "sample/mid-tier-placeholder", "sample/open-source-placeholder"
CANDIDATES = [FR, MID, OS]


class Data(SampleDataLayer):
    def __init__(self):
        super().__init__()
        self.written = []

    def write_evidence(self, record):
        self.written.append(record)


class FakeNightshift(Inference):
    """Scripted responses per role and model. Records every call."""

    def __init__(self, routes=None, critic=None, answers=None):
        self.routes = routes if routes is not None else CANDIDATES + ["other/critic-route"]
        self.critic = critic if critic is not None else {
            "verdict": "pass",
            "findings": [{"kind": "output_too_long", "feature_id": "answer", "model_id": FR, "claim": "longer than needed",
                          "severity": "medium", "passed": True},
                         {"kind": "made_up_kind", "feature_id": "answer", "model_id": FR, "claim": "ignored"}],
            "proposed_action": {"action": "apply_output_cap", "feature_id": "answer", "model_id": FR, "max_output_tokens": 200}}
        self.answers = answers or {FR: "short reply", MID: "short reply", OS: "a much longer reply than allowed"}
        self.calls = []

    def list_models(self):
        return list(self.routes)

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60, max_tokens=None):
        self.calls.append({"role": role, "model": model, "max_tokens": max_tokens})
        if role == "Planner":
            text = json.dumps({"domain_risks": [{"description": "Stores user text; consent needed", "severity": "high",
                                                 "feature_ids": ["answer", "not-a-feature"]}]})
            usage = {"prompt_tokens": 100, "completion_tokens": 50}
        elif role == "Critic":
            text, usage = json.dumps(self.critic), {"prompt_tokens": 300, "completion_tokens": 80}
        else:
            text = json.dumps({"answer": self.answers[model]})
            out = 150 if max_tokens else 500
            usage = {"prompt_tokens": 1000, "completion_tokens": out, "completion_tokens_details": {"reasoning_tokens": 100}}
        return InferenceResult(text=text, requested_model=model, resolved_model=model, route_id=f"r{len(self.calls)}",
                               usage=usage, elapsed_s=0.01, execution_kind="live_inference")


FEATURE = {"feature_id": "answer", "description": "answer a question", "example_input": "Is the sky blue on a clear day?",
           "mode": "interactive", "uses_per_user_month": "10", "expected_output_words": 300,
           "rubric_checks": [{"check_id": "shape", "description": "JSON with answer", "kind": "required_json_fields",
                              "params": {"fields": ["answer"]}},
                             {"check_id": "short", "description": "answer at most 3 words", "kind": "max_words",
                              "params": {"limit": 3, "json_field": "answer"}},
                             {"check_id": "tone", "description": "friendly", "kind": "human_review", "critical": False}]}


def _req(features=None, approved=True, run_id="live-1"):
    brief = FounderBrief.model_validate({"brief_id": "b", "brief_version": "1", "product_concept": "Q&A helper",
                                         "target_user": "anyone", "features_v1": [], "constraints": {"status": "unknown"},
                                         "ai_features": features or [FEATURE]})
    return RunRequest(project_id="p", run_id=run_id, brief=brief, evaluation_approved=approved, max_spend_usd=Decimal("25"))


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))

    def go(inf=None, critic_model="other/critic-route", req=None):
        inf = inf or FakeNightshift()
        req = req or _req()
        trace = Trace(req.run_id, "live", echo=False)
        ctl = Controller(Data(), inf, SampleMemory(), trace, "live", Checkpoints(str(tmp_path / "runs.db")),
                         critic_model=critic_model, planner_model="meterless/auto")
        pack = ctl.run(req)
        events = [json.loads(l) for l in trace.path.read_text(encoding="utf-8").splitlines()]
        return pack, inf, events, ctl
    return go


def test_measured_usage_is_recorded_and_used(run):
    pack, inf, _, _ = run()
    assert pack.status == RunState.complete
    fr = next(r for r in pack.feature_runs if r.model_id == FR and not r.is_repair)
    assert fr.executed and len(fr.samples) == 2
    assert fr.measured_mean.basis == "measured" and fr.measured_mean.output_tokens == 500
    assert fr.measured_mean.reasoning_tokens == 100            # breakdown inside the 500, not added
    assert fr.output_gap_ratio == Decimal("1.25")              # 500 measured / 400 estimated
    rows = [r for t in pack.stage_tables for r in t.rows if r.model_id == FR]
    assert rows and all(r.token_basis == "measured" for r in rows)
    analyst = [c for c in inf.calls if c["role"] == "Analyst"]
    assert len(analyst) == 3 * 2 + 1                           # 3 candidates × 2 samples + 1 repair


def test_rubric_decides_and_model_stack_is_cheapest_qualified(run):
    pack, _, _, _ = run()
    by = {r.model_id: r.rubric for r in pack.feature_runs if not r.is_repair}
    assert by[OS].checks["short"] is False and by[FR].checks["short"] is True and by[MID].pending == ["tone"]
    assert {e.status for e in pack.model_stack} == {"recommended"}
    assert {e.model_id for e in pack.model_stack} == {MID}     # cheapest that passes every critical check
    assert all(e.alternate_model_id == FR for e in pack.model_stack)


def test_critic_flags_only_and_verdicts_are_dropped(run):
    pack, _, events, _ = run()
    crit = pack.critiques[0]
    assert [f.kind for f in crit.findings] == ["output_too_long"]          # unknown kind dropped
    assert crit.controller_decision == "accepted"
    dropped = [e for e in events if e["action"] == "critic_verdict_ignored"]
    assert dropped and "verdict" in dropped[0]["output_summary"] and "passed" in dropped[0]["output_summary"]


def test_one_repair_rerun_with_output_cap_feeds_the_lever(run):
    pack, inf, _, _ = run()
    assert len(pack.revisions) == 1 and pack.revisions[0].change == {"max_tokens": 200}
    assert [c["max_tokens"] for c in inf.calls if c["max_tokens"]] == [200]
    rep = [r for r in pack.feature_runs if r.is_repair]
    assert len(rep) == 1 and rep[0].measured_mean.output_tokens == 150
    levers = [l for t in pack.stage_tables for r in t.rows if r.model_id == FR for l in r.levers if l.lever == "output_cap"]
    assert levers and all(l.applies and l.monthly_delta_usd < 0 for l in levers)


def test_invalid_cap_is_rejected_and_nothing_reruns(run):
    critic = {"findings": [{"kind": "output_too_long", "feature_id": "answer", "model_id": FR, "claim": "long"}],
              "proposed_action": {"action": "apply_output_cap", "feature_id": "answer", "model_id": FR, "max_output_tokens": 900}}
    pack, inf, _, _ = run(FakeNightshift(critic=critic))
    assert pack.critiques[0].controller_decision == "rejected" and pack.revisions == []
    assert not [c for c in inf.calls if c["max_tokens"]]


def test_unflagged_cap_and_unknown_actions_are_rejected(run):
    for i, action in enumerate(({"action": "apply_output_cap", "feature_id": "answer", "model_id": FR, "max_output_tokens": 200},
                                {"action": "delete_rubric"})):
        pack, _, _, _ = run(FakeNightshift(critic={"findings": [], "proposed_action": action}), req=_req(run_id=f"reject-{i}"))
        assert pack.critiques[0].controller_decision == "rejected" and pack.revisions == []


def test_prefix_move_is_recorded_not_executed(run):
    critic = {"findings": [], "proposed_action": {"action": "move_to_cacheable_prefix", "feature_id": "answer"}}
    pack, _, _, _ = run(FakeNightshift(critic=critic))
    assert pack.critiques[0].controller_decision == "no_change" and pack.revisions == []
    assert any("cacheable prefix" in q for q in pack.questions)


def test_critic_on_candidate_route_stops_before_any_paid_call_when_another_exists(run):
    pack, inf, _, _ = run(critic_model=FR)
    assert pack.status == RunState.needs_input and inf.calls == []
    assert "other/critic-route" in pack.questions[0]


def test_critic_shares_candidate_route_only_when_nothing_else_is_offered(run):
    pack, inf, events, _ = run(FakeNightshift(routes=CANDIDATES + ["meterless/auto"]), critic_model="")
    assert pack.status == RunState.complete
    assert any(e["action"] == "critic_shares_candidate_route" for e in events)
    assert any("not independent" in l for l in pack.limitations)
    assert [c["model"] for c in inf.calls if c["role"] == "Critic"] == [FR]


def test_domain_risks_come_from_planner_labeled_model_generated(run):
    pack, _, _, _ = run()
    dom = [r for r in pack.risks if r.cause_class.value == "domain"]
    assert len(dom) == 1 and dom[0].origin == "model_generated" and NOT_ADVICE in dom[0].description
    assert dom[0].triggered_by == ["ai_features:answer"]       # unknown feature id dropped


def test_audio_features_are_never_sent_to_nightshift(run):
    audio = {**FEATURE, "feature_id": "speak", "modality": ["text", "audio_out"], "audio_seconds_per_use": "3"}
    pack, inf, _, _ = run(req=_req([FEATURE, audio]))
    speak = [r for r in pack.feature_runs if r.feature_id == "speak"]
    assert all(not r.executed for r in speak) and len([c for c in inf.calls if c["role"] == "Analyst"]) == 3 * 2 + 1
    assert {e.status for e in pack.model_stack if e.feature_id == "speak"} == {"no_candidate_passes"}


def test_generation_cap_is_30():
    assert MAX_CANDIDATE_GENERATIONS == 30
    b = Budget(max_spend=Decimal("100"))
    for _ in range(30):
        b.reserve_generation(Decimal("0.01"))
    with pytest.raises(StopRun) as e:
        b.reserve_generation(Decimal("0.01"))
    assert e.value.state == RunState.partial and "(30)" in e.value.reason


def test_spend_reconciles_to_measured_cost(run):
    pack, _, _, _ = run()
    assert Decimal("0") < pack.spend_usd < Decimal("1")
