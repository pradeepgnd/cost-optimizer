"""SAMPLE_MODE adapters: bundled data, rule-based policies, zero network.

These never replay saved model answers or read output_examples. They run the same
controller with explicit rules in place of model calls. Every decision is labeled
execution_kind=rule_policy with model=None.
"""
from __future__ import annotations

import json
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
        if role == "candidate":
            # Produce a spec skeleton that covers required elements named in the prompt, deliberately
            # omitting any element the prompt marks as "context not retrieved" so the critic has work to do.
            required = re.findall(r"required_element:(\w+)", user)
            missing_ctx = set(re.findall(r"context_missing:(\w+)", user))
            sections = {k: (f"[{k}] specified from brief and retrieved records" if k not in missing_ctx
                            else f"[{k}] NOT SPECIFIED — supporting record not in context") for k in required}
            sections["cost_note"] = "cost_note: " + ("sourced:rate_ref" if "rate_ref:" in user else "UNSOURCED")
            return json.dumps(sections)
        if role == "critic":
            gaps = re.findall(r"NOT SPECIFIED — supporting record not in context", user)
            unsourced = "UNSOURCED" in user
            return json.dumps({"gaps": len(gaps), "unsourced_cost": unsourced,
                               "action": "retrieve_evidence" if gaps else ("revise_prototype" if unsourced else "finalize")})
        return json.dumps({"note": "rule_policy"})


class SampleMemory(Memory):
    """Offline H-MEM path. Until the sponsor reference is pinned and verified offline, this adapter
    refuses to pretend: it raises SetupIncomplete so sample readiness fails loudly (architecture §6)."""

    def __init__(self, bridge_available: bool = False):
        self.bridge_available = bridge_available

    def _guard(self):
        if not self.bridge_available:
            raise SetupIncomplete("H-MEM bridge not pinned/verified for offline use; sample readiness fails rather than "
                                  "substituting a dictionary. See app/engines/hmem/README.md.")

    def remember_confirmed(self, project_scope, payload):
        self._guard()

    def recall(self, project_scope, query):
        self._guard()

    def audit(self, project_scope):
        self._guard()
