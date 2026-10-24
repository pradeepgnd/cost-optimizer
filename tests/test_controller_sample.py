import json, os, subprocess, sys
from pathlib import Path

def _run(example, tmp_path, env_extra=None):
    env = {**os.environ, "SAMPLE_MODE": "true", "LOG_DIR": str(tmp_path / "logs"), "RUNS_DB": str(tmp_path / "runs.db")}
    env.update(env_extra or {})
    out = tmp_path / "out.json"
    p = subprocess.run([sys.executable, "run.py", "--input", example, "--output", str(out)], capture_output=True, text=True, env=env, cwd=Path(__file__).resolve().parents[1])
    return p, json.loads(out.read_text(encoding="utf-8")), tmp_path / "logs"

def test_sample_mode_runs_without_credentials_and_branches(tmp_path):
    p, pack, logs = _run("input_examples/example_1.json", tmp_path, {"ZETARIS_API_KEY": "", "METERLESS_RUNTIME_TOKEN": ""})
    assert p.returncode == 0, p.stderr
    assert pack["execution_mode"] == "sample" and pack["status"] == "complete"
    assert pack["revisions"], "stress fixture should trigger exactly one repair"
    assert len(pack["revisions"]) == 1
    assert pack["limitations"][0].startswith("SAMPLE/OFFLINE")
    trace = [json.loads(l) for l in (logs / "trace-example-1.jsonl").read_text(encoding="utf-8").splitlines()]
    agents = {e["agent_name"] for e in trace}
    assert {"Planner", "Analyst", "Critic", "Controller"} <= agents
    assert all(e["model"] is None for e in trace), "offline decisions must never carry a model name"
    assert all("confidence" not in e for e in trace)

def test_no_sealed_read_before_freeze(tmp_path):
    p, pack, logs = _run("input_examples/example_1.json", tmp_path)
    trace = [json.loads(l) for l in (logs / "trace-example-1.jsonl").read_text(encoding="utf-8").splitlines()]
    frozen_seq = next(e["seq"] for e in trace if e["action"] == "state_transition" and "-> frozen" in e["output_summary"])
    early_holdout = [e for e in trace if e["seq"] < frozen_seq and "holdout" in (e["input_summary"] or "") and e["status"] == "success" and e["action"] == "retrieve_evidence"]
    assert not early_holdout

def test_unapproved_returns_needs_input_not_paid_work(tmp_path):
    p, pack, _ = _run("input_examples/example_3.json", tmp_path)
    assert p.returncode == 0 and pack["status"] == "needs_input"
    assert pack["questions"] and pack["development_results"] == [] and pack["spend_usd"] == "0"

def test_idempotent_run_id_refused(tmp_path):
    _run("input_examples/example_2.json", tmp_path)
    p, pack, _ = _run("input_examples/example_2.json", tmp_path)
    assert p.returncode == 4 and pack["status"] == "error" and pack["code"] == "DUPLICATE_RUN"

def test_invalid_input_is_structured_error(tmp_path):
    bad = tmp_path / "bad.json"; bad.write_text('{"run_id": "x"}')
    env = {**os.environ, "SAMPLE_MODE": "true", "LOG_DIR": str(tmp_path)}
    out = tmp_path / "o.json"
    p = subprocess.run([sys.executable, "run.py", "--input", str(bad), "--output", str(out)], capture_output=True, text=True, env=env, cwd=Path(__file__).resolve().parents[1])
    assert p.returncode == 2 and json.loads(out.read_text(encoding="utf-8"))["code"] == "INVALID_INPUT"
    assert "Traceback" not in p.stderr
