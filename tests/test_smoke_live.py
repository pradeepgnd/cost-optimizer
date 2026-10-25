import importlib.util, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_live.py"
_spec = importlib.util.spec_from_file_location("smoke_live", SCRIPT)
smoke = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(smoke)

PLACEHOLDERS = {k: "your-placeholder" for k in ("ZETARIS_REST_URL", "ZETARIS_ORG_ID", "ZETARIS_API_KEY",
                                                 "METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN")}

def test_secret_values_are_redacted(monkeypatch):
    monkeypatch.setenv("SOME_API_KEY", "s3cr3t-value-123")
    monkeypatch.setenv("NIGHTSHIFT_TOKEN", "tok-abcdef")
    out = smoke.clean("401 for key s3cr3t-value-123 and token tok-abcdef\nsecond line")
    assert "s3cr3t-value-123" not in out and "tok-abcdef" not in out and "\n" not in out

def test_unconfigured_run_skips_everything_without_network_and_saves_report():
    env = {**os.environ, **PLACEHOLDERS}
    p = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)
    live = [l for l in p.stdout.splitlines() if l.startswith(("| Zetaris |", "| Nightshift |"))]
    assert len(live) == 6 and all("| SKIP |" in l for l in live)          # H-MEM depends on the machine
    saved = ROOT / p.stdout.strip().splitlines()[-1].removeprefix("Saved ").strip()
    try:
        assert saved.name.startswith("smoke-") and "| Component | Check | Result | Detail |" in saved.read_text(encoding="utf-8")
    finally:
        saved.unlink()

class _FakeNightshift:
    """Stands in for NightshiftInference: offers the sample frontier and Nemotron routes, not the mid-tier one."""
    def __init__(self, trace=None):
        pass

    def list_models(self):
        return ["sample/frontier-placeholder", "sample/open-source-placeholder", "other/route"]

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60, max_tokens=None):
        usage = {} if model == "sample/open-source-placeholder" else \
            {"prompt_tokens": 12, "completion_tokens": 2, "completion_tokens_details": {"reasoning_tokens": 0}}
        return {"text": "OK", "requested_model": model, "resolved_model": model + "@resolved", "usage": usage}

def test_nightshift_checks_report_usage_route_gaps_and_missing_usage(monkeypatch):
    import app.adapters.live_nightshift as ns
    monkeypatch.setattr(ns, "NightshiftInference", _FakeNightshift)
    monkeypatch.delenv("METERLESS_OPEN_MODEL", raising=False)
    smoke.rows.clear()
    smoke.check_nightshift(None)                                        # falls back to the bundled snapshot
    by = {r[1]: r for r in smoke.rows}
    assert by["GET /v1/models"][2] == "PASS" and "3 routes" in by["GET /v1/models"][3]
    fr = by["completion: frontier"]
    assert fr[2] == "PASS" and "resolved sample/frontier-placeholder@resolved" in fr[3] and "prompt=12 completion=2" in fr[3]
    assert "bundled sample price snapshot" in by["completion: mid-tier"][3] and by["completion: mid-tier"][2] == "SKIP"
    assert by["completion: Nemotron"][2] == "FAIL" and "no prompt_tokens/completion_tokens" in by["completion: Nemotron"][3]
