"""Integration checks against the actual pinned Node H-MEM reference."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from app.adapters.base import SetupIncomplete
from app.engines.hmem.bridge import HERE, HmemBridge, offline_bridge_available

@pytest.fixture(scope="module", autouse=True)
def require_real_engine():
    assert offline_bridge_available(), "Run npm ci --ignore-scripts in app/engines/hmem before pytest"

def test_remember_restart_recall_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HMEM_STORAGE_DIR", str(tmp_path))
    b1 = HmemBridge()
    saved = b1.remember_confirmed("proj-A", {"kind": "confirmed_constraint", "text": "monthly budget 300 USD"})
    assert saved["memory_ids"]
    b2 = HmemBridge()  # new process per call = restart
    got = b2.recall("proj-A", {"kind": "confirmed_constraint"})
    assert set(saved["memory_ids"]) <= set(got["memory_ids"])
    other = b2.recall("proj-B", {"kind": "confirmed_constraint"})
    assert not set(saved["memory_ids"]) & set(other.get("memory_ids", []))
    audit = b2.audit("proj-A")
    assert audit["audit_refs"]
    assert {entry["action"] for entry in audit["entries"]} >= {"create", "read"}
    assert got["engine_revision"] == (HERE / "PINNED_REVISION").read_text().strip()
    assert got["records"][0]["source"] and got["records"][0]["provenance"]
    other_saved = b2.remember_confirmed("proj-B", {"kind": "confirmed_constraint", "text": "a different project budget"})
    assert set(saved["memory_ids"]).isdisjoint(other_saved["memory_ids"])


def test_replacement_is_audited_and_old_constraint_does_not_return(tmp_path):
    bridge = HmemBridge(storage_dir=tmp_path)
    original = {"kind": "confirmed_constraint", "field": "devops_capacity", "value": "full"}
    replacement = {**original, "value": "none"}
    old = bridge.remember_confirmed("proj-A", original)
    new = bridge.remember_confirmed("proj-A", replacement)
    duplicate = HmemBridge(storage_dir=tmp_path).remember_confirmed("proj-A", replacement)
    assert duplicate["memory_ids"] == new["memory_ids"]
    recalled = bridge.recall("proj-A", {"kind": "confirmed_constraint"})
    assert recalled["memory_ids"] == new["memory_ids"]
    state = json.loads((tmp_path / "proj-A" / "state.json").read_text())
    old_record = next(r for r in state["records"] if "proj-A:" + r["id"] == old["memory_ids"][0])
    assert "proj-A:" + old_record["supersededBy"] == new["memory_ids"][0]
    audit = bridge.audit("proj-A")
    assert sum(e["action"] == "create" for e in audit["entries"]) == 2
    assert any(e["action"] == "update" and e["memory_id"] == old["memory_ids"][0] for e in audit["entries"])


def test_invalid_scope_and_unaccepted_findings_are_rejected(tmp_path):
    bridge = HmemBridge(storage_dir=tmp_path / "memory")
    with pytest.raises(SetupIncomplete):
        bridge.recall("../outside", {"kind": "confirmed_constraint"})
    assert not (tmp_path / "outside").exists()
    with pytest.raises(SetupIncomplete):
        bridge.remember_confirmed("proj-A", {"kind": "accepted_finding", "text": "generated recommendation"})


def test_independent_python_processes_do_not_overwrite_each_others_memory(tmp_path):
    code = """import sys
from app.engines.hmem.bridge import HmemBridge
HmemBridge().remember_confirmed('parallel', {'kind':'confirmed_constraint','text':'Confirmed note '+sys.argv[1]})
"""
    def save(index):
        process = subprocess.run([sys.executable, "-c", code, str(index)], capture_output=True, text=True,
                                 env={**os.environ, "HMEM_STORAGE_DIR": str(tmp_path)},
                                 cwd=Path(__file__).resolve().parents[1], timeout=20)
        assert process.returncode == 0, process.stderr
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(save, range(4)))
    recalled = HmemBridge(storage_dir=tmp_path).recall("parallel", {"kind": "confirmed_constraint"})
    assert len(set(recalled["memory_ids"])) == 4


def test_sample_memory_uses_real_engine_and_separate_storage(tmp_path, monkeypatch):
    from app.adapters.sample import SampleMemory
    monkeypatch.setenv("HMEM_SAMPLE_STORAGE_DIR", str(tmp_path / "sample"))
    monkeypatch.setenv("HMEM_STORAGE_DIR", str(tmp_path / "live"))
    memory = SampleMemory(bridge_available=True)
    saved = memory.remember_confirmed("proj-A", {"kind": "confirmed_constraint", "text": "confirmed sample fact"})
    assert saved["memory_ids"] == memory.recall("proj-A", {"kind": "confirmed_constraint"})["memory_ids"]
    assert not HmemBridge().recall("proj-A", {"kind": "confirmed_constraint"})["memory_ids"]


def test_trace_keeps_the_public_engine_revision_and_audit_refs(tmp_path):
    from app.trace import Trace
    trace = Trace("memory-trace", "sample", str(tmp_path / "logs"), echo=False)
    bridge = HmemBridge(trace, storage_dir=tmp_path / "memory")
    bridge.remember_confirmed("proj-A", {"kind": "confirmed_constraint", "text": "explicit confirmed input"})
    event = json.loads(trace.path.read_text().splitlines()[0])
    assert event["extra"]["engine_revision"] == bridge.revision
    assert event["extra"]["audit_refs"]
    assert event["memory_ids"] and "confidence" not in event
