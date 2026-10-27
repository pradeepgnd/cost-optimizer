"""M04: durable spend/call safety with synthetic billing evidence and no model/network calls."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
import sqlite3
from threading import Barrier

import httpx
import pytest

from app.adapters.sample import SampleDataLayer
from app.contracts import DispatchPolicy, EvidenceStatus, RateCategory, RunRequest
from app.dispatch import Budget, Checkpoints, Dispatcher, DuplicateRun, StopRun, request_bound
from app.trace import Trace
from tests.dispatch_fixtures import verified_profile
from tests.test_controller_live_fake import CANDIDATES, Data, FakeNightshift, FR, FEATURE, _req


class ScriptedInference:
    def __init__(self, outcomes=()):
        self.outcomes, self.calls = list(outcomes), []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0) if self.outcomes else None
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            return outcome(kwargs)
        if outcome is not None:
            return outcome
        return {"text": "OK", "requested_model": kwargs["model"], "resolved_model": kwargs["model"],
                "route_id": f"fixture-{len(self.calls)}", "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                "execution_kind": "live_inference"}


@pytest.fixture
def dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    def create(*, model=None, outcomes=(), allowance="25", run_id="dispatch-test", checkpoint=None, inference=None):
        model = model or verified_profile(SampleDataLayer().read_models()[0])
        ckpt = checkpoint or Checkpoints(str(tmp_path / "runs.db"))
        if not ckpt.conn.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone():
            assert ckpt.claim(run_id)
        inf = inference or ScriptedInference(outcomes)
        dispatcher = Dispatcher(inf, ckpt, run_id, Budget(Decimal(allowance)), [model], Trace(run_id, "live", echo=False))
        return dispatcher, inf, ckpt, model
    return create


def call(dispatcher, model, *, logical_id="feature/sample-1", role="Analyst", max_tokens=64):
    return dispatcher.call(logical_id=logical_id, role=role, model=model.model_id, system="Fixture system", user="Fixture input", max_tokens=max_tokens)


def test_reservation_is_committed_before_adapter_and_all_fields_are_reconciled(dispatch):
    dispatcher, inf, ckpt, model = dispatch()
    def callback(kwargs):
        # A separate connection sees the receipt before the inference adapter runs.
        db_path = ckpt.conn.execute("PRAGMA database_list").fetchone()[2]
        with sqlite3.connect(db_path) as reader:
            receipt = json.loads(reader.execute("SELECT record FROM dispatch_operations").fetchone()[0])
        assert receipt["state"] == "dispatching" and Decimal(receipt["reserved_usd"]) > 0
        assert dispatcher.budget.held == Decimal(receipt["reserved_usd"])
        assert kwargs["max_tokens"] == 64
        return {"text": "OK", "resolved_model": model.model_id, "route_id": "provider-fixture",
                "receipt_id": "receipt-fixture", "provider": "nvidia", "provider_kind": "cloud",
                "usage": {"prompt_tokens": 10, "completion_tokens": 4}}
    inf.outcomes.append(callback)
    call(dispatcher, model)
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.state == "completed" and record.provider_request_id == "provider-fixture"
    assert record.provider_receipt_id == "receipt-fixture" and record.provider == "nvidia"
    assert record.provider_kind == "cloud"
    assert record.actual_usd == Decimal("0.00015")
    assert dispatcher.budget.spent == record.actual_usd and dispatcher.budget.held == 0
    assert dispatcher.budget.dispatch_count == 1


@pytest.mark.parametrize("extra,error_type,role", [({"requires_review": True}, "RuntimeReviewRequired", "Analyst"),
                                                    ({"finish_reason": "length"}, "NonStopFinish", "Critic"),
                                                    ({"finish_reason": "length"}, "NonStopFinish", "Planner"),
                                                    ({"finish_reason": "content_filter"}, "NonStopFinish", "Analyst")])
def test_runtime_review_or_truncation_stops_further_spend_with_receipt(dispatch, extra, error_type, role):
    model = verified_profile(SampleDataLayer().read_models()[0])
    result = {"text": "partial", "resolved_model": model.model_id, "route_id": "request-fixture",
              "receipt_id": "receipt-fixture", "provider": "nvidia", "provider_kind": "cloud",
              "usage": {"prompt_tokens": 10, "completion_tokens": 4}, **extra}
    dispatcher, _, ckpt, _ = dispatch(model=model, outcomes=[result])
    with pytest.raises(StopRun):
        call(dispatcher, model, role=role)
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.state == "unknown" and record.error_type == error_type
    assert record.provider_receipt_id == "receipt-fixture" and record.actual_usd is not None
    with pytest.raises(StopRun):
        call(dispatcher, model, logical_id="later-sample")


@pytest.mark.parametrize("mutation", ["no_policy", "unverified_policy", "undated_policy", "no_policy_url", "no_rate",
    "unknown_rate", "unverified_rate", "undated_rate", "wrong_unit", "duplicate_rate", "unknown_long_context"])
def test_unknown_bounds_or_billing_rates_never_dispatch(dispatch, mutation):
    profile = verified_profile(SampleDataLayer().read_models()[0])
    if mutation == "no_policy":
        profile = profile.model_copy(update={"dispatch_policy": None})
    elif mutation in {"unverified_policy", "undated_policy", "no_policy_url"}:
        updates = {"status": EvidenceStatus.unverified} if mutation == "unverified_policy" else (
            {"verified_at": None} if mutation == "undated_policy" else {"origin_url": None})
        profile = profile.model_copy(update={"dispatch_policy": profile.dispatch_policy.model_copy(update={
            "source": profile.dispatch_policy.source.model_copy(update=updates)})})
    else:
        rates = list(profile.rates)
        if mutation == "no_rate":
            rates = rates[1:]
        elif mutation == "duplicate_rate":
            rates.append(rates[0])
        elif mutation == "unknown_long_context":
            profile = profile.model_copy(update={"terms": profile.terms.model_copy(update={"long_context_threshold_tokens": 1})})
            rates = [rate for rate in rates if rate.category != RateCategory.long_context_output_tokens]
        else:
            changes = {"usd_per_unit": None} if mutation == "unknown_rate" else (
                {"status": EvidenceStatus.unverified} if mutation == "unverified_rate" else (
                {"unit": "token"} if mutation == "wrong_unit" else {"source": rates[0].source.model_copy(update={"verified_at": None})}))
            rates[0] = rates[0].model_copy(update=changes)
        profile = profile.model_copy(update={"rates": rates})
    dispatcher, inf, ckpt, model = dispatch(model=profile)
    with pytest.raises(StopRun) as exc:
        call(dispatcher, model)
    assert exc.value.evidence_field.startswith("dispatch.")
    assert inf.calls == [] and ckpt.operations(dispatcher.run_id) == []


@pytest.mark.parametrize("limit", [0, -1, True, 1025, 2.5])
def test_invalid_output_limits_never_dispatch(dispatch, limit):
    dispatcher, inf, _, model = dispatch()
    with pytest.raises(StopRun):
        call(dispatcher, model, max_tokens=limit)
    assert not inf.calls


@pytest.mark.parametrize("role", ["Analyst", "Revision"])
def test_a_feature_sample_cut_at_the_cap_completes_with_its_charge_and_spending_continues(dispatch, role):
    model = verified_profile(SampleDataLayer().read_models()[0])
    cut = {"text": "a long answer cut off mid", "resolved_model": model.model_id, "route_id": "request-fixture",
           "receipt_id": "receipt-fixture", "usage": {"prompt_tokens": 10, "completion_tokens": 64}, "finish_reason": "length"}
    dispatcher, inf, ckpt, _ = dispatch(model=model, outcomes=[cut])
    assert call(dispatcher, model, role=role)["finish_reason"] == "length"
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.state == "completed" and record.error_type is None and record.actual_usd is not None
    call(dispatcher, model, logical_id="later-sample")
    assert len(inf.calls) == 2


def test_default_output_limit_is_the_lower_of_the_app_ceiling_and_the_route_policy(dispatch):
    from app.dispatch import MAX_OUTPUT_TOKENS
    dispatcher, inf, _, model = dispatch()
    route_cap = dispatcher.models[model.model_id].dispatch_policy.max_output_tokens
    assert dispatcher.output_cap(model.model_id) == min(route_cap, MAX_OUTPUT_TOKENS)
    call(dispatcher, model, max_tokens=None)
    assert inf.calls[0]["max_tokens"] == min(route_cap, MAX_OUTPUT_TOKENS)


def test_unpriced_router_alias_never_dispatches(dispatch):
    dispatcher, inf, _, _ = dispatch()
    with pytest.raises(StopRun, match="pinned route"):
        dispatcher.call(logical_id="planner", role="Planner", model="meterless/auto", system="fixture", user="fixture")
    assert not inf.calls


def test_zero_budget_stops_before_dispatch_and_cannot_be_raised_on_restart(dispatch):
    dispatcher, inf, ckpt, model = dispatch(allowance="0")
    with pytest.raises(StopRun, match="reservation"):
        call(dispatcher, model)
    assert inf.calls == [] and ckpt.operations(dispatcher.run_id) == []
    # Failed reservations create no operation; a budget is fixed once the first operation is committed.
    funded, inf, ckpt, model = dispatch(allowance="1")
    call(funded, model)
    changed, inf, _, model = dispatch(allowance="25")
    with pytest.raises(StopRun, match="budget cannot be changed"):
        call(changed, model, logical_id="new-operation")
    assert not inf.calls


def test_oversized_prompt_uses_verified_bytes_not_output_estimate(dispatch):
    profile = verified_profile(SampleDataLayer().read_models()[0])
    profile = profile.model_copy(update={"dispatch_policy": profile.dispatch_policy.model_copy(update={"max_prompt_bytes": 1})})
    dispatcher, inf, _, model = dispatch(model=profile)
    with pytest.raises(StopRun, match="byte bound"):
        call(dispatcher, model)
    assert not inf.calls


def test_exhaustion_after_a_completed_request_stops_before_the_next_dispatch(dispatch):
    profile = verified_profile(SampleDataLayer().read_models()[0])
    _, reservation, _, _, _ = request_bound(profile, "Fixture system", "Fixture input", 64)
    dispatcher, inf, ckpt, model = dispatch(allowance=str(reservation))
    call(dispatcher, model)
    with pytest.raises(StopRun, match="reservation"):
        call(dispatcher, model, logical_id="next")
    assert len(inf.calls) == 1 and len(ckpt.operations(dispatcher.run_id)) == 1
    assert dispatcher.budget.spent == Decimal("0.00015")


@pytest.mark.parametrize("input_tokens,expected", [(10, "0.00015"), (200, "0.00215")])
def test_reservation_covers_cliff_but_charge_uses_actual_whole_request_tariff(dispatch, input_tokens, expected):
    profile = verified_profile(SampleDataLayer().read_models()[0])
    profile = profile.model_copy(update={"terms": profile.terms.model_copy(update={"long_context_threshold_tokens": 100})})
    response = {"text": "OK", "resolved_model": profile.model_id,
                "usage": {"prompt_tokens": input_tokens, "completion_tokens": 4}}
    dispatcher, _, ckpt, model = dispatch(model=profile, outcomes=[response])
    call(dispatcher, model)
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.actual_usd == Decimal(expected) and record.reserved_usd > record.actual_usd


@pytest.mark.parametrize("role", ["Planner", "Analyst", "Critic", "Revision", "Diagnostic"])
def test_every_role_reconciles_to_usage_based_cost(dispatch, role):
    dispatcher, inf, ckpt, model = dispatch()
    call(dispatcher, model, role=role)
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.role == role and dispatcher.budget.spent == Decimal("0.00015")
    assert record.actual_usd < record.reserved_usd and dispatcher.budget.held == 0


@pytest.mark.parametrize("failure", [httpx.ReadTimeout("ambiguous"), httpx.WriteTimeout("ambiguous"),
    httpx.RemoteProtocolError("ambiguous"), ValueError("malformed success"), RuntimeError("uncertain"),
    httpx.HTTPStatusError("429 may have been processed", request=httpx.Request("POST", "https://example.test"), response=httpx.Response(429))])
def test_ambiguous_outcome_is_once_reserved_and_blocks_later_dispatch(dispatch, failure):
    dispatcher, inf, ckpt, model = dispatch(outcomes=[failure])
    with pytest.raises(StopRun, match="unknown potentially charged"):
        call(dispatcher, model)
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.state == "unknown" and record.actual_usd is None
    assert dispatcher.budget.spent == 0 and dispatcher.budget.held == record.reserved_usd
    with pytest.raises(StopRun, match="unresolved"):
        call(dispatcher, model, logical_id="later")
    assert len(inf.calls) == 1 and dispatcher.budget.transport_retries == 0


@pytest.mark.parametrize("failure", [httpx.ConnectError("not connected"), httpx.ConnectTimeout("not connected"), httpx.PoolTimeout("no connection acquired")])
def test_safe_pre_dispatch_retry_claims_another_receipt_and_slot(dispatch, failure):
    dispatcher, inf, ckpt, model = dispatch(outcomes=[failure])
    call(dispatcher, model, role="Planner")
    first, second = ckpt.operations(dispatcher.run_id)
    assert first.state == "not_dispatched" and first.actual_usd == 0
    assert second.state == "completed" and first.operation_id != second.operation_id
    assert second.attempt == 2 and second.reserved_usd == first.reserved_usd
    assert dispatcher.budget.transport_retries == 1 and dispatcher.budget.dispatch_count == 2
    assert dispatcher.budget.spent == second.actual_usd and dispatcher.budget.held == 0


def test_two_retry_limit_is_global_across_roles(dispatch):
    dispatcher, inf, ckpt, model = dispatch(outcomes=[httpx.ConnectError("safe"), httpx.ConnectError("safe")])
    call(dispatcher, model, role="Planner", logical_id="planner")
    inf.outcomes.append(httpx.ConnectError("safe"))
    with pytest.raises(StopRun, match="retries exhausted"):
        call(dispatcher, model, role="Critic", logical_id="critic")
    assert len(inf.calls) == 4 and dispatcher.budget.transport_retries == 2
    assert [r.attempt for r in ckpt.operations(dispatcher.run_id)] == [1, 2, 3, 1]


@pytest.mark.parametrize("result", [[], {"usage": {}}, {"text": "OK", "usage": {}},
    {"text": "OK", "resolved_model": FR, "usage": {"prompt_tokens": True, "completion_tokens": 1}},
    {"text": "OK", "resolved_model": "different/model", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}])
def test_malformed_or_unpriced_response_stays_unknown_without_retry(dispatch, result):
    dispatcher, inf, ckpt, model = dispatch(outcomes=[result])
    with pytest.raises(StopRun):
        call(dispatcher, model)
    assert len(inf.calls) == 1 and ckpt.operations(dispatcher.run_id)[0].state == "unknown"
    assert dispatcher.budget.held > 0 and dispatcher.budget.spent == 0


def test_overrun_records_full_charge_and_stops_further_spend(dispatch):
    response = {"text": "OK", "resolved_model": FR, "usage": {"prompt_tokens": 10_000_000, "completion_tokens": 10_000_000}}
    dispatcher, inf, ckpt, model = dispatch(outcomes=[response])
    with pytest.raises(StopRun, match="overrun"):
        call(dispatcher, model)
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.actual_usd == Decimal("475") and dispatcher.budget.spent == Decimal("475")
    assert record.state == "overrun" and record.actual_usd > record.reserved_usd
    with pytest.raises(StopRun, match="exceeded"):
        call(dispatcher, model, logical_id="later")
    assert len(inf.calls) == 1


def test_known_completed_operation_and_restart_never_replay(dispatch):
    dispatcher, inf, ckpt, model = dispatch()
    call(dispatcher, model)
    path = ckpt.conn.execute("PRAGMA database_list").fetchone()[2]
    ckpt.conn.close()
    restarted, inf, ckpt, model = dispatch(checkpoint=Checkpoints(path))
    assert not ckpt.claim(dispatcher.run_id)
    with pytest.raises(StopRun, match="already recorded"):
        call(restarted, model)
    assert not inf.calls and restarted.budget.spent > 0


def test_crash_after_transaction_before_dispatch_retains_reservation_on_restart(dispatch):
    from app.contracts import DispatchRecord
    dispatcher, inf, ckpt, model = dispatch()
    bound, reserved, _, _, sources = request_bound(model, "Fixture system", "Fixture input", 64)
    record = DispatchRecord(operation_id="crashed-operation", logical_id="crashed", attempt=1, role="Analyst",
        requested_model=model.model_id, state="dispatching", reserved_usd=reserved, prompt_token_bound=bound, max_tokens=64, source_refs=sources)
    ckpt.reserve(dispatcher.run_id, record, dispatcher.budget)
    path = ckpt.conn.execute("PRAGMA database_list").fetchone()[2]
    ckpt.conn.close()
    restarted, inf, ckpt, model = dispatch(checkpoint=Checkpoints(path))
    assert restarted.budget.held == reserved and restarted.budget.dispatch_count == 1
    with pytest.raises(StopRun, match="unresolved"):
        call(restarted, model, logical_id="after-restart")
    assert not inf.calls


def test_concurrent_connections_cannot_dispatch_past_an_unresolved_claim(dispatch):
    dispatcher, _, ckpt, model = dispatch()
    path = ckpt.conn.execute("PRAGMA database_list").fetchone()[2]
    barrier = Barrier(2)
    def worker(number):
        local = Checkpoints(path)
        inf = ScriptedInference([httpx.ReadTimeout("unknown")])
        service = Dispatcher(inf, local, dispatcher.run_id, Budget(Decimal("25")), [model], None)
        barrier.wait(timeout=5)
        with pytest.raises(StopRun):
            call(service, model, logical_id=f"parallel-{number}")
        local.conn.close()
        return len(inf.calls)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(worker, (1, 2))) == 1
    assert len(ckpt.operations(dispatcher.run_id)) == 1


@pytest.mark.parametrize("role", ["Planner", "Critic", "Revision"])
def test_role_limits_cannot_be_bypassed_with_new_logical_ids(dispatch, role):
    dispatcher, inf, _, model = dispatch()
    call(dispatcher, model, role=role, logical_id="first")
    with pytest.raises(StopRun, match="call limit"):
        call(dispatcher, model, role=role, logical_id="second")
    assert len(inf.calls) == 1


def test_thirty_dispatch_cap_includes_roles_and_retries(dispatch):
    dispatcher, inf, _, model = dispatch(outcomes=[httpx.ConnectError("safe")])
    call(dispatcher, model, role="Planner", logical_id="planner")  # two slots, one logical call
    call(dispatcher, model, role="Critic", logical_id="critic")
    call(dispatcher, model, role="Revision", logical_id="repair")
    for number in range(26):
        call(dispatcher, model, logical_id=f"candidate-{number}")
    assert dispatcher.budget.dispatch_count == len(inf.calls) == 30
    with pytest.raises(StopRun, match=r"cap \(30\)"):
        call(dispatcher, model, logical_id="extra")
    assert len(inf.calls) == 30


@pytest.mark.parametrize("bad", ["26", "-1", "NaN", "Infinity"])
def test_invalid_budget_cannot_reach_dispatch(bad):
    with pytest.raises(ValueError):
        Budget(Decimal(bad))


@pytest.mark.parametrize("features,profile,samples,dispatches", [(4, "production", 2, 27), (5, "production", 1, 18),
                                                               (4, "validation", 1, 15)])
def test_controller_selects_sampling_before_calls_and_keeps_default_when_it_fits(tmp_path, monkeypatch, features, profile, samples, dispatches):
    from app.controller import Controller
    from app.adapters.sample import SampleMemory
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    req = _req([{**FEATURE, "feature_id": "answer" if i == 0 else f"feature-{i}"} for i in range(features)])
    req.sampling_profile = profile
    inf = FakeNightshift()
    ctl = Controller(Data(), inf, SampleMemory(), Trace(req.run_id,"live",echo=False), "live",
                     Checkpoints(str(tmp_path/'run.db')), planner_model=FR, critic_model="other/critic-route")
    pack = ctl.run(req)
    assert pack.status.value == "complete"
    assert pack.selected_samples_per_pair == samples and pack.dispatch_count == dispatches
    assert pack.dispatch_count == len(inf.calls) <= 30 and pack.reserved_spend_usd == 0
    assert {record.role for record in pack.operations} == {"Planner", "Analyst", "Critic", "Revision"}
    assert pack.spend_usd == sum(record.actual_usd for record in pack.operations)
    assert all(len(run.samples) == samples for run in pack.feature_runs if not run.is_repair)
    assert any(f"{samples} sample(s)" in text for text in pack.limitations)
    with pytest.raises(DuplicateRun):
        ctl.run(req)
    assert len(inf.calls) == dispatches


@pytest.mark.parametrize("profile", ["one", 1, True, ""])
def test_one_sample_validation_profile_is_explicitly_validated(profile):
    payload = _req().model_dump(mode="json")
    payload["sampling_profile"] = profile
    with pytest.raises(ValueError):
        RunRequest.model_validate(payload)


def test_controller_timeout_returns_partial_with_held_charge_and_preserved_sample(tmp_path, monkeypatch):
    from app.controller import Controller
    from app.adapters.sample import SampleMemory
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    class Timeout(FakeNightshift):
        def complete(self, **kwargs):
            result = super().complete(**kwargs)
            if len(self.calls) == 3:
                raise httpx.ReadTimeout("after-dispatch fixture")
            return result
    inf, req = Timeout(), _req()
    ckpt = Checkpoints(str(tmp_path/'partial.db'))
    ctl = Controller(Data(), inf, SampleMemory(), Trace(req.run_id,"live",echo=False), "live", ckpt,
                     planner_model=FR, critic_model="other/critic-route")
    pack = ctl.run(req)
    assert pack.status.value == "partial" and len(inf.calls) == pack.dispatch_count == 3
    assert pack.transport_retries == 0 and pack.reserved_spend_usd > 0
    assert pack.operations[-1].state == "unknown"
    assert sum(len(run.samples) for run in pack.feature_runs) == 1
    assert pack.spend_usd == sum(record.actual_usd or Decimal(0) for record in pack.operations)
    assert any(gap.field == "dispatch.unknown_outcome" for gap in pack.evidence_gaps)
    assert ckpt.conn.execute("SELECT COUNT(*) FROM dispatch_operations WHERE response IS NOT NULL").fetchone()[0] == 2
    assert json.loads(ckpt.conn.execute("SELECT pack FROM runs WHERE run_id=?",(req.run_id,)).fetchone()[0])["status"] == "partial"


def test_missing_route_evidence_returns_partial_before_any_paid_role(tmp_path, monkeypatch):
    from app.controller import Controller
    from app.adapters.sample import SampleMemory
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    inf, req = FakeNightshift(), _req()
    ctl = Controller(SampleDataLayer(), inf, SampleMemory(), Trace(req.run_id,"live",echo=False), "live",
                     Checkpoints(str(tmp_path/'unverified.db')), planner_model=FR, critic_model="other/critic-route")
    pack = ctl.run(req)
    assert pack.status.value == "partial" and not inf.calls and pack.dispatch_count == 0
    assert pack.spend_usd == pack.reserved_spend_usd == 0
    assert any(gap.field.startswith("dispatch.") for gap in pack.evidence_gaps)


@pytest.mark.parametrize("malformed", [False, True])
def test_real_adapter_joins_durable_operation_and_keeps_provider_receipt_on_parse_error(dispatch, monkeypatch, malformed):
    import app.adapters.live_nightshift as module
    monkeypatch.setenv("METERLESS_BASE_URL", "https://runtime.test/v1")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "synthetic-credential")
    adapter = module.NightshiftInference()
    dispatcher, _, ckpt, model = dispatch(inference=adapter)
    adapter.trace = dispatcher.trace
    def handler(request):
        record = ckpt.operations(dispatcher.run_id)[0]
        assert record.state == "dispatching" and request.headers["X-Request-ID"] == record.operation_id
        body = {"id": "fixture-completion", "model": model.model_id,
                "usage": {"prompt_tokens": 10,"completion_tokens": 4}}
        if not malformed:
            body["choices"] = [{"message": {"content": "OK"}}]
        return httpx.Response(200,json=body,headers={"x-request-id": "provider-receipt"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(module.httpx,"post",client.post)
        if malformed:
            with pytest.raises(StopRun,match="unknown"):
                call(dispatcher,model)
        else:
            call(dispatcher,model)
    record = ckpt.operations(dispatcher.run_id)[0]
    assert record.provider_request_id == "provider-receipt" and record.usage["prompt_tokens"] == 10
    events = [json.loads(line) for line in dispatcher.trace.path.read_text().splitlines()]
    assert {event["operation_id"] for event in events} == {record.operation_id}
    assert record.state == ("unknown" if malformed else "completed")


def test_live_adapter_refuses_paid_requests_without_reservation_context(monkeypatch):
    from app.adapters.base import SetupIncomplete
    import app.adapters.live_nightshift as module
    monkeypatch.setenv("METERLESS_BASE_URL", "https://runtime.test/v1")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "synthetic-credential")
    monkeypatch.setattr(module.httpx, "post", lambda *a,**k: pytest.fail("unreserved dispatch"))
    with pytest.raises(SetupIncomplete, match="Dispatcher"):
        module.NightshiftInference().complete(role="Analyst",model=FR,system="fixture",user="fixture",max_tokens=8)
