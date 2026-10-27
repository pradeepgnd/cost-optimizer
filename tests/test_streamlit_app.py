import json

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from pathlib import Path

from app import ui_service as svc

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def ui_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "UI_DIR", tmp_path / "ui")
    monkeypatch.setenv("COST_ADVISOR_NO_DOTENV", "1")   # never load the developer's private .env into the test process


def app():
    return AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120).run()


def _markdown_text(at) -> str:
    return "\n".join(str(getattr(block, "value", block)) for block in at.markdown)


def test_sample_form_runs_once_and_shows_the_offline_label():
    at = app()
    assert not at.exception
    assert "SAMPLE/OFFLINE" in _markdown_text(at)
    assert 'Cost<span>.</span>Advisor' in _markdown_text(at)
    run = next(b for b in at.button if b.label == "Run")
    run.click().run()
    assert not at.exception
    text = _markdown_text(at)
    assert "SAMPLE/OFFLINE" in text
    assert "Status" in text and "complete" in text
    assert "Evaluation spend (USD)" in text
    run_id = at.session_state["run_id"]
    pack = svc.load_result(run_id)
    assert pack["execution_mode"] == "sample" and pack["status"] == "complete"
    assert str(pack["spend_usd"]) in ("0", "0.0", "0.00")
    assert str(pack["spend_usd"]) in text
    # A rerender loads the stored result and starts nothing new.
    before = sorted(p.name for p in svc.UI_DIR.iterdir())
    at.run()
    assert not at.exception and sorted(p.name for p in svc.UI_DIR.iterdir()) == before


def test_switching_the_idea_starts_a_new_run_and_hides_the_previous_result(monkeypatch):
    ids = iter(f"ui-switch-{n}" for n in range(1, 10))
    monkeypatch.setattr(svc, "new_run_id", lambda prefix="ui": next(ids))
    at = app()
    next(b for b in at.button if b.label == "Run").click().run()
    first = at.session_state["run_id"]
    assert svc.load_result(first)["status"] == "complete"
    other = next(name for name in svc.list_examples() if name != at.selectbox(key="example").value)
    at.selectbox(key="example").set_value(other).run()
    assert not at.exception
    assert at.session_state["run_id"] != first and at.session_state["outcome"] is None
    assert any("Fill in the brief" in i.value for i in at.info)


def test_invalid_input_disables_run_and_shows_the_problem():
    at = app()
    next(t for t in at.text_input if t.label.startswith("Maximum evaluation spend")).set_value("-5").run()
    assert any("Fix the inputs" in e.value for e in at.error)
    assert next(b for b in at.button if b.label == "Run").disabled


def test_live_shaped_pack_shows_market_costs_checks_and_critic_flags():
    pack = json.loads((ROOT / "output_examples" / "example_3_output.json").read_text())
    pack.update({"run_id": "ui-live-shape", "execution_mode": "live", "trace_path": None})
    pack["openrouter_projection_tables"] = [{**table, "rows": [{**row, "model_id": "openrouter/" + row["model_id"]} for row in table["rows"]]}
                                            for table in pack["stage_tables"]]
    first = pack["feature_runs"][0]
    first["rubric"] = {"checks": {"json_ok": True}, "pending": ["human_ok"]}
    pack["critiques"] = [{"findings": [{"kind": "token_gap", "severity": "low", "feature_id": first["feature_id"],
                                        "model_id": first["model_id"], "claim": "Estimated 10 vs measured 12"}]}]
    svc.UI_DIR.mkdir(parents=True)
    (svc.UI_DIR / "ui-live-shape.result.json").write_text(json.dumps(pack))
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120)
    at.session_state["run_id"] = "ui-live-shape"
    at.session_state["mode"] = "Live (Nightshift + Zetaris)"
    at.run()
    assert not at.exception
    assert 'class="ca-sample"' not in _markdown_text(at)  # live packs may mention SAMPLE in limitations text
    assert 'class="ca-live"' in _markdown_text(at)
    assert any("market reference price" in c.value for c in at.caption)
    assert "Recommendations locked until human review" in _markdown_text(at)
    frames = [df.value for df in at.dataframe]
    assert any("pending human review" in frame.to_string() for frame in frames)
    assert any("token_gap" in frame.to_string() for frame in frames)


def test_live_mode_shows_which_price_data_it_will_use_or_blocks_run(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "DEFAULT_BINDINGS", tmp_path / "missing.json")
    monkeypatch.delenv("ZETARIS_BINDINGS_FILE", raising=False)
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120).run()
    at.radio(key="mode").set_value("Live (Nightshift + Zetaris)").run()
    assert "LIVE" in _markdown_text(at) and "Nightshift runs the models" in _markdown_text(at)
    assert 'class="ca-sample"' not in _markdown_text(at)
    assert any("Price data not found" in e.value for e in at.error)
    assert next(b for b in at.button if b.label == "Run").disabled
    bindings = tmp_path / "b.json"
    bindings.write_text(json.dumps({"snapshot_id": "87f8564d36ffd17330015ad3", "expected_counts": {"models": 37, "catalog": 460}}))
    monkeypatch.setenv("ZETARIS_BINDINGS_FILE", str(bindings))
    at.run()
    assert any("snapshot `87f8564d`, 37 models, 460 catalog rows (from ZETARIS_BINDINGS_FILE)" in s.value for s in at.success)


def test_sample_run_shows_monthly_totals_with_revenue():
    at = app()
    next(t for t in at.text_input if t.label.startswith("Price per paying user")).set_value("15").run()
    next(t for t in at.text_input if t.label.startswith("Paying fraction")).set_value("0.08").run()
    next(b for b in at.button if b.label == "Run").click().run()
    assert not at.exception
    totals = next(
        df.value
        for df in at.dataframe
        if list(df.value.columns)[:3] == ["stage", "users", "monthly AI cost USD"]
    )
    assert totals["revenue USD"].notna().all()
    assert any("sample placeholder prices" in c.value and "AI-only" in c.value for c in at.caption)
    text = " ".join(item.value for item in at.markdown)
    assert "Recommendation" in text
    assert "sample/frontier-placeholder" in text and "sample/open-source-placeholder" in text
