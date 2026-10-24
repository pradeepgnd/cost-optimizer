"""JSONL trace in the organizer's recommended format, plus readable stdout.

One file per run: logs/trace-<run_id>.jsonl. Secrets are masked. `confidence`
is deliberately absent — we do not invent scores.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_SECRET_KEYS = re.compile(r"(token|api[_-]?key|secret|password|authorization)", re.I)
_SECRET_SHAPE = re.compile(r"\b(sk-[A-Za-z0-9_\-]{12,}|[A-Za-z0-9_\-]{40,})\b")


def _mask(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: ("...redacted" if _SECRET_KEYS.search(k) else _mask(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [_mask(x) for x in v]
    if isinstance(v, str):
        return _SECRET_SHAPE.sub("...redacted", v)
    return v


class Trace:
    def __init__(self, run_id: str, execution_mode: str, log_dir: str = "logs", echo: bool = True):
        self.run_id = run_id
        self.execution_mode = execution_mode
        self.dir = Path(os.getenv("LOG_DIR", log_dir))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"trace-{run_id}.jsonl"
        self.echo = echo
        self.seq = 0

    def event(self, agent_name: str, action: str, *, status: str = "success",
              input_summary: str = "", output_summary: str = "", target_agent: Optional[str] = None,
              model: Optional[str] = None, requested_model: Optional[str] = None,
              route_id: Optional[str] = None, retry_count: int = 0,
              evidence_ids: Optional[list[str]] = None, query_id: Optional[str] = None,
              memory_ids: Optional[list[str]] = None, execution_kind: Optional[str] = None,
              extra: Optional[dict] = None) -> dict:
        self.seq += 1
        ev = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "run_id": self.run_id,
            "seq": self.seq,
            "execution_mode": self.execution_mode,
            "agent_name": agent_name,
            "action": action,
            "input_summary": input_summary[:500],
            "output_summary": output_summary[:500],
            "target_agent": target_agent,
            "model": model,
            "requested_model": requested_model,
            "route_id": route_id,
            "retry_count": retry_count,
            "status": status,
            "evidence_ids": evidence_ids or [],
            "query_id": query_id,
            "memory_ids": memory_ids or [],
            "execution_kind": execution_kind,
        }
        if extra:
            ev["extra"] = _mask(extra)
        ev = _mask(ev)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        if self.echo:
            tgt = f" -> {target_agent}" if target_agent else ""
            mdl = f" (model: {model})" if model else ""
            print(f"[INFO] run_id={self.run_id} {agent_name} {action}{tgt} {status}{mdl}: {output_summary[:120]}",
                  file=sys.stderr, flush=True)
        return ev

    def final(self, payload: dict) -> None:
        """Documented final-result event so stdout-only callers can parse a single line."""
        line = json.dumps({"event": "final_result", "run_id": self.run_id, **_mask(payload)}, default=str)
        print(line, flush=True)
