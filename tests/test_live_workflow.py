"""Actual live adapters/controller against deterministic HTTP/S3 doubles, with real H-MEM.

These tests prove contracts and control flow, not sponsor connectivity or model quality.
"""
import json
import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.adapters.live import NightshiftInference, ZetarisDataLayer
from app.contracts import RunRequest, RunState
from app.controller import Checkpoints, Controller, DuplicateRun
from app.engines.hmem.bridge import HmemBridge
from app.trace import Trace
from scripts.prepare_localstack_data import envelope

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["nvidia/nemotron-test-lightning", "nvidia/nemotron-test-ultra"]


class S3:
    def __init__(self):
        self.objects = {}
        self.writes = []

    def put_object(self, **kwargs):
        key = kwargs["Key"]
        if "IfNoneMatch" in kwargs:
            assert key not in self.objects
        else:
            assert kwargs["IfMatch"] == str(len(self.writes))
        self.objects[key] = json.loads(kwargs["Body"])
        self.writes.append(kwargs)
        return {"ETag": str(len(self.writes))}


def harness(tmp_path, monkeypatch, mode="pass", spend="5", approved=True, fixture=False):
    for name, value in {"ZETARIS_REST_URL": "http://zetaris.test/api/v1.0", "ZETARIS_ORG_ID": "1",
                        "ZETARIS_API_KEY": "private-test-key", "ZETARIS_SOURCE": "oah_localstack",
                        "ZETARIS_SEALED_SOURCE": "oah_localstack_sealed", "METERLESS_BASE_URL": "http://runtime.test/v1",
                        "METERLESS_RUNTIME_TOKEN": "private-runtime-key"}.items():
        monkeypatch.setenv(name, value)
    payload = json.loads((ROOT / "input_examples/example_1.json").read_text())
    payload.update(run_id="test-live", sample_mode=False, max_spend_usd=spend, evaluation_approved=approved)
    request = RunRequest.model_validate(payload)
    brief = payload["brief"] | {"project_id": request.project_id}
    pricing = json.loads((ROOT / "data/sample/pricing_snapshots.json").read_text())
    tasks = json.loads((ROOT / "data/sample/dev_task_cases.json").read_text())
    def rows(kind, values, identity):
        return [envelope(kind, value, identity) | {"setup_fixture": fixture, "approved_for_evaluation": not fixture} for value in values]
    model_profiles = []
    for mid in MODELS:
        rates = [{"category": cat, "unit": "1M tokens", "usd_per_unit": "1",
                  "status": "verified", "source": {"source_set": "pricing_snapshots", "record_id": mid + "/" + cat,
                  "version": "mock-1", "status": "verified", "origin_url": "https://example.test/pricing", "verified_at": "2026-10-25"}}
                 for cat in ("input_tokens", "output_tokens")]
        if mode == "unknown_rate":
            rates[0]["usd_per_unit"] = None
        model_profiles.append({"model_id": mid, "provider_label": "nvidia", "rates": rates,
                               "source": {"source_set": "pricing_snapshots", "record_id": mid, "version": "mock-1"}})
    tables = {"founder_briefs": rows("founder_brief", [brief], "brief_id"),
              "pricing_snapshots_approaches": rows("approach", pricing["approaches"], "approach_id"),
              "pricing_snapshots_models": rows("model", model_profiles, "model_id"),
              "dev_task_cases": rows("task", [t for t in tasks if t["split"] == "development"], "task_id"),
              "dev_task_cases_holdout": rows("task", [t for t in tasks if t["split"] == "holdout"], "task_id")}
    s3, sql_calls, model_calls = S3(), [], []
    evidence_paths = {}
    def sql_handler(req):
        body = json.loads(req.content)
        sql = body["sql"]
        sql_calls.append(sql)
        assert body["source"] == "SqlEditor"
        if sql.startswith("CREATE"):
            table = re.search(r"TABLE (\w+)", sql)[1]
            evidence_paths[table] = re.search(r'PATH "s3a://cost-optimizer-data/([^\"]+)"', sql)[1]
            return httpx.Response(200, json={"headers": [], "data": []})
        table = re.search(r"FROM \w+\.(\w+)", sql)[1]
        if table in evidence_paths:
            data = s3.objects[evidence_paths[table]]
            rid = re.search(r"record_id = '([^']+)'", sql)[1]
            data = [row for row in data if row["record_id"] == rid]
            if mode == "bad_writeback":
                data = []
        else:
            data = tables[table]
            if mode == "missing_source" and table == "founder_briefs":
                data = []
        headers = list(data[0]) if data else ["record_id"]
        return httpx.Response(200, json={"headers": headers, "data": [[row[h] for h in headers] for row in data]})
    data = ZetarisDataLayer(s3_client=s3)
    data.client.close()
    data.client = httpx.Client(transport=httpx.MockTransport(sql_handler))
    def runtime_handler(req):
        if req.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": mid} for mid in MODELS]})
        body = json.loads(req.content)
        assert body["max_tokens"] == 1024 and body["chat_template_kwargs"]["enable_thinking"] is False
        prompt = json.loads(body["messages"][1]["content"])
        model_calls.append(prompt)
        if mode == "timeout":
            raise httpx.ReadTimeout("private failure", request=req)
        if mode == "connect_retry" and len(model_calls) <= 2 or mode == "connect_fail":
            raise httpx.ConnectError("not delivered", request=req)
        if "task" in prompt:
            task, config = prompt["task"], prompt["config"]
            output = {key: f"Concrete mock spec for {key}" for key in task["required_elements"]}
            if mode in {"repair", "requery"} and task["task_id"] == "T1" and config["config_id"] == "cfg-a" and config["config_version"] == 1:
                output.pop(task["required_elements"][0])
            if mode == "holdout_fail" and task["split"] == "holdout":
                output = {}
            output["cost_note"] = {"text": "Unknown approach conversion; cited evidence only.",
                                   "evidence_ids": [prompt["pricing_evidence"][0]["record_id"]]}
        else:
            results = [case["result"] for case in prompt["cases"]]
            failed = [r for r in results if not all(r["elements_present"].values())]
            target = failed[0] if failed else None
            output = {"case_ids": [r["output_ref"] for r in results],
                      "findings": [{"claim": "The schema section is missing in the observed output.", "severity": "high",
                                   "task_id": target["task_id"], "supporting_or_missing_source_ids": [target["output_ref"]]}] if target else [],
                      "proposed_action": {"action": "revise_prototype" if target else "finalize",
                          "inputs": {"config_id": target["config_id"], "task_ids": [target["task_id"]]} if target else {},
                          "evidence_ids": [target["output_ref"]] if target else [], "concise_reason": "Observed checks",
                          "expected_observation": "All required elements", "proposed_by": "Critic"}, "expected_check": "Required elements and citations"}
            if mode == "sealed_critic":
                output["proposed_action"].update(action="retrieve_evidence", inputs={"config_id": "cfg-a", "task_ids": ["T1"], "source_key": "dev_task_cases:holdout"})
            if mode == "requery":
                output["proposed_action"]["action"] = "retrieve_evidence"
                output["proposed_action"]["inputs"]["source_key"] = "pricing_snapshots"
            if mode == "unknown_ref":
                output["case_ids"] = ["invented/case"]
        text = "invalid JSON" if mode == "bad_critic" and "task" not in prompt else json.dumps(output)
        usage = {} if mode == "missing_usage" else {"prompt_tokens": 100, "completion_tokens": 50}
        return httpx.Response(200, json={"id": "response-" + str(len(model_calls)), "model": body["model"],
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}], "usage": usage,
            "meterless": {"receipt_id": "receipt-" + str(len(model_calls)),
                "winning_route": {"provider": "nvidia", "model": body["model"]}}})
    runtime = httpx.Client(transport=httpx.MockTransport(runtime_handler))
    monkeypatch.setattr(httpx, "get", runtime.get)
    monkeypatch.setattr(httpx, "post", runtime.post)
    trace = Trace(request.run_id, "live", str(tmp_path / "logs"), echo=False)
    data.trace = trace
    controller = Controller(data, NightshiftInference(trace), HmemBridge(storage_dir=tmp_path / "memory"), trace,
                            "live", Checkpoints(str(tmp_path / "runs.db")), critic_model=MODELS[1], candidate_models=MODELS)
    return controller, request, sql_calls, model_calls, s3


def test_live_adapters_complete_without_repair_and_freeze_precedes_holdout(tmp_path, monkeypatch):
    ctl, req, sql, calls, s3 = harness(tmp_path, monkeypatch)
    pack = ctl.run(req)
    assert pack.status == RunState.complete, pack.limitations
    assert pack.recommended_config and not pack.revisions
    assert len(pack.development_results) == len(pack.holdout_results) == 6
    assert len(calls) == 13 and pack.spend_usd == Decimal("0.00195") and pack.spend_reserved_usd == 0
    assert all(charge["status"] == "usage_priced" for charge in pack.inference_costs)
    assert pack.critiques[0].controller_decision == "no_change"
    assert all(ref.origin_url.startswith("zetaris://") for ref in pack.evidence_refs if ref.source_set == "evaluation_evidence")
    events = [json.loads(line) for line in ctl.trace.path.read_text().splitlines()]
    freeze = next(e["seq"] for e in events if "-> frozen" in e["output_summary"])
    hold_reads = [e["seq"] for e in events if "dev_task_cases_holdout" in e["output_summary"]]
    assert hold_reads and min(hold_reads) > freeze
    assert len(pack.frozen_configs) == 2 and pack.freeze_digest
    assert all(e["extra"]["usage"]["prompt_tokens"] == 100 for e in events if e["action"] == "nightshift_request")
    assert not any("retrospective_actuals" in query for query in sql)
    critic = next(c for c in calls if "cases" in c)
    assert all(task["split"] == "development" for task in critic["tasks"])
    assert all("holdout" not in case["result"]["output_ref"] for case in critic["cases"])
    before = len(calls)
    with pytest.raises(DuplicateRun):
        ctl.run(req)
    assert len(calls) == before


@pytest.mark.parametrize("mode", ["repair", "requery"])
def test_live_observed_failure_drives_one_targeted_revision(tmp_path, monkeypatch, mode):
    ctl, req, sql, calls, _ = harness(tmp_path, monkeypatch, mode)
    pack = ctl.run(req)
    assert pack.status == RunState.complete, pack.limitations
    assert len(pack.revisions) == 1 and pack.revisions[0].config_id == "cfg-a"
    assert pack.critiques[0].controller_decision == "accepted"
    repaired = [c for c in calls if "task" in c and c["config"]["config_version"] == 2 and c["task"]["split"] == "development"]
    assert len(repaired) == 3
    assert "schema section is missing" in repaired[0]["config"]["workflow_settings"]["repair"]["findings"][0]
    assert all("sample_context_missing" not in call for call in calls)
    assert sum("SELECT * FROM oah_localstack.pricing_snapshots_approaches" in query for query in sql) == (2 if mode == "requery" else 1)


@pytest.mark.parametrize("mode", ["bad_critic", "sealed_critic", "unknown_ref"])
def test_invalid_critique_abstains_before_holdout(tmp_path, monkeypatch, mode):
    ctl, req, sql, _, _ = harness(tmp_path, monkeypatch, mode)
    pack = ctl.run(req)
    assert pack.status == RunState.partial and pack.critiques[0].controller_decision == "rejected"
    assert not pack.revisions and not pack.holdout_results
    assert not any("dev_task_cases_holdout" in query for query in sql)


@pytest.mark.parametrize("mode", ["timeout", "missing_usage"])
def test_ambiguous_dispatched_cost_stays_unknown_and_is_not_retried(tmp_path, monkeypatch, mode):
    ctl, req, _, calls, _ = harness(tmp_path, monkeypatch, mode)
    pack = ctl.run(req)
    assert pack.status == RunState.partial and len(calls) == 1
    assert pack.spend_usd is None and pack.spend_reserved_usd > 0
    assert not pack.holdout_results and not pack.recommended_config


@pytest.mark.parametrize("mode", ["connect_retry", "connect_fail"])
def test_only_pre_delivery_connection_failures_retry_with_global_cap(tmp_path, monkeypatch, mode):
    ctl, req, _, calls, _ = harness(tmp_path, monkeypatch, mode)
    pack = ctl.run(req)
    assert ctl.budget.transport_retries == 2
    if mode == "connect_retry":
        assert pack.status == RunState.complete and len(calls) == 15
        assert pack.spend_usd == Decimal("0.00195")
    else:
        assert pack.status == RunState.partial and len(calls) == 3 and pack.spend_usd == 0
        assert pack.spend_reserved_usd == 0


@pytest.mark.parametrize("options", [{"approved": False}, {"fixture": True}, {"mode": "unknown_rate"}, {"spend": "0"}, {"mode": "missing_source"}])
def test_prerequisites_and_reservations_block_before_inference(tmp_path, monkeypatch, options):
    ctl, req, _, calls, _ = harness(tmp_path, monkeypatch, **options)
    pack = ctl.run(req)
    assert pack.status in {RunState.needs_input, RunState.partial} and calls == []
    assert pack.spend_usd == 0 and not pack.development_results


def test_sealed_read_is_denied_before_adapter_dispatch(tmp_path, monkeypatch):
    ctl, _, _, _, _ = harness(tmp_path, monkeypatch)
    def forbidden(*args):
        pytest.fail("Sealed adapter was reached before freeze")
    for source in ("dev_task_cases:holdout", "retrospective_actuals"):
        observation = ctl._read(source, forbidden)
        assert observation.status == "denied_sealed"
    assert "denied_sealed" in ctl.trace.path.read_text()


def test_holdout_gate_failure_abstains(tmp_path, monkeypatch):
    ctl, req, _, _, _ = harness(tmp_path, monkeypatch, "holdout_fail")
    pack = ctl.run(req)
    assert pack.status == RunState.complete and pack.recommended_config is None
    assert any("abstaining" in reason for reason in pack.reasons)


def test_failed_evidence_readback_stops_and_preserves_usage_spend(tmp_path, monkeypatch):
    ctl, req, _, calls, _ = harness(tmp_path, monkeypatch, "bad_writeback")
    pack = ctl.run(req)
    assert pack.status == RunState.partial and len(calls) == 1
    assert pack.spend_usd == Decimal("0.00015")
    assert any("readback" in message for message in pack.limitations)


@pytest.mark.parametrize("method,arg", [("read_brief", "x' OR '1'='1"), ("read_task_cases", "holdout' UNION SELECT"),
                                       ("read_sealed_actuals", "x'; DROP TABLE t")])
def test_identifiers_and_splits_are_validated_before_sql(tmp_path, monkeypatch, method, arg):
    ctl, _, sql, _, _ = harness(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        getattr(ctl.data, method)(arg)
    assert sql == []


@pytest.mark.parametrize("response", [{"headers": ["a", "a"], "data": [[1, 2]]},
                                      {"headers": ["a"], "data": [[1, 2]]},
                                      {"headers": ["a"], "data": [[1], [2]]},
                                      {"headers": ["a"], "data": [], "error": "failed"}])
def test_ambiguous_or_oversized_zetaris_results_are_rejected(response):
    from app.adapters.zetaris import table_rows
    from app.adapters.base import SetupIncomplete
    with pytest.raises(SetupIncomplete):
        table_rows(response, limit=1)


def test_missing_discovered_model_is_rejected_before_completion(tmp_path, monkeypatch):
    ctl, _, _, calls, _ = harness(tmp_path, monkeypatch)
    from app.adapters.base import SetupIncomplete
    with pytest.raises(SetupIncomplete, match="discovered"):
        ctl.inf.complete(role="candidate", model="typo-model", system="", user="")
    assert calls == []


@pytest.mark.parametrize("state", [RunState.investigating, RunState.development_check, RunState.repair])
def test_sealed_adapters_are_never_called_in_any_prefreeze_state(tmp_path, monkeypatch, state):
    ctl, _, _, _, _ = harness(tmp_path, monkeypatch)
    ctl.state = state
    def forbidden():
        pytest.fail("Adapter dispatched")
    assert ctl._read("retrospective_actuals", forbidden).status == "denied_sealed"
    assert ctl._read("dev_task_cases:holdout", forbidden).status == "denied_sealed"


@pytest.mark.parametrize("project,consent,passes", [("proj-brief-avl-prebuild", True, True),
                                                 ("another-project", True, False),
                                                 ("proj-brief-avl-prebuild", False, False)])
def test_private_actuals_require_matching_project_and_consent(tmp_path, monkeypatch, project, consent, passes):
    ctl, request, _, _, _ = harness(tmp_path, monkeypatch)
    row = {"project_id": project, "record_id": project, "source_version": "private-1", "evidence_status": "reconstructed",
           "consented_for_retrospective": consent, "payload_json": json.dumps({"project_id": project})}
    def query(sql, limit):
        assert ".retrospective_actuals" in sql and "LIMIT 2" in sql and limit == 2
        return {"headers": list(row), "data": [list(row.values())]}
    ctl.data._run_sql = query
    if passes:
        actuals = ctl.data.read_sealed_actuals(request.project_id)
        assert actuals["source"]["version"] == "private-1"
        assert actuals["source"]["source_set"] == "retrospective_actuals"
    else:
        from app.adapters.base import SetupIncomplete
        with pytest.raises(SetupIncomplete):
            ctl.data.read_sealed_actuals(request.project_id)


def test_trace_preserves_numeric_usage_but_masks_credentials():
    from app.trace import _mask
    masked = _mask({"usage": {"prompt_tokens": 100, "completion_tokens": 50},
                    "runtime_token": "private-test-secret", "input_tokens": "a-string-is-still-secret"})
    assert masked["usage"] == {"prompt_tokens": 100, "completion_tokens": 50}
    assert masked["runtime_token"] == masked["input_tokens"] == "...redacted"
