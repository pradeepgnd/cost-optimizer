"""Required real Meterless H-MEM reference persistence and isolation check."""
import json
import os
import subprocess
import sys
from pathlib import Path

from app.engines.hmem.bridge import HmemBridge, bridge_selftest

ROOT = Path(__file__).resolve().parents[1]

def test_remember_restart_recall_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HMEM_STORAGE_DIR", str(tmp_path))
    assert bridge_selftest()["status"] == "ok"
    b1 = HmemBridge()
    saved = b1.remember_confirmed("proj-A", {"kind": "confirmed_constraint", "text": "monthly budget 300 USD"})
    assert saved["memory_ids"]
    code = "import json; from app.engines.hmem.bridge import HmemBridge; print(json.dumps(HmemBridge().recall('proj-A', {'kind': 'confirmed_constraint'})))"
    process = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True,
                             env={**os.environ, "HMEM_STORAGE_DIR": str(tmp_path)}, check=True)
    got = json.loads(process.stdout)
    assert set(saved["memory_ids"]) <= set(got["memory_ids"])
    assert any(item["text"] == "monthly budget 300 USD" for item in got["context"])
    b2 = HmemBridge()
    other = b2.recall("proj-B", {"kind": "confirmed_constraint"})
    assert not set(saved["memory_ids"]) & set(other.get("memory_ids", []))
    assert other["context"] == [] and other["audit_refs"] == []
    audit = b2.audit("proj-A")
    assert audit["audit_refs"] and {item["action"] for item in audit["context"]} >= {"create", "read"}
    assert set(got["audit_refs"]) <= set(audit["audit_refs"])


def test_project_scope_cannot_escape_storage(tmp_path, monkeypatch):
    from app.adapters.base import SetupIncomplete
    import pytest
    monkeypatch.setenv("HMEM_STORAGE_DIR", str(tmp_path))
    bridge = HmemBridge()
    with pytest.raises(SetupIncomplete, match="project_scope"):
        bridge.remember_confirmed("../outside", {"kind": "confirmed_constraint", "text": "blocked"})
    assert list(tmp_path.iterdir()) == []


def test_bridge_selftest_with_node_network_blocked(monkeypatch):
    monkeypatch.setenv("NODE_OPTIONS", f'--require="{(ROOT / "scripts" / "hmem_network_guard.cjs").as_posix()}"')
    assert bridge_selftest()["status"] == "ok"
