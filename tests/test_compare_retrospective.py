import importlib.util, json, os, subprocess, sys
from decimal import Decimal
from pathlib import Path

import pytest

# The comparison runs on the AVL pre-build brief, which v4 removed with examples 1–3 (07 §10).
pytestmark = pytest.mark.skip(reason="shelved in v4")

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
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)

def _load(packs, brief=True):
    pack = cr.load_pack(json.loads(packs["complete"].read_text(encoding="utf-8")))
    actuals = json.loads(ACTUALS.read_text(encoding="utf-8"))
    return pack, actuals, (cr.load_brief(json.loads(BRIEF.read_text(encoding="utf-8"))) if brief else None)

def test_refuses_pack_that_is_not_complete_or_frozen(packs):
    with pytest.raises(cr.Refused):
        cr.load_pack(json.loads(packs["needs_input"].read_text(encoding="utf-8")))
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

def _expected_matches(pack, actuals):
    return [f"{inc['cause_class']}:{i}:{j}" for i, inc in enumerate(actuals["rework_incidents"])
            for j, r in enumerate(pack.risks) if r.cause_class.value == inc["cause_class"]]

def test_cause_class_pairs_are_class_level_matches_not_surfaced(packs):
    pack, actuals, _ = _load(packs)
    rc = cr.risk_cause_classes(pack, actuals)
    assert [m["match_id"] for m in rc["matches"]] == _expected_matches(pack, actuals)
    assert rc["class_level_matches"] == len(rc["matches"]) > 0
    assert "surfaced" not in rc and rc["reviewed"] is False
    m = rc["matches"][0]
    risk = pack.risks[int(m["match_id"].split(":")[2])]
    assert m["risk_description"] == risk.description and m["risk_triggered_by"] == risk.triggered_by
    assert m["incident"] == actuals["rework_incidents"][m["incident_index"]]
    report = cr.render(cr.compare(pack, actuals))
    assert report.count("class-level match — relevance requires human review") == len(rc["matches"])
    assert "Surfaced: not assessed" in report

def test_only_matches_judged_relevant_count_as_surfaced(packs, tmp_path):
    pack, actuals, _ = _load(packs)
    ids = _expected_matches(pack, actuals)
    compute = next(i for i in ids if i.startswith("compute_cost"))
    review = {"run_id": pack.run_id, "judgments": [{"match_id": i, "judgment": "relevant" if i == compute else "not_relevant",
                                                     "reviewer": "test"} for i in ids]}
    rc = cr.risk_cause_classes(pack, actuals, cr.load_review(review, pack))
    assert rc["surfaced"] == 1 and rc["surfaced_incidents"] == ["compute_cost"]
    assert rc["judged_not_relevant"] == len(ids) - 1 and rc["unreviewed"] == 0
    f = tmp_path / "review.json"; f.write_text(json.dumps(review), encoding="utf-8")
    p = _cli("--pack", packs["complete"], "--actuals", ACTUALS, "--reviewed", f)
    assert p.returncode == 0, p.stderr
    assert "Surfaced (matches a human judged relevant): 1 of 3 incidents (compute_cost)" in p.stdout
    assert p.stdout.count("class-level match — relevance requires human review") == len(ids)

def test_review_for_unknown_match_or_other_run_is_invalid_input(packs, tmp_path):
    for bad in ({"run_id": "other-run", "judgments": []},
                {"judgments": [{"match_id": "scope_change:9:9", "judgment": "relevant"}]},
                {"judgments": [{"match_id": "x", "judgment": "maybe"}]}):
        f = tmp_path / "bad.json"; f.write_text(json.dumps(bad), encoding="utf-8")
        p = _cli("--pack", packs["complete"], "--actuals", ACTUALS, "--reviewed", f)
        assert p.returncode == 2 and "invalid input" in p.stderr

def test_alternatives_outside_founder_list_need_the_brief(packs):
    pack, actuals, brief = _load(packs)
    al = cr.alternative_surfacing(pack, actuals, brief)
    assert al["outside_founder_list"] == ["replit-agent"] and al["founder_list_status"] == "unknown"
    assert cr.alternative_surfacing(pack, actuals, None)["outside_founder_list"] is None

def test_cli_report_has_no_savings_language(packs, tmp_path):
    p = _cli("--pack", packs["complete"], "--actuals", ACTUALS, "--brief", BRIEF, "--json-out", tmp_path / "c.json")
    assert p.returncode == 0, p.stderr
    assert not cr._SAVINGS.search(p.stdout) and not cr._SAVINGS.search((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert "agreement with history" in p.stdout and "SYNTHETIC" in p.stdout
    with pytest.raises(RuntimeError):
        cr.assert_no_savings_language("the tool would have saved $500")
