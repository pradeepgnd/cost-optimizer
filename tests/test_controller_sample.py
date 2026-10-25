import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _run(example, tmp_path, env_extra=None, payload=None):
    env = {**os.environ, "SAMPLE_MODE": "true", "LOG_DIR": str(tmp_path / "logs"), "RUNS_DB": str(tmp_path / "runs.db")}
    env.update(env_extra or {})
    if payload is not None:
        example = str(tmp_path / "in.json"); Path(example).write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out.json"
    p = subprocess.run([sys.executable, "run.py", "--input", example, "--output", str(out)], capture_output=True, text=True, env=env, cwd=ROOT)
    return p, json.loads(out.read_text(encoding="utf-8")), tmp_path / "logs"

def _example(n):
    return json.loads((ROOT / "input_examples" / f"example_{n}.json").read_text(encoding="utf-8"))

def _trace(logs, run_id):
    return [json.loads(l) for l in (logs / f"trace-{run_id}.jsonl").read_text(encoding="utf-8").splitlines()]

def test_sample_run_estimates_everything_and_fabricates_nothing(tmp_path):
    p, pack, logs = _run("input_examples/example_3.json", tmp_path, {"ZETARIS_API_KEY": "", "METERLESS_RUNTIME_TOKEN": ""})
    assert p.returncode == 0, p.stderr
    assert pack["execution_mode"] == "sample" and pack["status"] == "complete"
    assert pack["limitations"][0].startswith("SAMPLE/OFFLINE")
    runs = pack["feature_runs"]
    assert len(runs) == 2 * 3 and all(not r["executed"] and r["samples"] == [] and r["rubric"] is None for r in runs)
    assert all(r["estimated"]["basis"] == "estimated" for r in runs)
    rows = [row for t in pack["stage_tables"] for row in t["rows"]]
    assert rows and all(row["token_basis"] == "estimated" for row in rows)
    assert all(t["switch_points"] == [] for t in pack["stage_tables"])
    assert {e["status"] for e in pack["model_stack"]} == {"requires_live_run"}
    assert pack["critiques"][0]["findings"] == [] and pack["revisions"] == [] and pack["spend_usd"] == "0"
    trace = _trace(logs, "example-3")
    assert {"Planner", "Analyst", "Critic", "Controller"} <= {e["agent_name"] for e in trace}
    assert all(e["model"] is None for e in trace), "offline decisions must never carry a model name"
    assert all("confidence" not in e for e in trace)

def test_sample_domain_risks_require_live_mode_and_none_are_invented(tmp_path):
    _, pack, _ = _run("input_examples/example_1.json", tmp_path)
    assert "Domain risk review requires live mode." in pack["limitations"]
    assert any(g["field"] == "domain_risks" and "requires live mode" in g["note"] for g in pack["evidence_gaps"])
    assert not [r for r in pack["risks"] if r["cause_class"] == "domain" or r["origin"] == "model_generated"]

def test_missing_build_inputs_ask_but_do_not_stop_the_stage_table(tmp_path):
    _, pack, _ = _run("input_examples/example_2.json", tmp_path)
    assert pack["status"] == "complete" and pack["stage_tables"]
    assert pack["build_panel"]["ranked_approach_ids"] == []
    assert any(q.startswith("Build panel:") and "DevOps" in q for q in pack["questions"])

def test_audio_features_are_not_executed_and_say_why(tmp_path):
    _, pack, _ = _run("input_examples/example_1.json", tmp_path)
    a1 = [r for r in pack["feature_runs"] if r["feature_id"] == "A1_transcribe_attempt"]
    assert a1 and all("audio modality" in r["not_executed_reason"] for r in a1)

def test_revenue_share_risk_reaches_the_pack(tmp_path):
    _, pack, _ = _run("input_examples/example_2.json", tmp_path)
    assert any(r["cause_class"] == "unit_economics" and r["severity"] == "high" for r in pack["risks"])

def test_unapproved_returns_needs_input_with_estimates_and_no_paid_work(tmp_path):
    payload = {**_example(3), "run_id": "unapproved", "evaluation_approved": False}
    p, pack, _ = _run(None, tmp_path, payload=payload)
    assert p.returncode == 0 and pack["status"] == "needs_input"
    assert pack["questions"] and pack["spend_usd"] == "0" and pack["stage_tables"]
    assert all(not r["executed"] for r in pack["feature_runs"])

def test_brief_without_ai_features_needs_input_but_keeps_build_panel(tmp_path):
    payload = _example(3); payload["run_id"] = "no-features"; payload["brief"]["ai_features"] = []
    _, pack, _ = _run(None, tmp_path, payload=payload)
    assert pack["status"] == "needs_input" and pack["build_ledgers"]
    assert any("AI features" in q for q in pack["questions"]) and pack["stage_tables"] == []

def test_no_sealed_read_before_freeze(tmp_path):
    _, _, logs = _run("input_examples/example_3.json", tmp_path)
    trace = _trace(logs, "example-3")
    frozen_seq = next(e["seq"] for e in trace if e["action"] == "state_transition" and "-> frozen" in e["output_summary"])
    early = [e for e in trace if e["seq"] < frozen_seq and e["action"] == "retrieve_evidence" and e["status"] == "success"
             and any(s in (e["input_summary"] or "") for s in ("holdout", "retrospective_actuals"))]
    assert not early

def test_idempotent_run_id_refused(tmp_path):
    _run("input_examples/example_2.json", tmp_path)
    p, pack, _ = _run("input_examples/example_2.json", tmp_path)
    assert p.returncode == 4 and pack["status"] == "error" and pack["code"] == "DUPLICATE_RUN"

def test_invalid_input_is_structured_error(tmp_path):
    bad = tmp_path / "bad.json"; bad.write_text('{"run_id": "x"}')
    env = {**os.environ, "SAMPLE_MODE": "true", "LOG_DIR": str(tmp_path)}
    out = tmp_path / "o.json"
    p = subprocess.run([sys.executable, "run.py", "--input", str(bad), "--output", str(out)], capture_output=True, text=True, env=env, cwd=ROOT)
    assert p.returncode == 2 and json.loads(out.read_text(encoding="utf-8"))["code"] == "INVALID_INPUT"
    assert "Traceback" not in p.stderr
