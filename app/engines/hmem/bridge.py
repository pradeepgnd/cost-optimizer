"""Thin Python wrapper over the pinned Meterless H-MEM reference (Node/TypeScript).

Contract (architecture §4):  memory_bridge({operation, project_scope, payload})
                           -> {status, engine_revision, memory_ids, context, audit_refs}
Structured stdin/stdout, argument array, fixed script path, timeout, single-writer lock.

The pinned reference and bridge must pass the offline self-test before use.
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


def bridge_selftest() -> dict:
    """Parse the real bridge protocol; formatting or a substring cannot turn failure into success."""
    missing = [path.name for path in (BRIDGE, PIN, HERE / "reference" / "src" / "index.ts",
                                       HERE / "reference" / "node_modules" / "tsx") if not path.exists()]
    if missing:
        raise SetupIncomplete(f"H-MEM bridge not installed: missing {', '.join(missing)}")
    revision = PIN.read_text().strip()
    if not revision:
        raise ValueError("H-MEM pinned revision is empty")
    out = subprocess.run(["node", str(BRIDGE), "--selftest"], capture_output=True, text=True, timeout=20)
    if out.returncode != 0:
        raise ValueError(f"H-MEM self-test exit {out.returncode}: {out.stderr[:200]}")
    try:
        result = json.loads(out.stdout)
    except (ValueError, TypeError) as error:
        raise ValueError("H-MEM self-test returned invalid JSON") from error
    if not isinstance(result, dict) or result.get("status") != "ok" or result.get("engine_revision") != revision:
        raise ValueError("H-MEM self-test JSON status or revision is invalid")
    return result


def offline_bridge_available() -> bool:
    """Self-test availability only; persistence/isolation/offline delegation require M07 evidence."""
    try:
        bridge_selftest()
        return True
    except (OSError, ValueError, SetupIncomplete, subprocess.TimeoutExpired):
        return False


class HmemBridge(Memory):
    def __init__(self, trace=None, timeout_s: int = 20):
        try:
            bridge_selftest()
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            raise SetupIncomplete(f"H-MEM self-test failed: {type(error).__name__}") from error
        self.trace = trace
        self.timeout = timeout_s
        self.storage = str(Path(os.getenv("HMEM_STORAGE_DIR", str(HERE / "storage"))).resolve())
        self.revision = PIN.read_text().strip()

    def _call(self, operation: str, project_scope: str, payload: dict) -> dict:
        req = json.dumps({"operation": operation, "project_scope": project_scope, "payload": payload, "storage": self.storage})
        try:
            with _LOCK:
                out = subprocess.run(["node", str(BRIDGE)], input=req, capture_output=True, text=True, timeout=self.timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SetupIncomplete(f"H-MEM bridge failed ({operation}): {type(error).__name__}") from error
        if out.returncode != 0:
            raise SetupIncomplete(f"H-MEM bridge failed ({operation}): {out.stderr[:300]}")
        try:
            res = json.loads(out.stdout)
        except (ValueError, TypeError) as error:
            raise SetupIncomplete(f"H-MEM bridge returned invalid JSON ({operation})") from error
        if (not isinstance(res, dict) or res.get("status") != "ok" or res.get("engine_revision") != self.revision
                or not isinstance(res.get("memory_ids"), list) or not isinstance(res.get("context"), list)
                or not isinstance(res.get("audit_refs"), list)):
            raise SetupIncomplete(f"H-MEM bridge returned invalid response ({operation})")
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
