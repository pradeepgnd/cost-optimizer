"""SAMPLE_MODE adapters: bundled data, rule-based policies, zero network.

These never replay saved model answers or read output_examples. They run the same
controller with explicit rules in place of model calls. Every decision is labeled
execution_kind=rule_policy with model=None.
"""
from __future__ import annotations

import json
import os
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Optional

from app.adapters.base import DataLayer, Inference, InferenceResult, Memory, SetupIncomplete
from app.contracts import (ApproachProfile, DevTaskCase, EvidenceStatus, FounderBrief, ModelProfile, SourceRef)

DATA = Path(__file__).resolve().parents[2] / "data" / "sample"


def _load(name: str):
    with (DATA / name).open(encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


class SampleDataLayer(DataLayer):
    def __init__(self):
        self.manifest = _load("manifest.json")

    def _ref(self, source_set: str, record_id: str, status=EvidenceStatus.verified) -> SourceRef:
        m = self.manifest["sources"][source_set]
        return SourceRef(source_set=source_set, record_id=record_id, version=m["version"],
                         origin_url=m.get("origin"), verified_at=m.get("verified_at"), status=status)

    def read_brief(self, brief_id: str):
        for b in _load("founder_briefs.json"):
            if b["brief_id"] == brief_id:
                brief = FounderBrief.model_validate(b)
                return brief, self._ref("founder_briefs", brief_id, EvidenceStatus.reconstructed)
        raise KeyError(f"brief {brief_id} not in sample data")

    def read_approaches(self):
        return [ApproachProfile.model_validate(a) for a in _load("pricing_snapshots.json")["approaches"]]

    def read_models(self):
        return [ModelProfile.model_validate(m) for m in _load("pricing_snapshots.json")["models"]]

    def read_task_cases(self, split: str):
        return [DevTaskCase.model_validate(t) for t in _load("dev_task_cases.json") if t["split"] == split]

    def read_sealed_actuals(self, project_id: str):
        # SYNTHETIC analogue. The real aggregate lives only in Zetaris live and the deck.
        return _load("retrospective_actuals_SYNTHETIC.json")

    def write_evidence(self, record: dict) -> SourceRef:
        out = DATA.parent / "sample_evidence_written.jsonl"
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return SourceRef(source_set="evaluation_evidence", record_id=record.get("id", "local"), version="local-unpublished",
                         status=EvidenceStatus.verified)


class RulePolicyInference(Inference):
    """Deterministic stand-in for Planner/Analyst/Critic calls. Produces structure from inputs, not canned prose."""

    def list_models(self):
        return []

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60) -> InferenceResult:
        t0 = time.time()
        text = self._policy(role, user)
        return InferenceResult(text=text, requested_model=None, resolved_model=None, route_id=None,
                               usage={"input_tokens": 0, "output_tokens": 0}, elapsed_s=round(time.time() - t0, 4),
                               execution_kind="rule_policy")

    def _policy(self, role: str, user: str) -> str:
        request = json.loads(user)
        if role == "candidate":
            missing = set(request.get("sample_context_missing", []))
            sections = {key: (f"[{key}] specified from brief and retrieved records" if key not in missing
                              else "NOT SPECIFIED — supporting record not in context")
                        for key in request["task"]["required_elements"]}
            refs = [ref["record_id"] for ref in request["pricing_evidence"]]
            sections["cost_note"] = {"text": "Rates are cited; unverified amounts remain estimates.", "evidence_ids": refs[:1]}
            return json.dumps(sections)
        if role == "critic":
            cases = [case["result"] for case in request["cases"]]
            failed = [r for r in cases if not all(r["elements_present"].values()) or not r["cost_note_sourced"] or r["critical_failures_hit"]]
            target = failed[0] if failed else None
            refs = [target["output_ref"]] if target else []
            return json.dumps({"case_ids": [r["output_ref"] for r in cases],
                "findings": [{"claim": "The sample stress case omits a required element.",
                              "supporting_or_missing_source_ids": refs, "severity": "high", "task_id": target["task_id"]}] if target else [],
                "proposed_action": {"action": "revise_prototype" if target else "finalize",
                    "inputs": {"config_id": target["config_id"], "task_ids": [target["task_id"]]} if target else {},
                    "evidence_ids": refs, "concise_reason": "Repair the observed gap" if target else "All cases pass the deterministic checks",
                    "expected_observation": "Required elements present", "proposed_by": "rule_policy"},
                "expected_check": "Rerun development once" if target else "Freeze without repair"})
        return json.dumps({"note": "rule_policy"})


class SampleMemory(Memory):
    """The real offline reference, with sample storage separate from live memory."""

    def __init__(self, bridge_available: bool = False, trace=None):
        from app.engines.hmem.bridge import HERE, HmemBridge
        self.bridge = HmemBridge(trace, storage_dir=os.getenv("HMEM_SAMPLE_STORAGE_DIR", str(HERE / "storage" / "sample"))) if bridge_available else None

    def _guard(self):
        if self.bridge is None:
            raise SetupIncomplete("H-MEM bridge not pinned/verified for offline use; sample readiness fails rather than "
                                  "substituting a dictionary. See app/engines/hmem/README.md.")

    def remember_confirmed(self, project_scope, payload):
        self._guard()
        return self.bridge.remember_confirmed(project_scope, payload)

    def recall(self, project_scope, query):
        self._guard()
        return self.bridge.recall(project_scope, query)

    def audit(self, project_scope):
        self._guard()
        return self.bridge.audit(project_scope)
