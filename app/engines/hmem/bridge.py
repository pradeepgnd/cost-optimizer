"""Thin Python wrapper over the pinned Meterless H-MEM reference (Node/TypeScript).

Contract (architecture §4):  memory_bridge({operation, project_scope, payload})
                           -> {status, engine_revision, memory_ids, context, audit_refs}
Structured stdin/stdout, argument array, fixed script path, timeout, single-writer lock.

The unchanged sponsor reference is vendored with source hashes and a revision pin.
Every call starts a fresh Node process; persistence and auditing belong to H-MEM.
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
    if not (BRIDGE.exists() and PIN.exists() and (HERE / "node_modules" / "tsx").exists()):
        return False
    try:
        out = subprocess.run(["node", str(BRIDGE), "--selftest"], capture_output=True, text=True, timeout=20)
        result = json.loads(out.stdout)
        return out.returncode == 0 and result.get("status") == "ok" and result.get("engine_revision") == PIN.read_text().strip()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


class HmemBridge(Memory):
    def __init__(self, trace=None, timeout_s: int = 20, storage_dir=None):
        if not all(p.exists() for p in (BRIDGE, PIN, HERE / "reference" / "src" / "index.ts", HERE / "node_modules" / "tsx")):
            raise SetupIncomplete("H-MEM dependencies missing: run npm ci --ignore-scripts in app/engines/hmem")
        self.trace = trace
        self.timeout = timeout_s
        self.storage = str(Path(storage_dir or os.getenv("HMEM_STORAGE_DIR", str(HERE / "storage" / "live"))).resolve())
        self.revision = PIN.read_text().strip()

    def _call(self, operation: str, project_scope: str, payload: dict) -> dict:
        req = json.dumps({"operation": operation, "project_scope": project_scope, "payload": payload, "storage": self.storage})
        try:
            with _LOCK:
                out = subprocess.run(["node", str(BRIDGE)], input=req, capture_output=True, text=True, timeout=self.timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SetupIncomplete(f"H-MEM {operation} could not finish ({type(error).__name__})") from None
        if out.returncode != 0:
            raise SetupIncomplete(f"H-MEM bridge failed ({operation}, exit {out.returncode}); check scope, source integrity, and Node dependencies")
        try:
            res = json.loads(out.stdout)
            if (res.get("status") != "ok" or res.get("engine_revision") != self.revision
                    or res.get("project_scope") != project_scope
                    or not all(isinstance(res.get(key), list) for key in ("memory_ids", "audit_refs", "records"))
                    or not isinstance(res.get("context"), str)
                    or not all(isinstance(mid, str) and mid.startswith(project_scope + ":") for mid in res["memory_ids"])):
                raise ValueError
        except (ValueError, AttributeError, TypeError):
            raise SetupIncomplete(f"H-MEM {operation} returned an invalid or incorrectly scoped response") from None
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
