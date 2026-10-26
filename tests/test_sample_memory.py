"""Sample memory must delegate to the real engine and report broken setup."""
import pytest
from pathlib import Path

from app.adapters.base import SetupIncomplete
from app.adapters.sample import SampleMemory
from app.engines.hmem import bridge as hmem

ROOT = Path(__file__).resolve().parents[1]


def test_sample_memory_delegates_offline_and_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("HMEM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("NODE_OPTIONS", f"--require={ROOT / 'scripts' / 'hmem_network_guard.cjs'}")
    assert hmem.offline_bridge_available()
    memory = SampleMemory(bridge_available=True)
    saved = memory.remember_confirmed("sample-project", {"kind": "confirmed_constraint", "text": "use a 300 USD budget"})
    recalled = SampleMemory(bridge_available=True).recall("sample-project", {"kind": "confirmed_constraint"})
    assert saved["memory_ids"] == recalled["memory_ids"]
    assert recalled["context"][0]["text"] == "use a 300 USD budget"
    assert memory.audit("sample-project")["audit_refs"]


def test_sample_memory_reports_missing_or_broken_bridge(tmp_path, monkeypatch):
    with pytest.raises(SetupIncomplete, match="H-MEM bridge"):
        SampleMemory(bridge_available=False).recall("sample-project", {})
    broken = tmp_path / "broken.mjs"
    broken.write_text("process.stdout.write('not JSON')")
    monkeypatch.setattr(hmem, "BRIDGE", broken)
    assert not hmem.offline_bridge_available()
    with pytest.raises(SetupIncomplete, match="self-test"):
        SampleMemory(bridge_available=True).recall("sample-project", {})
