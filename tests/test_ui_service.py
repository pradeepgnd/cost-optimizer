import json
from pathlib import Path

import pytest

from app import ui_service as svc


@pytest.fixture(autouse=True)
def ui_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "UI_DIR", tmp_path / "ui")


def form_args(template, **over):
    brief = template["brief"]
    args = dict(run_id="ui-test-1", idea=brief["product_concept"], user=brief["target_user"],
                features=[{"feature_id": f["feature_id"], "description": f["description"], "example_input": f["example_input"],
                           "mode": f["mode"], "modality": ", ".join(f["modality"]),
                           "uses_per_user_month": f["uses_per_user_month"]} for f in brief["ai_features"]],
                stages=[{"name": s["name"], "active_users": s["active_users"]} for s in brief["growth_stages"]],
                switch_threshold="100", monthly_ceiling="", approved=True, max_spend="0.50")
    args.update(over)
    return args


def test_sidebar_names_example_1_as_idea_a_and_example_2_as_idea_b():
    assert svc.example_label("example_1") == "Idea: Speech triage"
    assert svc.example_label("example_2") == "Idea: Payments assist"
    assert svc.example_label("example_3") == "Idea: Writing coach"
    concept = svc.load_template("example_1")["brief"]["product_concept"]
    assert "helps kids with speech delays build sentences" in concept
    assert "autistic" not in concept.lower()


@pytest.mark.parametrize("name", svc.list_examples())
def test_unchanged_form_round_trips_to_a_valid_request(name):
    template = svc.load_template(name)
    request = svc.build_request(template, **form_args(template))
    parsed, problem = svc.validate(request)
    assert parsed is not None and problem == ""
    assert [f.feature_id for f in parsed.brief.ai_features] == [f["feature_id"] for f in template["brief"]["ai_features"]]


def test_edits_and_new_feature_rows_reach_the_request_and_nothing_is_invented():
    template = svc.load_template("example_3")
    args = form_args(template)
    args["features"][0]["modality"] = "text, image_in"
    args["features"].append({"feature_id": "extra", "description": "d", "example_input": "x", "mode": "background",
                             "modality": "", "uses_per_user_month": "3"})
    request = svc.build_request(template, **args)
    first, extra = request["brief"]["ai_features"][0], request["brief"]["ai_features"][-1]
    assert first["modality"] == ["text", "image_in"] and extra["modality"] == ["text"]
    assert first["field_status"]["uses_per_user_month"] == "assumed" and extra["calls_per_use"] == "1"
    assert "extra" not in [f["feature_id"] for f in template["brief"]["ai_features"]]   # template untouched


def test_invalid_form_reports_the_problem_instead_of_raising():
    template = svc.load_template("example_3")
    args = form_args(template, max_spend="-1")
    parsed, problem = svc.validate(svc.build_request(template, **args))
    assert parsed is None and "max_spend_usd" in problem


def test_a_run_id_runs_once_and_the_second_call_reuses_the_stored_result():
    template = svc.load_template("example_3")
    request = svc.build_request(template, **form_args(template))
    first = svc.submit_run(request, sample=True)
    assert first["exit_code"] == 0 and not first["reused"]
    pack = first["result"]
    assert pack["status"] == "complete" and pack["execution_mode"] == "sample" and pack["spend_usd"] == "0"
    second = svc.submit_run(request, sample=True)
    assert second["reused"] and second["result"] == pack
    assert svc.load_result("ui-test-1") == pack


def test_run_ids_are_validated_before_touching_the_filesystem():
    with pytest.raises(ValueError):
        svc.result_path("../escape")


def test_stop_reason_reads_the_trace_and_explains_missing_setup(tmp_path):
    trace = tmp_path / "t.jsonl"
    trace.write_text('{"agent_name":"Analyst","action":"retrieve_evidence","status":"error","output_summary":"SetupIncomplete"}\n'
                     '{"agent_name":"Controller","action":"stop","status":"needs_input","output_summary":"pricing unavailable"}\n'
                     '{"agent_name":"Controller","action":"start","status":"ok","output_summary":"mode=live"}\n')
    reason = svc.stop_reason({"trace_path": str(trace)})
    assert "SetupIncomplete" in reason and "pricing unavailable" in reason and "mode=live" not in reason
    assert "ZETARIS_BINDINGS_FILE" in svc.setup_hint(reason) and svc.setup_hint("pricing unavailable") == ""
    assert svc.stop_reason({}) == ""


def test_find_bindings_prefers_override_then_env_then_default(tmp_path, monkeypatch):
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"snapshot_id": "abc", "expected_counts": {"models": 2}}))
    monkeypatch.setattr(svc, "DEFAULT_BINDINGS", tmp_path / "absent.json")
    monkeypatch.delenv("ZETARIS_BINDINGS_FILE", raising=False)
    assert not svc.find_bindings()["ok"] and "ZETARIS_BINDINGS_FILE" in svc.find_bindings()["problem"]
    monkeypatch.setattr(svc, "DEFAULT_BINDINGS", good)
    assert svc.find_bindings()["source"] == "default location"
    monkeypatch.setenv("ZETARIS_BINDINGS_FILE", str(tmp_path / "typo.json"))
    assert svc.find_bindings() == {"ok": False, "source": "ZETARIS_BINDINGS_FILE", "path": str(tmp_path / "typo.json"),
                                   "problem": "file not found"}            # a wrong setting is reported, not skipped
    assert svc.find_bindings(str(good))["source"] == "override" and svc.find_bindings(str(good))["snapshot_id"] == "abc"
    (tmp_path / "bad.json").write_text("{}")
    assert "not a bindings file" in svc.find_bindings(str(tmp_path / "bad.json"))["problem"]


def test_candidate_options_and_picks_reach_the_request(tmp_path):
    sample = svc.candidate_options(sample=True)
    assert "sample/mid-tier-placeholder" in sample and "sample placeholder" in sample["sample/mid-tier-placeholder"]
    bindings = tmp_path / "b.json"
    bindings.write_text(json.dumps({"snapshot_id": "x", "expected_ids": {"models": [
        "openrouter/lab/model", "nvidia/nemotron-3-ultra-550b-a55b", "meterless/auto"]}}))
    live = svc.candidate_options(sample=False, bindings_path=str(bindings))
    assert list(live)[0] == "nvidia/nemotron-3-ultra-550b-a55b" and "can be measured" in live["nvidia/nemotron-3-ultra-550b-a55b"]
    assert "projected only" in live["openrouter/lab/model"] and "meterless/auto" not in live
    assert svc.candidate_options(sample=False) == {}
    template = svc.load_template("example_3")
    request = svc.build_request(template, **form_args(template), candidate_models=["sample/mid-tier-placeholder"])
    assert svc.validate(request)[0].candidate_models == ["sample/mid-tier-placeholder"]
    assert "candidate_models" not in svc.build_request(template, **form_args(template), candidate_models=[])


def test_sample_run_with_picks_uses_only_the_picks():
    template = svc.load_template("example_3")
    request = svc.build_request(template, **form_args(template, run_id="ui-picks-1"),
                                candidate_models=["sample/mid-tier-placeholder", "sample/open-source-placeholder"])
    pack = svc.submit_run(request, sample=True)["result"]
    assert pack["status"] == "complete"
    assert {r["model_id"] for r in pack["feature_runs"]} == {"sample/mid-tier-placeholder", "sample/open-source-placeholder"}
    assert any("chosen by the founder" in item for item in pack["limitations"])


def test_revenue_inputs_reach_the_usage_block_as_assumptions():
    template = svc.load_template("example_3")
    request = svc.build_request(template, **form_args(template), subscription_price="15", paying_fraction="0.08")
    usage = svc.validate(request)[0].brief.usage
    assert str(usage.subscription_price_usd) == "15" and str(usage.paying_fraction) == "0.08"
    assert usage.field_status["paying_fraction"].value == "assumed"
    bad = svc.build_request(template, **form_args(template), paying_fraction="8")      # 8, not 0.08
    assert "paying_fraction" in svc.validate(bad)[1]


def test_run_estimates_include_the_instructions_sent_with_each_example():
    from app.contracts import RunRequest
    from app.controller import Controller
    from app.economics import estimate_tokens
    template = svc.load_template("example_3")
    pack = svc.submit_run(svc.build_request(template, **form_args(template, run_id="ui-instr-1")), sample=True)["result"]
    for feature in RunRequest.model_validate(template).brief.ai_features:
        expected = feature.static_prefix_tokens + estimate_tokens(Controller._prompt(feature)) + estimate_tokens(feature.example_input)
        runs = [r for r in pack["feature_runs"] if r["feature_id"] == feature.feature_id]
        assert runs and all(r["estimated"]["input_tokens"] == str(expected) for r in runs)


def test_read_events_waits_for_complete_lines(tmp_path):
    trace = tmp_path / "t.jsonl"
    trace.write_text('{"seq": 1, "action": "hmem_recall"}\n{"seq": 2, "act')
    events, offset = svc.read_events(trace)
    assert [e["seq"] for e in events] == [1]
    with trace.open("a") as handle:
        handle.write('ion": "select_candidates"}\n')
    more, _ = svc.read_events(trace, offset)
    assert [e["seq"] for e in more] == [2]
    assert svc.read_events(tmp_path / "missing.jsonl") == ([], 0)


def test_progress_rows_summarise_and_hide_bookkeeping():
    events = [{"seq": 1, "agent_name": "Analyst", "action": "nightshift_request_attempt", "status": "pending"},
              {"seq": 2, "agent_name": "Analyst", "action": "nightshift_request", "status": "success", "model": "m",
               "extra": {"usage": {"prompt_tokens": 815, "completion_tokens": 60}, "elapsed_s": 0.9}},
              {"seq": 3, "agent_name": "Analyst", "action": "dispatch_receipt", "status": "dispatching"},
              {"seq": 4, "agent_name": "Critic", "action": "critique", "status": "error", "output_summary": "x" * 300}]
    summary, rows = svc.progress_rows(events)
    assert summary == {"steps": 4, "model_requests": 1, "errors": 1, "latest": "Critic flagging issues"}
    assert [r["#"] for r in rows] == [2, 4] and rows[0]["step"] == "Model request" and len(rows[1]["detail"]) == 120
    assert rows[0]["detail"] == "815 in / 60 out tokens, 0.9 s"
    waiting, _ = svc.progress_rows(events[:1])
    assert waiting["latest"] == "Model request (waiting)"


def test_pipeline_phases_map_trace_to_planner_analyst_critic():
    empty = svc.pipeline_phases([])
    assert [p["name"] for p in empty] == ["Planner", "Analyst", "Critic"]
    assert {p["state"] for p in empty} == {"pending"}
    mid = svc.pipeline_phases([
        {"action": "domain_risk_review", "agent_name": "Planner", "status": "success"},
        {"action": "select_candidates", "agent_name": "Controller", "status": "success"},
        {"action": "nightshift_request", "agent_name": "Analyst", "status": "success"},
    ])
    assert mid[0]["state"] == "done" and mid[1]["state"] == "active" and mid[2]["state"] == "pending"
    done = svc.pipeline_phases(mid and [
        {"action": "domain_risk_review", "agent_name": "Planner", "status": "success"},
        {"action": "run_feature", "agent_name": "Analyst", "status": "success"},
        {"action": "critique", "agent_name": "Critic", "status": "success"},
        {"action": "complete", "agent_name": "Controller", "status": "success"},
    ])
    assert [p["state"] for p in done] == ["done", "done", "done"]


def test_progress_callback_receives_trace_events_while_running():
    template = svc.load_template("example_3")
    seen = []
    out = svc.submit_run(svc.build_request(template, **form_args(template, run_id="ui-progress-1")), sample=True,
                         on_progress=lambda events: seen.append(len(events)), poll_s=0.05)
    assert out["result"]["status"] == "complete" and seen and seen == sorted(seen)
    assert any(e["action"] == "calculate_cost" for e in svc.read_events(svc.ROOT / "logs" / "trace-ui-progress-1.jsonl")[0])


def _single(model, stage, users, monthly, fit, *, complete=True):
    return {"scenario": "single_model", "pricing_scope": "actual_route", "model_id": model, "stage": stage,
            "active_users": users, "monthly_usd": monthly, "complete": complete, "budget_fit": fit}


def test_tier_recommendations_pick_one_frontier_and_one_open_source_that_fit_the_budget():
    pack = {
        "monthly_ai_budget_usd": "100",
        "feature_runs": [{"model_id": mid, "tier": tier, "is_repair": False} for mid, tier in (
            ("big", "frontier"), ("small-f", "frontier"), ("oss", "open_source"), ("oss-costly", "open_source"))],
        "stage_tables": [{"rows": [
            {"model_id": "big", "token_basis": "measured"},
            {"model_id": "small-f", "token_basis": "estimated"},
            {"model_id": "oss", "token_basis": "measured"},
            {"model_id": "oss-costly", "token_basis": "measured"}]}],
        "model_stack": [{"feature_id": "notes", "stage": "Scale", "status": "no_candidate_passes", "model_id": None}],
        "stage_totals": [
            _single("big", "Prototype", 50, "40", "within"), _single("big", "Scale", 5000, "400", "over"),
            _single("small-f", "Prototype", 50, "20", "within"), _single("small-f", "Scale", 5000, "80", "within"),
            _single("oss", "Prototype", 50, "5", "within"), _single("oss", "Scale", 5000, "50", "within"),
            _single("oss-costly", "Prototype", 50, "9", "within"), _single("oss-costly", "Scale", 5000, "90", "within"),
            _single("mid", "Scale", 5000, "1", "within"),
        ],
    }
    picks = {item["tier"]: item for item in svc.tier_recommendations(pack)}
    assert set(picks) == {"frontier", "open_source"}
    assert picks["frontier"]["model_id"] == "small-f" and picks["frontier"]["stage"] == "Scale"
    assert picks["frontier"]["budget_fit"] == "within" and picks["frontier"]["token_basis"] == "estimated"
    assert "$100/month" in picks["frontier"]["reason"] and "Not quality-qualified yet" in picks["frontier"]["reason"]
    assert picks["open_source"]["model_id"] == "oss" and picks["open_source"]["monthly_usd"] == "50"


def test_tier_recommendations_without_a_budget_use_the_cheapest_at_the_largest_stage():
    pack = {
        "monthly_ai_budget_usd": None,
        "feature_runs": [{"model_id": "costly", "tier": "frontier"}, {"model_id": "cheap", "tier": "frontier"}],
        "stage_tables": [{"rows": [{"model_id": "cheap", "token_basis": "estimated"},
                                   {"model_id": "costly", "token_basis": "estimated"}]}],
        "model_stack": [{"status": "requires_live_run", "model_id": None, "feature_id": "notes", "stage": "Scale"}],
        "stage_totals": [
            _single("costly", "Prototype", 50, "10", "no_budget"), _single("costly", "Scale", 5000, "30", "no_budget"),
            _single("cheap", "Prototype", 50, "40", "no_budget"), _single("cheap", "Scale", 5000, "20", "no_budget"),
        ],
    }
    picks = svc.tier_recommendations(pack)
    assert picks[0]["model_id"] == "cheap" and picks[0]["stage"] == "Scale" and "No monthly AI budget" in picks[0]["reason"]
    assert picks[0]["reason"].startswith("cheap ")
    assert "live run is required" in picks[0]["reason"]
    assert picks[1]["model_id"] is None and "No open-source model was compared" in picks[1]["reason"]


def test_tier_recommendations_skip_a_model_that_is_not_priced_for_every_feature():
    pack = {
        "monthly_ai_budget_usd": "100",
        "feature_runs": [{"model_id": "partial", "tier": "open_source"}, {"model_id": "full", "tier": "open_source"}],
        "model_stack": [{"status": "recommended", "model_id": "full", "feature_id": "notes", "stage": "Prototype"}],
        "stage_totals": [
            _single("partial", "Prototype", 50, "1", "within", complete=False),
            _single("full", "Prototype", 50, "10", "within"),
        ],
    }
    pick = svc.tier_recommendations(pack)[1]
    assert pick["tier"] == "open_source" and pick["model_id"] == "full"
    assert "Quality-qualified for notes" in pick["reason"]
    assert svc.tier_recommendations({"stage_totals": []}) == []


def test_tier_recommendations_still_name_a_model_when_some_features_are_unpriced():
    pack = {
        "monthly_ai_budget_usd": None,
        "feature_runs": [{"model_id": "oss", "tier": "open_source"}],
        "stage_tables": [{"rows": [{"model_id": "oss", "token_basis": "estimated"}]}],
        "model_stack": [{"status": "requires_live_run", "model_id": None, "feature_id": "audio", "stage": "Scale"}],
        "stage_totals": [{
            **_single("oss", "Scale", 5000, "12", "unknown", complete=False),
            "feature_costs": {"text": "12", "audio": None},
            "note": "cost unknown for audio, so the total covers known features only",
        }],
    }
    pick = svc.tier_recommendations(pack)[1]
    assert pick["model_id"] == "oss" and "Cost unknown for audio" in pick["reason"]


def test_tier_recommendations_use_the_market_price_scope_and_the_furthest_stage_that_fits():
    pack = {
        "monthly_ai_budget_usd": "10",
        "openrouter_projection_tables": [{"rows": [
            {"model_id": "openrouter/oss", "tier": "open_source", "token_basis": "measured"}]}],
        "model_stack": [{"status": "no_candidate_passes", "model_id": None, "feature_id": "notes", "stage": "Scale"}],
        "stage_totals": [
            {**_single("openrouter/oss", "Prototype", 50, "4", "within"), "pricing_scope": "openrouter_listed_token_scenario"},
            {**_single("openrouter/oss", "Scale", 5000, "40", "over"), "pricing_scope": "openrouter_listed_token_scenario"},
            _single("ignored-actual", "Scale", 5000, "1", "within"),
        ],
    }
    picks = {item["tier"]: item for item in svc.tier_recommendations(pack)}
    assert picks["frontier"]["model_id"] is None
    assert picks["open_source"]["model_id"] == "openrouter/oss" and picks["open_source"]["stage"] == "Prototype"
    assert picks["open_source"]["budget_fit"] == "within" and picks["open_source"]["token_basis"] == "measured"


def test_outbox_hint_explains_a_partial_run_with_unpublished_evidence():
    assert svc.outbox_hint({"unpublished_evidence_ids": []}) == ""
    hint = svc.outbox_hint({"run_id": "ui-x", "unpublished_evidence_ids": ["a", "b"]})
    assert hint.startswith("2 evidence record(s) were not written back") and "retry_evidence.py" in hint and "--run-id ui-x" in hint
    assert "publisher was not running" in hint
    reached = svc.outbox_hint({"run_id": "ui-y", "unpublished_evidence_ids": ["a"],
                               "evidence_refs": [{"source_set": "evaluation_evidence", "record_id": "ui-y/s1"}]})
    assert "publisher accepted other records" in reached and "not running" not in reached and "--run-id ui-y" in reached
