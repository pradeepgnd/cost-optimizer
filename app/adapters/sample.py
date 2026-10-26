"""SAMPLE_MODE adapters: bundled data, rule-based policies, zero network.

These never replay saved model answers or read output_examples. They run the same
controller with explicit rules in place of model calls. Every decision is labeled
execution_kind=rule_policy with model=None.
"""
from __future__ import annotations

import json
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
    def __init__(self, evidence_path=None):
        self.manifest = _load("manifest.json")
        self.evidence_path = Path(evidence_path) if evidence_path else DATA.parent / "sample_evidence_written.jsonl"

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
        if "id" not in record:
            raise ValueError("sample evidence needs an ID")
        try:
            previous, source = self.read_evidence(record["id"])
            if previous != record:
                raise ValueError("sample evidence ID conflict")
            return source
        except KeyError:
            pass
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        with self.evidence_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return self.read_evidence(record["id"])[1]

    def read_evidence(self, record_id):
        from app.source_snapshots import canonical, digest
        if self.evidence_path.exists():
            for line in self.evidence_path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                if record.get("id") == record_id:
                    sha = digest(canonical(record))
                    return record, SourceRef(source_set="evaluation_evidence", record_id=record_id, version=sha,
                        status=EvidenceStatus.unverified, content_sha256=sha, origin_url=f"sample://evidence/{record_id}")
        raise KeyError("sample evidence not found")


class RulePolicyInference(Inference):
    """Sample mode makes no inference calls and produces no outputs. The controller estimates tokens with the
    4/3 rule instead; any attempt to call a model here is a bug and fails loudly rather than inventing text."""

    def list_models(self):
        return []

    def complete(self, *, role, model, system, user, json_schema=None, timeout_s=60, max_tokens=None) -> InferenceResult:
        raise RuntimeError(f"sample mode makes no inference calls (role {role}); no output is fabricated")


class SampleMemory(Memory):
    """Offline H-MEM delegation. The same real bridge runs without provider calls."""

    def __init__(self, bridge_available: bool = False):
        self.bridge_available = bridge_available

    def _guard(self):
        if not self.bridge_available:
            raise SetupIncomplete("H-MEM bridge not pinned/verified for offline use; sample readiness fails rather than "
                                  "substituting a dictionary. See app/engines/hmem/README.md.")
        from app.engines.hmem.bridge import HmemBridge
        return HmemBridge()

    def remember_confirmed(self, project_scope, payload):
        return self._guard().remember_confirmed(project_scope, payload)

    def recall(self, project_scope, query):
        return self._guard().recall(project_scope, query)

    def audit(self, project_scope):
        return self._guard().audit(project_scope)
