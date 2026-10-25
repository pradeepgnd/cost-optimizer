"""Real memory must affect ranking, preserve scope, and respect newer input."""
import json
from decimal import Decimal

from app.adapters.sample import RulePolicyInference, SampleDataLayer
from app.contracts import ApproachProfile, EvidenceStatus, Rate, RateCategory, RunRequest, RunState, SourceRef
from app.controller import Checkpoints, Controller
from app.engines.hmem.bridge import HmemBridge
from app.trace import Trace


class PricingData(SampleDataLayer):
    def read_approaches(self):
        rows = []
        for name, price, devops in [("self-hosted", "1", "full"), ("managed", "2", "none")]:
            source = SourceRef(source_set="pricing_snapshots", record_id=name, version="synthetic-test")
            rows.append(ApproachProfile(approach_id=name, name=name, requires_devops=devops,
                tokens_per_task_class={"M": Decimal("1000000")}, source=source,
                rates=[Rate(category=RateCategory.input_tokens, unit="1M", usd_per_unit=Decimal(price),
                            status=EvidenceStatus.verified, source=source)]))
        return rows


def run_case(tmp_path, run_id, devops=None, project="project-A", verified=True):
    constraints = {"cash_budget_usd": "5", "status": "verified" if verified else "reconstructed"}
    if devops is not None:
        constraints["devops_capacity"] = devops
    request = RunRequest.model_validate({"run_id": run_id, "project_id": project,
        "brief": {"brief_id": "test-brief", "brief_version": run_id, "product_concept": "synthetic memory test",
                  "target_user": "test", "features_v1": [{"feature_id": "F1", "title": "test", "size_class": "M"}],
                  "constraints": constraints}, "evaluation_approved": False})
    trace = Trace(run_id, "sample", str(tmp_path / "logs"), echo=False)
    checkpoints = Checkpoints(str(tmp_path / "runs.db"))
    try:
        controller = Controller(PricingData(), RulePolicyInference(), HmemBridge(storage_dir=tmp_path / "memory"),
                                trace, "sample", checkpoints)
        pack = controller.run(request)
    finally:
        checkpoints.conn.close()
    return pack, request, [json.loads(line) for line in trace.path.read_text().splitlines()]


def test_restart_recall_affects_eligibility_and_current_brief_supersedes_it(tmp_path):
    first, _, _ = run_case(tmp_path, "initial", "full")
    assert any("cfg-a self-hosted" in reason for reason in first.reasons)
    resumed, original, trace = run_case(tmp_path, "resumed")
    assert any("applied confirmed devops_capacity=full" in reason for reason in resumed.reasons)
    assert any("cfg-a self-hosted" in reason for reason in resumed.reasons)
    assert "devops_capacity" not in original.brief.constraints.model_fields_set
    assert any(event["action"] == "hmem_constraint_applied" for event in trace)
    assert any(ref.source_set == "hmem_confirmed_constraints" for ref in resumed.evidence_refs)
    changed, _, _ = run_case(tmp_path, "new-confirmation", "none")
    assert any("overrides the older devops_capacity" in reason for reason in changed.reasons)
    assert any("cfg-a managed" in reason for reason in changed.reasons)
    later, _, _ = run_case(tmp_path, "later")
    assert any("applied confirmed devops_capacity=none" in reason for reason in later.reasons)
    assert any("cfg-a managed" in reason for reason in later.reasons)
    assert not any("applied confirmed devops_capacity=full" in reason for reason in later.reasons)
    other, _, _ = run_case(tmp_path, "other-project", project="project-B")
    assert any("DevOps" in question for question in other.questions)
    assert not any("applied confirmed devops_capacity" in reason for reason in other.reasons)


def test_reconstructed_input_is_not_promoted_to_confirmed_memory(tmp_path):
    run_case(tmp_path, "unconfirmed", "full", verified=False)
    records = HmemBridge(storage_dir=tmp_path / "memory").recall("project-A", {"kind": "confirmed_constraint"})
    assert records["memory_ids"] == []


def test_missing_memory_returns_partial_before_evaluation(tmp_path):
    from app.adapters.sample import SampleMemory
    request = RunRequest.model_validate({"run_id": "missing-engine", "project_id": "project-A",
        "brief": {"brief_id": "b", "brief_version": "1", "product_concept": "test", "target_user": "test",
                  "features_v1": [], "constraints": {}}, "evaluation_approved": True})
    checkpoints = Checkpoints(str(tmp_path / "missing.db"))
    try:
        pack = Controller(PricingData(), RulePolicyInference(), SampleMemory(),
                          Trace(request.run_id, "sample", str(tmp_path / "logs"), echo=False),
                          "sample", checkpoints).run(request)
    finally:
        checkpoints.conn.close()
    assert pack.status == RunState.partial
    assert pack.development_results == [] and pack.spend_usd == 0
    assert any("H-MEM unavailable" in line for line in pack.limitations)
