import importlib.util, os, subprocess, sys
import json
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal

import pytest

from app.adapters.validation import validate_select_one
from app.contracts import DecisionPack, ReadinessCheck, ReadinessResult
from app.adapters.sample import SampleDataLayer
from app.dispatch import Checkpoints
from tests.dispatch_fixtures import verified_profile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_live.py"
_spec = importlib.util.spec_from_file_location("smoke_live", SCRIPT)
smoke = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(smoke)

PLACEHOLDERS = {k: "your-placeholder" for k in ("ZETARIS_REST_URL", "ZETARIS_ORG_ID", "ZETARIS_API_KEY",
                                                 "METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN")}


def diagnose(models=None, **kwargs):
    models = models if models is not None else [verified_profile(model) for model in SampleDataLayer().read_models()]
    smoke.check_nightshift(models, allowance=Decimal("1"), checkpoints=Checkpoints(":memory:"), **kwargs)

def test_secret_values_are_redacted(monkeypatch):
    monkeypatch.setenv("SOME_API_KEY", "s3cr3t-value-123")
    monkeypatch.setenv("NIGHTSHIFT_TOKEN", "tok-abcdef")
    out = smoke.clean("401 for key s3cr3t-value-123 and token tok-abcdef\nsecond line")
    assert "s3cr3t-value-123" not in out and "tok-abcdef" not in out and "\n" not in out

def test_unconfigured_run_skips_everything_without_network_and_saves_report(tmp_path):
    env = {**os.environ, **PLACEHOLDERS}
    p = subprocess.run([sys.executable, str(SCRIPT), "--no-dotenv", "--output-dir", str(tmp_path)],
                       capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)
    live = [l for l in p.stdout.splitlines() if l.startswith(("| Zetaris |", "| Nightshift |"))]
    assert len(live) == 6 and all("| SKIP |" in l for l in live)          # H-MEM depends on the machine
    assert p.returncode == 1 and "incomplete" in p.stdout
    saved = Path(p.stdout.strip().splitlines()[-1].removeprefix("Saved ").strip())
    assert saved.parent == tmp_path and "| Component | Check | Result | Detail |" in saved.read_text(encoding="utf-8")
    evidence = json.loads(saved.with_suffix(".json").read_text())
    assert evidence["readiness"]["scope"] == "live_diagnostic" and evidence["readiness"]["status"] == "incomplete"
    assert evidence["counts"]["SKIP"] >= 6

class _FakeNightshift:
    """Stands in for NightshiftInference: offers the sample frontier and open-model routes, not the mid-tier one."""
    def __init__(self, trace=None, **kwargs):
        pass

    def list_models(self):
        return ["sample/frontier-placeholder", "sample/open-source-placeholder", "other/route"]

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60, max_tokens=None):
        usage = {} if model == "sample/open-source-placeholder" else \
            {"prompt_tokens": 12, "completion_tokens": 2, "completion_tokens_details": {"reasoning_tokens": 0}}
        return {"text": "OK", "requested_model": model, "resolved_model": model, "usage": usage,
                "route_id": "fixture-request"}

def test_nightshift_checks_report_usage_route_gaps_and_missing_usage(monkeypatch):
    import app.adapters.live_nightshift as ns
    monkeypatch.setattr(ns, "NightshiftInference", _FakeNightshift)
    monkeypatch.delenv("METERLESS_OPEN_MODEL", raising=False)
    smoke.rows.clear()
    diagnose()  # explicitly funded, synthetic verified billing profiles
    by = {r[1]: r for r in smoke.rows}
    assert by["GET /v1/models"][2] == "PASS" and "3 routes" in by["GET /v1/models"][3]
    fr = by["completion: frontier"]
    assert fr[2] == "PASS" and "resolved sample/frontier-placeholder" in fr[3] and "prompt=12 completion=2" in fr[3]
    assert "Zetaris price snapshot" in by["completion: mid-tier"][3] and by["completion: mid-tier"][2] == "SKIP"
    assert by["completion: open-source"][2] == "FAIL" and "unknown" in by["completion: open-source"][3]


@pytest.mark.parametrize("body", [ [[1]], {"rows": [[1]]}, {"data": [{"one": 1}]},
    {"result": {"rows": [{"1": "1"}]}}, {"records": [[1.0]]} ])
def test_select_one_accepts_only_a_recognized_single_cell(body):
    validate_select_one(body)


@pytest.mark.parametrize("body", [None, {}, {"status": "ok"}, {"rows": []}, {"rows": [[2]]},
    {"rows": [[True]]}, {"rows": [["not 1"]]}, {"rows": [[1, 2]]}, {"rows": [[1], [1]]},
    {"rows": [[1]], "error": "SQL denied"}, {"rows": [[1]], "errors": ["bad SQL"]},
    {"rows": [[1]], "success": False}, {"result": {"rows": [[1]], "status": "failed"}},
    {"rows": [1]}, {"rows": [{"value": 1, "other": 2}]}])
def test_http_200_is_insufficient_for_select_one(body):
    with pytest.raises(ValueError):
        validate_select_one(body)


@pytest.mark.parametrize("body,expected", [({"rows": [[1]]}, "PASS"), ({"rows": [[2]]}, "FAIL"),
                                         ({"error": "denied", "rows": [[1]]}, "FAIL")])
def test_smoke_validates_select_one_even_with_an_alternate_adapter(monkeypatch, body, expected):
    import app.adapters.live_zetaris as module

    class FakeZetaris:
        def __init__(self, **kwargs):
            pass

        def select_one(self):
            return body

        def read_models(self):
            return []

    monkeypatch.setattr(module, "ZetarisDataLayer", FakeZetaris)
    smoke.rows.clear()
    smoke.check_zetaris()
    assert smoke.rows[0][2] == expected
    assert smoke.rows[1][2] == ("FAIL" if expected == "PASS" else "SKIP")


@pytest.mark.parametrize("resolved,request_id,discovered,expected", [
    ("nvidia/nemotron-fixture", "request-1", True, "PASS"),
    ("meterless/auto", "request-1", True, "FAIL"),
    (None, "request-1", True, "FAIL"),
    ("provider/other", "request-1", True, "FAIL"),
    ("nvidia/nemotron-fixture", None, True, "FAIL"),
    ("nvidia/nemotron-fixture", "request-1", False, "FAIL"),
    ("provider/notnemotron", "request-1", True, "FAIL"),
])
def test_open_model_diagnostic_needs_explicit_corroborated_identity(monkeypatch, resolved, request_id, discovered, expected):
    import app.adapters.live_nightshift as module

    class FakeNightshift(_FakeNightshift):
        def list_models(self):
            return super().list_models() + (["nvidia/nemotron-fixture"] if discovered else [])

        def complete(self, **kwargs):
            if kwargs["model"] != "nvidia/nemotron-fixture":
                return super().complete(**kwargs)
            return {"text": "OK", "requested_model": kwargs["model"], "resolved_model": resolved,
                    "route_id": request_id, "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    monkeypatch.setattr(module, "NightshiftInference", FakeNightshift)
    monkeypatch.delenv("METERLESS_OPEN_MODEL", raising=False)
    smoke.rows.clear()
    models = [verified_profile(model) for model in SampleDataLayer().read_models()]
    models = [model.model_copy(update={"required": False}) if model.tier == "open_source" else model for model in models]
    models.append(models[-1].model_copy(update={"model_id": "nvidia/nemotron-fixture", "required": True}))
    diagnose(models)
    assert next(row for row in smoke.rows if row[1] == "completion: open-source")[2] == expected


@pytest.mark.parametrize("routes", [[], "a", [""], [None], ["a", "a"]])
def test_smoke_stops_completions_after_invalid_discovery(monkeypatch, routes):
    import app.adapters.live_nightshift as module

    class FakeNightshift(_FakeNightshift):
        def list_models(self):
            return routes

        def complete(self, **kwargs):
            pytest.fail("invalid discovery must not dispatch a completion")

    monkeypatch.setattr(module, "NightshiftInference", FakeNightshift)
    smoke.rows.clear()
    diagnose()
    assert smoke.rows[0][2] == "FAIL" and all(row[2] == "SKIP" for row in smoke.rows[1:])


@pytest.mark.parametrize("usage", ["bad usage", {"prompt_tokens": True, "completion_tokens": 1},
    {"prompt_tokens": -1, "completion_tokens": 1},
    {"prompt_tokens": 1, "completion_tokens": 1, "completion_tokens_details": [1]},
    {"prompt_tokens": 1, "completion_tokens": 1, "completion_tokens_details": {"reasoning_tokens": 2}}])
def test_bad_usage_fails_each_completion_without_hiding_later_checks(monkeypatch, usage):
    import app.adapters.live_nightshift as module

    class FakeNightshift(_FakeNightshift):
        def list_models(self):
            return super().list_models() + ["sample/mid-tier-placeholder"]

        def complete(self, **kwargs):
            return {"text": "OK", "requested_model": kwargs["model"], "resolved_model": "nvidia/nemotron-fixture",
                    "route_id": "request-1", "usage": usage}

    monkeypatch.setattr(module, "NightshiftInference", FakeNightshift)
    monkeypatch.delenv("METERLESS_OPEN_MODEL", raising=False)
    smoke.rows.clear()
    diagnose()
    assert len(smoke.rows) == 4 and smoke.rows[1][2] == "FAIL"
    assert all(row[2] == "SKIP" for row in smoke.rows[2:])  # unknown charge stops further paid calls


@pytest.mark.parametrize("status,optional,expected", [("pass", False, "ready"), ("fail", False, "not_ready"),
    ("skip", False, "incomplete"), ("not_verified", False, "not_verified"),
    ("skip", True, "ready"), ("fail", True, "ready")])
def test_shared_readiness_requires_all_required_checks(status, optional, expected):
    result = ReadinessResult(checks=[ReadinessCheck(name="required", status="pass"),
                                   ReadinessCheck(name="second", status=status, required=not optional)])
    assert result.status == expected
    assert result.model_dump(mode="json")["checks"][1]["required"] == (not optional)
    assert ReadinessResult.model_validate(result.model_dump()).status == expected


def test_empty_missing_or_forged_readiness_cannot_report_ready():
    assert ReadinessResult().status == "not_verified"
    assert ReadinessResult.model_validate({"status": "ready"}).status == "not_verified"
    smoke.rows.clear()
    smoke.record("Zetaris", "SELECT 1", "PASS", "fixture")
    assert smoke.readiness_result().status == "not_verified"
    with pytest.raises(ValueError, match="unique"):
        ReadinessResult(checks=[ReadinessCheck(name="same", status="pass"), ReadinessCheck(name="same", status="pass")])


def test_completed_pack_is_not_sponsor_readiness():
    pack = DecisionPack(run_id="fixture", project_id="fixture", execution_mode="sample", status="complete")
    assert pack.readiness.status == "not_verified" and len(pack.readiness.checks) == 4
    assert all(check.required and check.status == "not_verified" for check in pack.readiness.checks)


@pytest.mark.parametrize("status,expected,exit_code", [("PASS", "ready", 0), ("SKIP", "incomplete", 1),
                                                      ("FAIL", "not_ready", 1)])
def test_report_exit_tracks_all_required_checks_and_resets_previous_rows(tmp_path, monkeypatch, capsys, status, expected, exit_code):
    monkeypatch.setattr(smoke, "load_dotenv", lambda *a, **k: pytest.fail("dotenv loading is disabled"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "traces"))
    smoke.rows[:] = [("stale", "previous failure", "FAIL", "must be cleared")]

    def zetaris(trace=None):
        for component, check in smoke.REQUIRED:
            if component == "Zetaris":
                smoke.record(component, check, status, "synthetic fixture only")

    def nightshift(models, trace=None, **kwargs):
        for component, check in smoke.REQUIRED:
            if component == "Nightshift":
                smoke.record(component, check, status, "synthetic fixture only")

    monkeypatch.setattr(smoke, "check_zetaris", zetaris)
    monkeypatch.setattr(smoke, "check_nightshift", nightshift)
    monkeypatch.setattr(smoke, "check_hmem", lambda: smoke.record("H-MEM", "bridge self-test", status, "synthetic fixture only"))
    assert smoke.main(["--no-dotenv", "--output-dir", str(tmp_path)]) == exit_code
    evidence = json.loads(next(tmp_path.glob("smoke-*.json")).read_text())
    assert evidence["readiness"]["status"] == expected and len(evidence["readiness"]["checks"]) == 7
    assert "End-to-end sponsor readiness remains unverified" in capsys.readouterr().out


@pytest.fixture
def fake_bridge(tmp_path, monkeypatch):
    from app.engines.hmem import bridge
    monkeypatch.setattr(bridge, "HERE", tmp_path)
    monkeypatch.setattr(bridge, "BRIDGE", tmp_path / "bridge.mjs")
    monkeypatch.setattr(bridge, "PIN", tmp_path / "PINNED_REVISION")
    bridge.BRIDGE.touch()
    bridge.PIN.write_text("synthetic-fixture-revision")
    (tmp_path / "reference" / "src").mkdir(parents=True)
    (tmp_path / "reference" / "src" / "index.ts").touch()
    (tmp_path / "reference" / "node_modules" / "tsx").mkdir(parents=True)
    return bridge


@pytest.mark.parametrize("stdout,exit_code,expected", [('{"status":"ok","engine_revision":"synthetic-fixture-revision"}', 0, True),
    ('{\n "status" : "ok", "engine_revision": "synthetic-fixture-revision"\n}', 0, True), ('{"status":"ok"}', 1, False),
    ('{"status":"failed","message":"\\\"status\\\": \\\"ok\\\""}', 0, False),
    ("{'status': 'ok'}", 0, False), ('log: {"status": "ok"}', 0, False), ('[]', 0, False)])
def test_bridge_selftest_parses_json_status_not_a_substring(fake_bridge, monkeypatch, stdout, exit_code, expected):
    monkeypatch.setattr(fake_bridge.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=exit_code, stdout=stdout, stderr="fixture failure"))
    assert fake_bridge.offline_bridge_available() is expected
    smoke.rows.clear()
    smoke.check_hmem()
    assert smoke.rows[0][2] == ("PASS" if expected else "FAIL")


def test_missing_bridge_is_skipped_and_not_ready(fake_bridge):
    fake_bridge.PIN.unlink()
    assert not fake_bridge.offline_bridge_available()
    smoke.rows.clear()
    smoke.check_hmem()
    assert smoke.rows[0][2] == "SKIP" and smoke.readiness_result().status == "incomplete"


@pytest.mark.parametrize("funded,verified", [(False, True), (True, False)])
def test_diagnostics_never_bypass_allowance_or_verified_billing(monkeypatch, funded, verified):
    import app.adapters.live_nightshift as module
    class FakeNightshift(_FakeNightshift):
        def complete(self, **kwargs):
            pytest.fail("diagnostic dispatched without an allowance and verified billing")
    monkeypatch.setattr(module, "NightshiftInference", FakeNightshift)
    models = SampleDataLayer().read_models()
    if verified:
        models = [verified_profile(model) for model in models]
    smoke.rows.clear()
    smoke.check_nightshift(models, allowance=Decimal("1") if funded else Decimal("0"), checkpoints=Checkpoints(":memory:"))
    assert all(row[2] == "SKIP" for row in smoke.rows[1:])


def test_zero_allowance_disables_diagnostic_generations_even_for_zero_tariffs(monkeypatch):
    import app.adapters.live_nightshift as module
    class FakeNightshift(_FakeNightshift):
        def complete(self, **kwargs):
            pytest.fail("zero allowance must disable diagnostic generations")
    monkeypatch.setattr(module,"NightshiftInference",FakeNightshift)
    models = [verified_profile(model) for model in SampleDataLayer().read_models()]
    models = [model.model_copy(update={"rates": [rate.model_copy(update={"usd_per_unit": Decimal(0)}) for rate in model.rates]}) for model in models]
    smoke.rows.clear()
    smoke.check_nightshift(models, checkpoints=Checkpoints(":memory:"))
    assert all(row[2] == "SKIP" and "disabled" in row[3] for row in smoke.rows[1:])


def test_funded_diagnostics_share_dispatch_accounting_and_refuse_duplicate_run(monkeypatch):
    import app.adapters.live_nightshift as module
    calls = []
    models = [verified_profile(model) for model in SampleDataLayer().read_models() if model.tier != "frontier" or model.required]
    frontier = verified_profile(SampleDataLayer().read_models()[0])
    models.append(frontier)
    models = [model.model_copy(update={"model_id": "openrouter/google/gemma-4-31b-it:free"}) if model.tier == "open_source" else model for model in models]
    routes = [model.model_id for model in models]
    class FakeNightshift(_FakeNightshift):
        def list_models(self):
            return routes
        def complete(self, **kwargs):
            calls.append(kwargs)
            return {"text": "OK", "requested_model": kwargs["model"], "resolved_model": kwargs["model"],
                    "route_id": "provider-fixture", "usage": {"prompt_tokens": 12, "completion_tokens": 2}}
    monkeypatch.setattr(module, "NightshiftInference", FakeNightshift)
    monkeypatch.delenv("METERLESS_OPEN_MODEL", raising=False)
    ledger = Checkpoints(":memory:")
    smoke.rows.clear()
    smoke.check_nightshift(models,allowance=Decimal("1"),checkpoints=ledger,run_id="diagnostic-fixture")
    assert len(calls) == 3 and all(row[2] == "PASS" for row in smoke.rows)
    operations = ledger.operations("diagnostic-fixture")
    assert len(operations) == 3 and all(record.role == "Diagnostic" and record.actual_usd > 0 for record in operations)
    smoke.rows.clear()
    smoke.check_nightshift(models,allowance=Decimal("1"),checkpoints=ledger,run_id="diagnostic-fixture")
    assert len(calls) == 3 and all(row[2] == "SKIP" for row in smoke.rows[1:])


@pytest.mark.parametrize("allowance", ["-1", "2", "NaN"])
def test_diagnostic_allowance_is_validated_before_dotenv_or_dispatch(tmp_path, monkeypatch, allowance):
    monkeypatch.setattr(smoke,"load_dotenv",lambda *a,**k: pytest.fail("invalid allowance reached setup"))
    with pytest.raises(SystemExit) as exc:
        smoke.main(["--max-spend-usd",allowance,"--output-dir",str(tmp_path)])
    assert exc.value.code == 2
