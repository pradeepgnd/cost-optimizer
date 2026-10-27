"""M06 typed source/readback fixtures and controller outage/allowlist regressions; no network."""
from pathlib import Path
from decimal import Decimal
import json

import httpx
import pytest

from app.adapters.base import SetupIncomplete
from app.adapters.live_zetaris import ZetarisDataLayer
from app.adapters.sample import SampleDataLayer, SampleMemory
from app.adapters.validation import table_rows
from app.contracts import FounderBrief, RunState
from app.controller import Controller
from app.dispatch import Checkpoints
from app.source_contracts import RouteMap, SourceBindings
from app.source_snapshots import build_bundle, canonical, collect_snapshot, digest, json_load
from app.trace import Trace
from tests.test_controller_live_fake import Data, FakeNightshift, FR, _req

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bundle(tmp_path):
    snapshot, _ = collect_snapshot(tmp_path / "catalog", from_file=ROOT / "data/source_examples/openrouter.fixture.json")
    route_map = RouteMap.model_validate_json((ROOT / "data/source_examples/routes.fixture.json").read_text())
    brief = FounderBrief.model_validate(json.loads((ROOT / "input_examples/example_3.json").read_text())["brief"])
    directory, manifest = build_bundle(snapshot, route_map, tmp_path / "bundles", [brief])
    bindings = SourceBindings(namespace="cost_optimizer_test", snapshot_id=manifest["bundle_id"],
        tables={key: key + "_table" for key in manifest["counts"]}, expected_counts=manifest["counts"], expected_ids=manifest["ids"], registered=True,
        expected_row_sha256={key: {row["record_id"]: digest(canonical(row)) for row in json_load((directory / f"{key}.json").read_bytes())}
                             for key in manifest["counts"]})
    return directory, manifest, bindings


@pytest.fixture
def layer(monkeypatch, bundle):
    for key, value in {"ZETARIS_REST_URL": "https://zetaris.test/api", "ZETARIS_ORG_ID": "1", "ZETARIS_API_KEY": "fixture-credential"}.items():
        monkeypatch.setenv(key, value)
    adapter = ZetarisDataLayer(bindings=bundle[2])
    yield adapter
    adapter.client.close()


def response_rows(rows):
    headers = list(rows[0]) if rows else []
    return {"headers": headers, "data": [[row[key] for key in headers] for row in rows]}


def test_reads_validate_pinned_ids_hashes_and_preserve_unknown_prices(layer, bundle, monkeypatch):
    calls = []
    def query(sql, limit=50):
        calls.append(sql)
        assert "snapshot_id = '" + bundle[1]["bundle_id"] + "'" in sql and "LIMIT 4" in sql
        layer.last_query_id = "fixture-query"
        return response_rows(json_load((bundle[0] / "models.json").read_bytes()))
    monkeypatch.setattr(layer, "_run_sql", query)
    models = layer.read_models()
    assert len(calls) == 1 and len(models) == 3
    assert all(rate.usd_per_unit is None for model in models for rate in model.rates)
    assert all(model.source.query_id == "fixture-query" and model.source.transport_ref.startswith("zetaris://") for model in models)
    assert all(model.dispatch_policy is None for model in models)


@pytest.mark.parametrize("mutation", ["hash", "duplicate", "wrong_id", "wrong_snapshot", "incomplete", "extra", "bad_payload", "forged_payload", "fixture_flag"])
def test_invalid_ambiguous_or_incomplete_rows_fail_closed(layer, bundle, monkeypatch, mutation):
    rows = json_load((bundle[0] / "models.json").read_bytes())
    if mutation == "hash":
        rows[0]["payload_sha256"] = "0" * 64
    elif mutation == "duplicate":
        rows[1] = dict(rows[0])
    elif mutation == "wrong_id":
        rows[0]["record_id"] = "wrong/model"
    elif mutation == "wrong_snapshot":
        rows[0]["snapshot_id"] = "0" * 24
    elif mutation == "incomplete":
        rows.pop()
    elif mutation == "extra":
        rows.append(dict(rows[0]))
    elif mutation == "bad_payload":
        rows[0]["payload_json"] = '{"model_id":"x"}'
        rows[0]["payload_sha256"] = digest(rows[0]["payload_json"].encode())
    elif mutation == "forged_payload":
        payload = json_load(rows[0]["payload_json"])
        payload["rates"][0]["usd_per_unit"] = "999"
        rows[0]["payload_json"] = canonical(payload).decode()
        rows[0]["payload_sha256"] = digest(rows[0]["payload_json"].encode())
    else:
        rows[0]["integration_test_fixture"] = False
    monkeypatch.setattr(layer,"_run_sql",lambda *a,**k: response_rows(rows))
    with pytest.raises(ValueError):
        layer.read_models()


def test_actual_http_request_uses_observed_source_field(layer):
    def handle(request):
        body = json.loads(request.content)
        assert body["source"] == "SqlEditor" and body["sql"] == "SELECT 1"
        assert body["queryId"] == request.headers["X-Request-ID"]
        return httpx.Response(200,json={"headers": ["1"],"data": [["1"]]})
    layer.client.close()
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        layer.client = client
        assert layer.select_one()["data"] == [["1"]]


def test_optional_build_binding_is_independent_and_missing_bindings_are_explicit(layer):
    assert layer.read_approaches() == []
    layer.bindings = None
    with pytest.raises(SetupIncomplete, match="binding"):
        layer.read_models()


def test_record_id_cannot_inject_sql(layer):
    with pytest.raises(ValueError,match="record ID"):
        layer.read_brief("x' OR 1=1 --")


def test_original_provider_citation_and_date_survive_transport_annotation(layer,bundle,monkeypatch):
    from tests.dispatch_fixtures import verified_profile
    rows = json_load((bundle[0] / "models.json").read_bytes())
    model = verified_profile(SampleDataLayer().read_models()[0]).model_copy(update={"model_id": rows[0]["record_id"]})
    original = model.source.model_copy(deep=True)
    rows[0]["payload_json"] = canonical(model.model_dump(mode="json")).decode()
    rows[0]["payload_sha256"] = digest(rows[0]["payload_json"].encode())
    rows[0]["integration_test_fixture"] = False
    layer.bindings.expected_row_sha256["models"][rows[0]["record_id"]] = digest(canonical(rows[0]))
    layer.last_query_id = "transport-fixture"
    monkeypatch.setattr(layer,"_run_sql",lambda *a,**k: response_rows(rows))
    value = layer.read_models()[0]
    assert value.source.origin_url == original.origin_url and value.source.verified_at == original.verified_at
    assert value.source.status == original.status and value.source.version == original.version
    assert value.source.query_id == "transport-fixture" and value.source.transport_ref.startswith("zetaris://")


def test_sample_evidence_roundtrip_is_idempotent_and_stays_offline_unverified(tmp_path):
    data = SampleDataLayer(tmp_path / "evidence.jsonl")
    record = {"id": "fixture/sample", "run_id": "fixture", "kind": "integration_test_fixture", "payload": {"x": 1}}
    first = data.write_evidence(record)
    second = data.write_evidence(record)
    payload, ref = data.read_evidence(record["id"])
    assert payload == record and ref.version == first.version == second.version
    assert ref.status.value == "unverified" and len(data.evidence_path.read_text().splitlines()) == 1
    with pytest.raises(ValueError,match="conflict"):
        data.write_evidence({**record,"payload": {"x": 2}})


def controller(tmp_path, monkeypatch, data):
    monkeypatch.setenv("LOG_DIR",str(tmp_path / "logs"))
    request, inference = _req(), FakeNightshift()
    ctl = Controller(data,inference,SampleMemory(),Trace(request.run_id,"live",echo=False),"live",Checkpoints(str(tmp_path / "runs.db")),
                     planner_model=FR,critic_model="other/critic-route")
    return ctl, request, inference


def test_controller_reads_each_price_source_once_and_optional_build_outage_does_not_stop_it(tmp_path, monkeypatch):
    class CountingData(Data):
        def __init__(self):
            super().__init__()
            self.counts = {"models": 0,"approaches": 0}
        def read_models(self):
            self.counts["models"] += 1
            return super().read_models()
        def read_approaches(self):
            self.counts["approaches"] += 1
            raise SetupIncomplete("optional build outage")
    data = CountingData()
    ctl, request, inf = controller(tmp_path,monkeypatch,data)
    pack = ctl.run(request)
    assert pack.status == RunState.complete and data.counts == {"models": 1,"approaches": 1}
    assert pack.stage_tables and any("Optional build" in note for note in pack.limitations)
    assert pack.unpublished_evidence_ids == []
    assert any(ref.source_set == "evaluation_evidence" for ref in pack.evidence_refs)


def test_outage_keeps_completed_outputs_and_restart_safe_pending_outbox(tmp_path, monkeypatch):
    class OfflineWriter(Data):
        def write_evidence(self, record):
            raise SetupIncomplete("writer unavailable")
    ctl, request, inf = controller(tmp_path,monkeypatch,OfflineWriter())
    pack = ctl.run(request)
    assert pack.status == RunState.partial and any(run.executed for run in pack.feature_runs)
    pending = ctl.ckpt.pending_evidence(request.run_id)
    assert {record["id"] for record in pending} == set(pack.unpublished_evidence_ids)
    assert {record["kind"] for record in pending} == {"feature_sample","decision_evidence"}
    assert len(pending) > 1 and all("payload" in record for record in pending)
    restarted = Checkpoints(str(tmp_path / "runs.db"))
    assert restarted.pending_evidence(request.run_id) == pending and not restarted.claim(request.run_id)
    assert len(inf.calls) == pack.dispatch_count


def test_wrong_write_readback_never_produces_published_receipt(tmp_path, monkeypatch):
    class WrongData(Data):
        def read_evidence(self, record_id):
            payload, ref = super().read_evidence(record_id)
            return {**payload,"payload": {"changed": True}}, ref
    ctl, request, _ = controller(tmp_path,monkeypatch,WrongData())
    pack = ctl.run(request)
    assert pack.status == RunState.partial and pack.unpublished_evidence_ids
    assert not any(ref.source_set == "evaluation_evidence" for ref in pack.evidence_refs)


def test_sealed_reads_are_still_denied_before_freeze(tmp_path, monkeypatch):
    ctl, _, _ = controller(tmp_path,monkeypatch,Data())
    for key in ("retrospective_actuals","dev_task_cases:holdout"):
        observation, value = ctl._read(key, lambda: pytest.fail("sealed read was executed"))
        assert observation.status == "denied_sealed" and value is None


def test_a_run_stopped_partial_still_publishes_and_reads_back_its_decision_evidence(tmp_path, monkeypatch):
    class UnknownRevision(FakeNightshift):
        def complete(self, **kwargs):
            result = super().complete(**kwargs)
            if kwargs["role"] == "Revision":
                result["usage"] = {}   # no usage: the operation is unknown and the run stops partial
            return result
    monkeypatch.setenv("LOG_DIR",str(tmp_path / "logs"))
    request, data = _req(), Data()
    ctl = Controller(data,UnknownRevision(),SampleMemory(),Trace(request.run_id,"live",echo=False),"live",
                     Checkpoints(str(tmp_path / "runs.db")),planner_model=FR,critic_model="other/critic-route")
    pack = ctl.run(request)
    assert pack.status == RunState.partial and any("further spending stopped" in l for l in pack.limitations)
    assert pack.unpublished_evidence_ids == []
    assert f"{request.run_id}/decision-evidence" in {ref.record_id for ref in pack.evidence_refs}


def test_sealed_reads_stay_denied_in_stopped_states(tmp_path, monkeypatch):
    ctl, _, _ = controller(tmp_path,monkeypatch,Data())
    for state in (RunState.partial,RunState.needs_input,RunState.failed):
        ctl.state = state
        for key in ("retrospective_actuals","dev_task_cases:holdout"):
            observation, value = ctl._read(key, lambda: pytest.fail("sealed read was executed"))
            assert observation.status == "denied_sealed" and value is None
