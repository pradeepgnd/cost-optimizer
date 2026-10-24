import importlib.util, json, os, subprocess, sys
from decimal import Decimal
from pathlib import Path

import pytest

from app.contracts import DecisionPack, EvidenceGap, EvidenceStatus

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_retrospective.py"
ACTUALS = ROOT / "data" / "sample" / "retrospective_actuals_SYNTHETIC.json"
BRIEF = ROOT / "input_examples" / "example_1.json"

_spec = importlib.util.spec_from_file_location("compare_retrospective", SCRIPT)
cr = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cr)

def _sample_pack(example, tmp):
    env = {**os.environ, "SAMPLE_MODE": "true", "LOG_DIR": str(tmp / "logs"), "RUNS_DB": str(tmp / "runs.db")}
    out = tmp / f"{example}.json"
    subprocess.run([sys.executable, "run.py", "--input", f"input_examples/{example}.json", "--output", str(out)],
                   capture_output=True, text=True, env=env, cwd=ROOT, check=True)
    return out

@pytest.fixture(scope="module")
def packs(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("packs")
    return {"complete": _sample_pack("example_1", tmp), "needs_input": _sample_pack("example_3", tmp)}

def _cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, cwd=ROOT)

def _load(packs, brief=True):
    pack = cr.load_pack(json.loads(packs["complete"].read_text()))
    actuals = json.loads(ACTUALS.read_text())
    return pack, actuals, (cr.load_brief(json.loads(BRIEF.read_text())) if brief else None)

def test_refuses_pack_that_is_not_complete_or_frozen(packs):
    with pytest.raises(cr.Refused):
        cr.load_pack(json.loads(packs["needs_input"].read_text()))
    p = _cli("--pack", packs["needs_input"], "--actuals", ACTUALS)
    assert p.returncode == 4 and "refused" in p.stderr and p.stdout == ""

def test_approach_and_build_range_against_synthetic_actuals(packs):
    pack, actuals, _ = _load(packs)
    r = cr.compare(pack, actuals)
    assert r["approach_coverage"]["named"] is True
    br, total = r["build_range"], Decimal(str(actuals["total_spend"]["amount"]))
    assert br["result"] == "above_high"
    assert br["pct_beyond"] == ((total - br["high"]) / br["high"] * 100).quantize(Decimal("0.1"))

def test_checkpoint_fraction_is_threshold_over_actual_total(packs):
    pack, actuals, _ = _load(packs)
    ct = cr.checkpoint_timing(pack, actuals)
    total = Decimal(str(actuals["total_spend"]["amount"]))
    assert ct["result"] == "ok" and ct["first_fired"] == 1 and len(ct["gates"]) == 3
    for g in ct["gates"]:
        assert g["fired"] and g["fraction_of_actual_total"] == (g["threshold_base"] / total * 100).quantize(Decimal("0.1"))
        cum = sum(Decimal(str(m["spend"])) for m in actuals["monthly_profile"] if m["month"] <= g["month"])
        assert cum >= g["threshold_base"]

def test_risk_surfacing_exact_phrase_only(packs):
    pack, actuals, _ = _load(packs)
    assert cr.risk_surfacing(pack, actuals)["named"] == []
    flagged = pack.model_copy(update={"evidence_gaps": pack.evidence_gaps + [
        EvidenceGap(field="hosting", status=EvidenceStatus.unknown, note="scaling of backtest compute not assessed")]})
    rs = cr.risk_surfacing(flagged, actuals)
    assert rs["named"] == ["scaling"] and rs["where"]["scaling"] == ["evidence_gaps"]
    assert set(rs["missed"]) == {"platform_limitation", "requirements_change"}

def test_alternatives_outside_founder_list_need_the_brief(packs):
    pack, actuals, brief = _load(packs)
    al = cr.alternative_surfacing(pack, actuals, brief)
    assert al["outside_founder_list"] == ["replit-agent"] and al["founder_list_status"] == "unknown"
    assert cr.alternative_surfacing(pack, actuals, None)["outside_founder_list"] is None

def test_cli_report_has_no_savings_language(packs, tmp_path):
    p = _cli("--pack", packs["complete"], "--actuals", ACTUALS, "--brief", BRIEF, "--json-out", tmp_path / "c.json")
    assert p.returncode == 0, p.stderr
    assert not cr._SAVINGS.search(p.stdout) and not cr._SAVINGS.search((tmp_path / "c.json").read_text())
    assert "agreement with history" in p.stdout and "SYNTHETIC" in p.stdout
    with pytest.raises(RuntimeError):
        cr.assert_no_savings_language("the tool would have saved $500")
