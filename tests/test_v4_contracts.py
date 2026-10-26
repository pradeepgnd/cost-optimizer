"""M01: validate the public request before setup, dispatch or cost arithmetic."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

from app.adapters.sample import RulePolicyInference, SampleDataLayer, SampleMemory
from app.contracts import (
    BuildConstraints, DecisionPack, EvidenceStatus, FeatureProfile, ModelPricingTerms,
    Rate, RunRequest, RunState, Stage, TokenUsage,
)
from app.controller import Checkpoints, Controller
from app.trace import Trace

ROOT = Path(__file__).resolve().parents[1]


def request_data():
    return {
        "schema_version": "1.1", "project_id": "contract-project", "run_id": "contract-run",
        "sample_mode": True, "evaluation_approved": True, "max_spend_usd": "0",
        "brief": {
            "brief_id": "brief-contract", "brief_version": "1",
            "product_concept": "Turn meeting notes into summaries and action lists.",
            "target_user": "Project leads",
            "ai_features": [
                {"feature_id": "summary", "description": "Summarize notes", "example_input": "Review on Friday.",
                 "mode": "interactive", "uses_per_user_month": "4", "expected_output_words": 100},
                {"feature_id": "actions", "description": "Extract actions", "example_input": "Alex will review on Friday.",
                 "mode": "background", "uses_per_user_month": "2", "expected_output_words": 50},
            ],
        },
    }


def sample_pack(data, tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    request = RunRequest.model_validate(data)
    checkpoints = Checkpoints(str(tmp_path / "runs.db"))
    try:
        controller = Controller(SampleDataLayer(), RulePolicyInference(), SampleMemory(),
                                Trace(request.run_id, "sample", echo=False), "sample", checkpoints)
        return controller.run(request)
    finally:
        checkpoints.conn.close()


def test_operating_only_request_completes_with_unknown_build_panel(tmp_path, monkeypatch):
    request = RunRequest.model_validate(request_data())
    assert request.brief.features_v1 == []
    assert request.brief.constraints.status == EvidenceStatus.assumed
    pack = sample_pack(request_data(), tmp_path, monkeypatch)
    assert pack.status == RunState.complete and len(pack.stage_tables) == 2
    assert pack.build_panel.ranked_approach_ids == []
    assert all(ledger.base_build_cost.base is None for ledger in pack.build_ledgers)
    assert any("build" in reason.lower() and "unknown" in reason.lower() for reason in pack.build_panel.reasons)


@pytest.mark.parametrize("version", [None, "1.0", "1.1"])
def test_schema_migration_keeps_controls_and_round_trips(version):
    data = request_data()
    if version is None:
        data.pop("schema_version")
    else:
        data["schema_version"] = version
    data["brief"].update(monthly_ai_budget_usd="300.25", switch_threshold_usd="50.50")
    request = RunRequest.model_validate(data)
    assert request.schema_version == "1.1"
    assert request.brief.monthly_ai_budget_usd == Decimal("300.25")
    assert request.brief.switch_threshold_usd == Decimal("50.50")
    assert RunRequest.model_validate_json(request.model_dump_json()) == request


@pytest.mark.parametrize("version", ["0.9", "2.0"])
def test_unsupported_schema_version_is_rejected(version):
    data = request_data()
    data["schema_version"] = version
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


def test_legacy_schema_cannot_bypass_validation():
    data = request_data()
    data.update(schema_version="1.0", max_spend_usd="1000")
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("tiers,profile", [(["frontier", "mid_tier"], "production"),
                                            (["frontier"], "validation"),
                                            (["frontier", "frontier"], "validation"),
                                            (["frontier", "unknown"], "validation")])
def test_validation_candidate_subset_requires_two_unique_known_tiers(tiers, profile):
    data = request_data()
    data.update(candidate_tiers=tiers, sampling_profile=profile)
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


def test_validation_candidate_subset_survives_request_export():
    data = request_data()
    data.update(candidate_tiers=["frontier", "mid_tier"], sampling_profile="validation")
    request = RunRequest.model_validate(data)
    assert RunRequest.model_validate_json(request.model_dump_json()).candidate_tiers == ["frontier", "mid_tier"]


def test_controls_survive_pack_export_and_threshold_reaches_tables(tmp_path, monkeypatch):
    data = request_data()
    data["brief"].update(monthly_ai_budget_usd="300.25", switch_threshold_usd="50.50")
    pack = sample_pack(data, tmp_path, monkeypatch)
    restored = DecisionPack.model_validate_json(pack.model_dump_json())
    assert restored.schema_version == "1.1"
    assert restored.monthly_ai_budget_usd == Decimal("300.25")
    assert restored.switch_threshold_usd == Decimal("50.50")
    assert {table.threshold_usd for table in pack.stage_tables} == {Decimal("50.50")}
    gaps = {gap.field: gap.status for gap in pack.evidence_gaps}
    assert gaps["monthly_ai_budget_usd"] == gaps["switch_threshold_usd"] == EvidenceStatus.assumed


@pytest.mark.parametrize("count", [0, 1, 6])
def test_public_request_requires_two_to_five_features(count):
    data = request_data()
    template = data["brief"]["ai_features"][0]
    data["brief"]["ai_features"] = [{**template, "feature_id": f"f{i}"} for i in range(count)]
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


def test_five_features_are_valid_and_low_level_single_feature_is_supported():
    data = request_data()
    template = data["brief"]["ai_features"][0]
    data["brief"]["ai_features"] = [{**template, "feature_id": f"f{i}"} for i in range(5)]
    assert len(RunRequest.model_validate(data).brief.ai_features) == 5
    assert FeatureProfile.model_validate(template).feature_id == "summary"


@pytest.mark.parametrize("location", ["feature", "build_feature", "stage", "check"])
def test_duplicate_identifiers_are_rejected(location):
    data = request_data()
    brief = data["brief"]
    if location == "feature":
        brief["ai_features"][1]["feature_id"] = "summary"
    elif location == "build_feature":
        feature = {"feature_id": "build", "title": "Build", "size_class": "S"}
        brief["features_v1"] = [feature, deepcopy(feature)]
    elif location == "stage":
        brief["growth_stages"] = [{"name": "Launch", "active_users": 50}, {"name": " Launch ", "active_users": 500}]
    else:
        check = {"check_id": "same", "description": "Check this", "kind": "human_review"}
        brief["ai_features"][0]["rubric_checks"] = [check, deepcopy(check)]
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("field,bad", [("run_id", "../outside"), ("project_id", " "), ("run_id", "")])
def test_run_and_project_ids_are_valid_before_file_creation(field, bad):
    data = request_data()
    data[field] = bad
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


def test_explicitly_empty_stages_are_not_silently_replaced_with_defaults():
    data = request_data()
    data["brief"]["growth_stages"] = []
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("field", ["product_concept", "target_user"])
@pytest.mark.parametrize("bad", ["", "   ", None])
def test_required_founder_text_is_nonblank(field, bad):
    data = request_data()
    data["brief"][field] = bad
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("field", ["feature_id", "description", "example_input"])
def test_required_feature_text_is_nonblank(field):
    data = request_data()
    data["brief"]["ai_features"][0][field] = "  "
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("field,bad", [
    ("uses_per_user_month", "-1"), ("uses_per_user_month", "NaN"),
    ("uses_per_user_month", "Infinity"), ("calls_per_use", "0"), ("calls_per_use", "-1"),
    ("revenue_per_use", "-0.01"), ("audio_seconds_per_use", "-1"),
    ("static_prefix_tokens", -1), ("static_prefix_tokens", True),
    ("expected_output_words", -1), ("output_reuse_rate", "1.01"), ("distinct_outputs", 0),
])
def test_invalid_feature_numbers_are_rejected(field, bad):
    data = request_data()
    data["brief"]["ai_features"][0][field] = bad
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("field,bad", [("paying_fraction", "-0.1"), ("paying_fraction", "1.1"),
                                     ("subscription_price_usd", "-1"), ("workflows_per_user_month", "NaN")])
def test_invalid_usage_and_revenue_inputs_are_rejected(field, bad):
    data = request_data()
    data["brief"]["usage"] = {field: bad}
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("model,kwargs", [
    (Stage, {"name": "Launch", "active_users": -1}),
    (Stage, {"name": "Launch", "active_users": float("inf")}),
    (BuildConstraints, {"cash_budget_usd": "-1"}),
    (BuildConstraints, {"time_budget_weeks": "NaN"}),
    (BuildConstraints, {"team_size": 0}),
    (ModelPricingTerms, {"cache_ttl_minutes": "0"}),
    (ModelPricingTerms, {"batch_discount": "1.1"}),
    (ModelPricingTerms, {"cache_min_prefix_tokens": -1}),
    (ModelPricingTerms, {"long_context_threshold_tokens": -1}),
    (TokenUsage, {"input_tokens": -1, "output_tokens": 1, "basis": "measured", "method": "API usage"}),
    (TokenUsage, {"input_tokens": 1, "output_tokens": "Infinity", "basis": "measured", "method": "API usage"}),
    (TokenUsage, {"input_tokens": 1, "output_tokens": 1, "reasoning_tokens": -1, "basis": "measured", "method": "API usage"}),
])
def test_invalid_economic_inputs_are_rejected(model, kwargs):
    with pytest.raises(ValidationError):
        model(**kwargs)


@pytest.mark.parametrize("bad", ["-0.1", "NaN", "Infinity"])
def test_invalid_rate_is_rejected(bad):
    with pytest.raises(ValidationError):
        Rate(category="input_tokens", unit="1M tokens", usd_per_unit=bad, status="assumed",
             source={"source_set": "pricing_snapshots", "record_id": "rate", "version": "1"})


@pytest.mark.parametrize("bad", ["-1", "25.01", "1000", "NaN", "Infinity"])
def test_evaluation_spend_ceiling_is_validated(bad):
    data = request_data()
    data["max_spend_usd"] = bad
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


@pytest.mark.parametrize("field", ["monthly_ai_budget_usd", "switch_threshold_usd"])
@pytest.mark.parametrize("bad", ["-1", "NaN", "Infinity"])
def test_invalid_founder_controls_are_rejected(field, bad):
    data = request_data()
    data["brief"][field] = bad
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


def test_zero_volume_prices_revenue_and_control_values_are_valid(tmp_path, monkeypatch):
    data = request_data()
    data["brief"].update(monthly_ai_budget_usd="0", switch_threshold_usd="0",
                         growth_stages=[{"name": "Empty", "active_users": 0}])
    data["brief"]["ai_features"][0].update(uses_per_user_month="0", revenue_per_use="0", expected_output_words=0)
    pack = sample_pack(data, tmp_path, monkeypatch)
    assert pack.status == RunState.complete and pack.spend_usd == 0
    assert all(row.gross_monthly_usd == 0 for table in pack.stage_tables for row in table.rows)
    assert TokenUsage(input_tokens=0, output_tokens=0, basis="measured", method="API usage").output_tokens == 0


@pytest.mark.parametrize("location", ["request", "brief", "feature", "constraints", "usage", "stage", "check"])
def test_unknown_public_fields_are_rejected(location):
    data = request_data()
    if location == "request":
        data["monthly_ai_budget_usd"] = "300"  # Supported location is inside brief.
    elif location == "brief":
        data["brief"]["monthly_ai_buget_usd"] = "300"
    elif location == "feature":
        data["brief"]["ai_features"][0]["calls_per_ues"] = 2
    elif location == "constraints":
        data["brief"]["constraints"] = {"cash_buget_usd": "500"}
    elif location == "usage":
        data["brief"]["usage"] = {"paying_faction": "0.1"}
    elif location == "stage":
        data["brief"]["growth_stages"] = [{"name": "Launch", "active_users": 50, "users": 100}]
    else:
        data["brief"]["ai_features"][0]["rubric_checks"] = [{"check_id": "c", "description": "Check", "critcal": False}]
    with pytest.raises(ValidationError):
        RunRequest.model_validate(data)


def test_defaults_are_assumed_nulls_unknown_and_provenance_survives_round_trip():
    data = request_data()
    data["brief"]["ai_features"][0]["field_status"] = {"calls_per_use": "verified", "example_input": "verified"}
    request = RunRequest.model_validate(data)
    brief = request.brief
    assert brief.field_status["switch_threshold_usd"] == EvidenceStatus.assumed
    assert brief.field_status["monthly_ai_budget_usd"] == EvidenceStatus.unknown
    assert brief.constraints.field_status["devops_capacity"] == EvidenceStatus.assumed
    feature = brief.ai_features[0]
    assert feature.field_status["calls_per_use"] == EvidenceStatus.assumed  # Not supplied; cannot promote a default.
    assert feature.field_status["modality"] == EvidenceStatus.assumed
    assert feature.field_status["revenue_per_use"] == EvidenceStatus.unknown
    assert feature.field_status["uses_per_user_month"] == EvidenceStatus.assumed
    assert feature.field_status["example_input"] == EvidenceStatus.verified  # Explicit evidence stays explicit.
    restored = RunRequest.model_validate_json(request.model_dump_json())
    assert restored == request


def test_invalid_cli_request_fails_before_adapter_setup(tmp_path, monkeypatch):
    import run
    data = request_data()
    data["brief"]["ai_features"][0]["uses_per_user_month"] = "-1"
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(run, "load_dotenv", lambda: None)
    monkeypatch.setattr(sys, "argv", ["run.py", "--input", str(source), "--output", str(output)])
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid input reached adapter setup")
    monkeypatch.setattr(run, "build_controller", forbidden)
    assert run.main() == 2
    assert json.loads(output.read_text())["code"] == "INVALID_INPUT"
    assert not (tmp_path / "logs").exists()


@pytest.mark.parametrize("number", [1, 2, 3])
def test_bundled_examples_use_current_schema(number):
    data = json.loads((ROOT / "input_examples" / f"example_{number}.json").read_text())
    assert data["schema_version"] == "1.1"
    assert RunRequest.model_validate(data).schema_version == "1.1"


@pytest.mark.parametrize("picked,ok", [(["a/x"], True), (["a/x", "b/y", "c/z"], True), ([], False),
                                       (["a/x", "a/x"], False), (["a", "b", "c", "d"], False), ([" "], False)])
def test_candidate_models_accepts_one_to_three_unique_routes(picked, ok):
    from app.ui_service import load_template
    request = {**load_template("example_3"), "candidate_models": picked}
    if ok:
        assert RunRequest.model_validate(request).candidate_models == picked
    else:
        with pytest.raises(ValidationError):
            RunRequest.model_validate(request)
    assert "candidate_models" not in RunRequest.model_validate(load_template("example_3")).model_dump(mode="json")
