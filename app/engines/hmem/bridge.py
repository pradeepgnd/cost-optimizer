"""Thin Python wrapper over the pinned Meterless H-MEM reference (Node/TypeScript).

Contract (architecture §4):  memory_bridge({operation, project_scope, payload})
                           -> {status, engine_revision, memory_ids, context, audit_refs}
Structured stdin/stdout, argument array, fixed script path, timeout, single-writer lock.

STATUS: interface only. Pradeep pins the reference revision in app/engines/hmem/PINNED_REVISION,
installs it under app/engines/hmem/reference/ and makes `node bridge.mjs` answer the contract.
Until then every call raises SetupIncomplete. A dictionary is not an engine.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path

from app.adapters.base import Memory, SetupIncomplete

HERE = Path(__file__).resolve().parent
BRIDGE = HERE / "bridge.mjs"
PIN = HERE / "PINNED_REVISION"
_LOCK = threading.Lock()


def offline_bridge_available() -> bool:
    """True only when the pinned reference is present and its offline self-test passes."""
    if not (BRIDGE.exists() and PIN.exists() and (HERE / "reference").exists()):
        return False
    try:
        out = subprocess.run(["node", str(BRIDGE), "--selftest"], capture_output=True, text=True, timeout=20)
        return out.returncode == 0 and '"status": "ok"' in out.stdout.replace("'", '"')
    except (OSError, subprocess.TimeoutExpired):
        return False


class HmemBridge(Memory):
    def __init__(self, trace=None, timeout_s: int = 20):
        if not BRIDGE.exists() or not PIN.exists():
            raise SetupIncomplete("H-MEM bridge not installed: missing app/engines/hmem/bridge.mjs or PINNED_REVISION")
        self.trace = trace
        self.timeout = timeout_s
        self.storage = os.getenv("HMEM_STORAGE_DIR", str(HERE / "storage"))
        self.revision = PIN.read_text().strip()

    def _call(self, operation: str, project_scope: str, payload: dict) -> dict:
        req = json.dumps({"operation": operation, "project_scope": project_scope, "payload": payload, "storage": self.storage})
        with _LOCK:
            out = subprocess.run(["node", str(BRIDGE)], input=req, capture_output=True, text=True, timeout=self.timeout)
        if out.returncode != 0:
            raise SetupIncomplete(f"H-MEM bridge failed ({operation}): {out.stderr[:300]}")
        res = json.loads(out.stdout[-200000:])
        res.setdefault("engine_revision", self.revision)
        if self.trace:
            self.trace.event("Analyst", f"hmem_{operation}", memory_ids=res.get("memory_ids", []),
                             output_summary=f"{operation} ok", extra={"engine_revision": res["engine_revision"], "audit_refs": res.get("audit_refs")})
        return res

    def remember_confirmed(self, project_scope, payload):
        return self._call("remember_confirmed", project_scope, payload)

    def recall(self, project_scope, query):
        return self._call("recall", project_scope, query)

    def audit(self, project_scope):
        return self._call("audit", project_scope, {})
