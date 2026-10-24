"""The Meterless Engine test the README points judges to. Skips until the bridge is pinned (W03)."""
import pytest
from app.engines.hmem.bridge import offline_bridge_available

pytestmark = pytest.mark.skipif(not offline_bridge_available(), reason="H-MEM bridge not pinned/installed yet (W03)")

def test_remember_restart_recall_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HMEM_STORAGE_DIR", str(tmp_path))
    from app.engines.hmem.bridge import HmemBridge
    b1 = HmemBridge()
    saved = b1.remember_confirmed("proj-A", {"kind": "confirmed_constraint", "text": "monthly budget 300 USD"})
    assert saved["memory_ids"]
    b2 = HmemBridge()  # new process per call = restart
    got = b2.recall("proj-A", {"kind": "confirmed_constraint"})
    assert set(saved["memory_ids"]) <= set(got["memory_ids"])
    other = b2.recall("proj-B", {"kind": "confirmed_constraint"})
    assert not set(saved["memory_ids"]) & set(other.get("memory_ids", []))
    assert b2.audit("proj-A")["audit_refs"]
