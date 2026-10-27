"""H-MEM carries founder inputs between runs of one project; the current brief always wins."""
from pathlib import Path

from app.adapters.sample import RulePolicyInference, SampleDataLayer, SampleMemory
from app.contracts import RunRequest
from app.controller import Checkpoints, Controller
from app.engines.hmem import bridge as hmem
from app.trace import Trace
from tests.test_v4_contracts import request_data

ROOT = Path(__file__).resolve().parents[1]


def run(tmp_path, monkeypatch, run_id, project_id="memory-project", **inputs):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("HMEM_STORAGE_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("NODE_OPTIONS", f'--require="{(ROOT / "scripts" / "hmem_network_guard.cjs").as_posix()}"')
    data = request_data()
    data.update(run_id=run_id, project_id=project_id)
    brief = data["brief"]
    if "budget" in inputs:
        brief["monthly_ai_budget_usd"] = inputs["budget"]
    if "price" in inputs:
        brief["usage"] = {"subscription_price_usd": inputs["price"], "paying_fraction": inputs["fraction"],
                          "field_status": {"subscription_price_usd": "assumed", "paying_fraction": "assumed"}}
    request = RunRequest.model_validate(data)
    checkpoints = Checkpoints(str(tmp_path / f"{run_id}.db"))
    try:
        controller = Controller(SampleDataLayer(), RulePolicyInference(), SampleMemory(bridge_available=True),
                                Trace(request.run_id, "sample", echo=False), "sample", checkpoints)
        return controller.run(request)
    finally:
        checkpoints.conn.close()


def recalled_notes(pack):
    return [note for note in pack.limitations if note.startswith("Recalled from H-MEM")]


def test_second_run_fills_empty_inputs_from_first_run(tmp_path, monkeypatch):
    assert hmem.offline_bridge_available()
    first = run(tmp_path, monkeypatch, "run-1", budget="40", price="15", fraction="0.08")
    assert first.status.value == "complete" and not recalled_notes(first)
    assert all(row.revenue_usd is not None for row in first.stage_totals)
    assert len(first.memory_ids) == 2   # accepted stack and founder inputs, the two kinds a later run recalls

    second = run(tmp_path, monkeypatch, "run-2")
    assert set(first.memory_ids) <= set(second.memory_ids)
    assert second.monthly_ai_budget_usd == first.monthly_ai_budget_usd
    assert [row.revenue_usd for row in second.stage_totals] == [row.revenue_usd for row in first.stage_totals]
    [note] = recalled_notes(second)
    assert "from run run-1" in note and "paying_fraction = 0.08 (assumed" in note   # status kept, never upgraded


def test_current_input_wins_and_projects_are_isolated(tmp_path, monkeypatch):
    run(tmp_path, monkeypatch, "run-1", budget="40", price="15", fraction="0.08")
    second = run(tmp_path, monkeypatch, "run-2", budget="500")
    assert str(second.monthly_ai_budget_usd) == "500"
    [note] = recalled_notes(second)
    assert "monthly_ai_budget_usd" not in note and "subscription_price_usd = 15" in note

    other = run(tmp_path, monkeypatch, "run-3", project_id="other-project")
    assert other.monthly_ai_budget_usd is None and not recalled_notes(other)
    assert all(row.revenue_usd is None for row in other.stage_totals)
