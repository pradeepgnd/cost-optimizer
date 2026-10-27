"""Two-model validation must not authorize an unverified third candidate."""
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from app.contracts import RunState
from app.dispatch import StopRun

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_m08_gate", ROOT / "scripts" / "check_m08_gate.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def test_two_model_gate_excludes_open_route_from_dispatch_readiness(tmp_path, monkeypatch):
    # The gate loads the developer's .env and sets ZETARIS_BINDINGS_FILE; keep both out of the shared test process.
    monkeypatch.setattr(gate, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("ZETARIS_BINDINGS_FILE", "")
    selected = json.loads((ROOT / "data/source_examples/routes.selected.json").read_text())
    # The shipped map no longer pins an open route; this scenario needs one, so add it to a private copy.
    selected["routes"].append({"catalog_id": "fixture/open:free", "route_id": "openrouter/fixture/open:free", "tier": "open_source"})
    current = tmp_path / "routes.selected.json"
    current.write_text(json.dumps(selected))
    monkeypatch.setattr(gate, "SELECTED", current)
    routes = {entry["tier"]: entry["route_id"] for entry in selected["routes"]}
    snapshot_id = "a" * 24
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({"snapshot_id": snapshot_id}))
    monkeypatch.setenv("ZETARIS_BINDINGS_FILE", str(bindings))
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text(json.dumps({"bundle_id": snapshot_id,
                                                      "route_map": {**selected, "mapping_status": "discovery_observed"}}))
    payload = json.loads((ROOT / "input_examples/example_3.json").read_text())
    payload.update(run_id="two-model-gate", sampling_profile="validation",
                   candidate_tiers=["frontier", "mid_tier"])
    request = tmp_path / "request.json"
    request.write_text(json.dumps(payload))

    profiles = [SimpleNamespace(model_id=route, source=SimpleNamespace(status=SimpleNamespace(value="unknown")),
                                dispatch_policy=None) for route in routes.values()]
    monkeypatch.setattr(gate, "ZetarisDataLayer", lambda: SimpleNamespace(read_models=lambda: profiles))
    monkeypatch.setattr(gate, "NightshiftInference", lambda: SimpleNamespace(list_models=lambda: list(routes.values())))
    monkeypatch.setenv("METERLESS_MODEL", routes["mid_tier"])
    monkeypatch.setenv("METERLESS_CRITIC_MODEL", routes["frontier"])

    def bound(profile, *args):
        if profile.model_id == routes["open_source"]:
            raise StopRun(RunState.partial, "open-source route tariff unverified")
        return None, Decimal("0.01"), None, None, None

    monkeypatch.setattr(gate, "request_bound", bound)
    subset = gate.check(bindings, bundle, request)
    assert subset["status"] == "ready_for_bounded_validation"
    assert subset["candidate_tiers"] == ["frontier", "mid_tier"]
    assert subset["selection_matches_current"]
    assert not next(row for row in subset["routes"] if row["role"] == "open_source")["required_for_run"]
    assert gate.check(bindings, bundle)["status"] == "incomplete"


def test_gate_reads_bundle_passed_with_bundle_flag_when_bindings_live_elsewhere(tmp_path, monkeypatch):
    # README layout: bindings in one folder, bundle in another. Without --bundle the gate must say it fell back.
    monkeypatch.setattr(gate, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("ZETARIS_BINDINGS_FILE", "")
    selected = json.loads((ROOT / "data/source_examples/routes.selected.json").read_text())
    routes = [entry["route_id"] for entry in selected["routes"]]
    snapshot_id = "b" * 24
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({"snapshot_id": snapshot_id}))
    bundle = tmp_path / "openrouter" / "bundles" / snapshot_id
    bundle.mkdir(parents=True)
    (bundle / "manifest.json").write_text(json.dumps({"bundle_id": snapshot_id,
                                                      "route_map": {**selected, "mapping_status": "discovery_observed"}}))
    profiles = [SimpleNamespace(model_id=route, source=SimpleNamespace(status=SimpleNamespace(value="verified")),
                                dispatch_policy=object()) for route in routes]
    monkeypatch.setattr(gate, "ZetarisDataLayer", lambda: SimpleNamespace(read_models=lambda: profiles))
    monkeypatch.setattr(gate, "NightshiftInference", lambda: SimpleNamespace(list_models=lambda: routes))
    monkeypatch.setattr(gate, "request_bound", lambda *args: (None, Decimal("0"), None, None, None))
    monkeypatch.setenv("METERLESS_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    monkeypatch.setenv("METERLESS_CRITIC_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

    fallback = gate.check(bindings)
    assert fallback["status"] == "incomplete"
    assert fallback["mapping_status"] == "planned"
    assert fallback["route_map_source"].startswith("committed_fallback")

    with_bundle = gate.check(bindings, bundle)
    assert with_bundle["status"] == "ready_for_bounded_dispatch"
    assert with_bundle["route_map_source"] == "bundle_manifest"
