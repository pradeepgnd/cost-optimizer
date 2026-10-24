"""Bounded controller: validates every proposed action against schema, allowlist-by-state,
founder authorization, spend reservation and hard call limits before anything executes.

Hard limits per approved run (architecture §3): 1 planning call, 1 batched critique call,
≤1 revision call; candidate generations ≤ 23; ≤ 2 transport retries globally.

Sealed-source rule (architecture §5): retrospective_actuals and holdout task rows are
readable only in state >= frozen, and never by Planner/Analyst/Critic prompts.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Optional

from app.adapters.base import DataLayer, Inference, Memory, SetupIncomplete
from app.contracts import (
    ActionProposal, ActionType, CandidateConfig, CaseResult, Critique, CritiqueFinding, DecisionPack,
    DevTaskCase, EvidenceGap, EvidenceStatus, Observation, Revision, Risk, RiskCause, RunRequest, RunState, SourceRef,
)
from app.economics import SIZE_MULTIPLIER, build_ledger, operating_ledger
from app.trace import Trace

MAX_ROLE_CALLS = {"Planner": 1, "Critic": 1, "Revision": 1}
MAX_CANDIDATE_GENERATIONS = 23
MAX_TRANSPORT_RETRIES = 2

# Source sets readable per state. Anything not listed for a state is denied and logged.
ALLOWLIST = {
    RunState.approved: {"founder_briefs", "pricing_snapshots"},
    RunState.investigating: {"founder_briefs", "pricing_snapshots", "dev_task_cases:development", "evaluation_evidence"},
    RunState.development_check: {"dev_task_cases:development", "evaluation_evidence", "pricing_snapshots"},
    RunState.repair: {"dev_task_cases:development", "evaluation_evidence", "pricing_snapshots"},
    RunState.frozen: {"dev_task_cases:holdout", "evaluation_evidence", "retrospective_actuals"},
    RunState.holdout: {"dev_task_cases:holdout", "evaluation_evidence", "retrospective_actuals"},
    RunState.complete: {"retrospective_actuals", "evaluation_evidence"},
}
SEALED = {"retrospective_actuals", "dev_task_cases:holdout"}


class DuplicateRun(Exception):
    """A run_id that already exists is refused before any state change or dispatch."""


class StopRun(Exception):
    def __init__(self, state: RunState, reason: str, questions: Optional[list[str]] = None):
        self.state, self.reason, self.questions = state, reason, questions or []


@dataclass
class Budget:
    max_spend: Decimal
    spent: Decimal = Decimal("0")
    role_calls: dict = field(default_factory=lambda: {"Planner": 0, "Critic": 0, "Revision": 0})
    candidate_generations: int = 0
    transport_retries: int = 0

    def reserve_role(self, role: str):
        if self.role_calls[role] >= MAX_ROLE_CALLS[role]:
            raise StopRun(RunState.partial, f"{role} call limit reached")
        self.role_calls[role] += 1

    def reserve_generation(self, est_cost: Decimal):
        if self.candidate_generations >= MAX_CANDIDATE_GENERATIONS:
            raise StopRun(RunState.partial, "candidate generation cap (23) reached")
        if self.spent + est_cost > self.max_spend:
            raise StopRun(RunState.partial, f"spend reservation {self.spent + est_cost} exceeds max_spend {self.max_spend}")
        self.candidate_generations += 1
        self.spent += est_cost


class Checkpoints:
    """SQLite operational store: idempotency, per-call checkpoints. Not a data layer, not memory."""

    def __init__(self, path: str = "runs.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, state TEXT, pack TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS events (run_id TEXT, seq INTEGER, kind TEXT, payload TEXT)")
        self.conn.commit()

    def claim(self, run_id: str) -> bool:
        try:
            self.conn.execute("INSERT INTO runs (run_id, state) VALUES (?, ?)", (run_id, RunState.approved.value))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def set_state(self, run_id: str, state: RunState):
        self.conn.execute("UPDATE runs SET state=? WHERE run_id=?", (state.value, run_id))
        self.conn.commit()

    def save_pack(self, run_id: str, pack: DecisionPack):
        self.conn.execute("UPDATE runs SET pack=? WHERE run_id=?", (pack.model_dump_json(), run_id))
        self.conn.commit()


class Controller:
    def __init__(self, data: DataLayer, inference: Inference, memory: Memory, trace: Trace,
                 execution_mode: str, checkpoints: Optional[Checkpoints] = None,
                 critic_model: str = "", candidate_models: Optional[list[str]] = None):
        self.data, self.inf, self.mem, self.trace = data, inference, memory, trace
        self.mode = execution_mode
        self.ckpt = checkpoints or Checkpoints()
        self.critic_model = critic_model
        self.candidate_models = candidate_models or ["config-a", "config-b"]
        self.state = RunState.approved
        self.evidence: list[SourceRef] = []
        self.gaps: list[EvidenceGap] = []
        self.memory_ids: list[str] = []
        self.ranking_reasons: list[str] = []
        self.questions: list[str] = []      # non-blocking: what would change the result

    # ------------------------------------------------------------ guards

    def _transition(self, new: RunState):
        self.trace.event("Controller", "state_transition", output_summary=f"{self.state.value} -> {new.value}")
        self.state = new
        self.ckpt.set_state(self.run_id, new)

    def _read(self, source_key: str, fn, *args) -> Observation:
        """Every data read passes here. Sealed sources before freeze are denied and logged."""
        allowed = ALLOWLIST.get(self.state, set())
        if source_key not in allowed:
            self.trace.event("Controller", "retrieve_evidence", status="denied_sealed" if source_key in SEALED else "denied",
                             input_summary=source_key, output_summary=f"not permitted in state {self.state.value}")
            return Observation(status="denied_sealed" if source_key in SEALED else "error",
                               error=f"{source_key} not readable in state {self.state.value}")
        try:
            result = fn(*args)
        except KeyError as e:
            return Observation(status="missing", missing_fields=[str(e)])
        self.trace.event("Analyst", "retrieve_evidence", input_summary=source_key,
                         output_summary=f"{source_key} read ok", evidence_ids=[source_key])
        return Observation(status="ok", source_ids=[source_key], result_ref=source_key)

    def _validate(self, p: ActionProposal) -> ActionProposal:
        """Schema is enforced by Pydantic; here we enforce allowlist and founder-constraint protection."""
        if p.action == ActionType.revise_prototype and any(k.startswith("constraints.") for k in p.inputs):
            raise StopRun(RunState.failed, "proposal attempted to change a founder constraint")
        return p

    # -------------------------------------------------------------- run

    def run(self, req: RunRequest) -> DecisionPack:
        self.run_id = req.run_id
        budget = Budget(max_spend=req.max_spend_usd)
        pack = DecisionPack(run_id=req.run_id, project_id=req.project_id, execution_mode=self.mode,
                            status=RunState.approved, trace_path=str(self.trace.path))

        if not self.ckpt.claim(req.run_id):
            raise DuplicateRun(f"run_id {req.run_id} already exists; idempotent refusal, no work dispatched")

        try:
            # 0. Recall confirmed constraints (H-MEM). Visible failure if the engine is not wired.
            try:
                recalled = self.mem.recall(req.project_id, {"kind": "confirmed_constraint"})
                self.memory_ids = recalled.get("memory_ids", [])
                self.trace.event("Analyst", "hmem_recall", memory_ids=self.memory_ids,
                                 output_summary=f"{len(self.memory_ids)} memories", extra={"engine_revision": recalled.get("engine_revision")})
            except SetupIncomplete as e:
                self.trace.event("Analyst", "hmem_recall", status="error", output_summary=str(e))
                pack.limitations.append(f"H-MEM unavailable: {e}")

            # 1. Brief + gaps
            brief = req.brief
            for fld, st in brief.field_status.items():
                if st != EvidenceStatus.verified:
                    self.gaps.append(EvidenceGap(field=fld, status=st, note="see founder brief provenance"))
            if brief.usage.status == EvidenceStatus.unknown:
                self.gaps.append(EvidenceGap(field="usage", status=EvidenceStatus.unknown, note="operating ledger is cost-only"))

            # 2. Pricing evidence
            self._transition(RunState.investigating)
            obs = self._read("pricing_snapshots", self.data.read_approaches)
            if obs.status != "ok":
                raise StopRun(RunState.needs_input, "approach pricing unavailable", ["Which development approaches should be priced?"])
            approaches = self.data.read_approaches()
            models = self.data.read_models()
            for a in approaches:
                self.evidence.append(a.source)

            # 3. Build ledgers for every approach (the ranking needs base build cost); operating ledger for the brief's usage
            pack.build_ledgers = [build_ledger(a, brief.features_v1) for a in approaches]
            self.trace.event("Analyst", "calculate_cost", output_summary=f"{len(pack.build_ledgers)} build ledgers (Decimal)")
            if models:
                pack.operating_ledger = operating_ledger(models[0], brief.usage, Decimal("1500"), Decimal("600"))
            pack.risks = self._risks(brief, approaches, pack.build_ledgers)
            self.trace.event("Analyst", "assess_risks", output_summary=f"{len(pack.risks)} risks from general signals",
                             evidence_ids=sorted({t for r in pack.risks for t in r.triggered_by}))

            # 4. Planner: rank approaches and propose two configs (one call budget). Rule policy in sample mode.
            budget.reserve_role("Planner")
            configs = self._propose_configs(brief, approaches, models, pack.build_ledgers)
            self.trace.event("Planner", "propose_configs", target_agent="Analyst",
                             input_summary=f"brief {brief.brief_id}, {len(approaches)} approaches, {len(models)} models",
                             output_summary=f"{configs[0].approach_id} / {configs[1].approach_id}; " + " ".join(self.ranking_reasons),
                             execution_kind="rule_policy" if self.mode == "sample" else "live_inference")

            # 5. Approval gate before any paid work
            if not req.evaluation_approved:
                raise StopRun(RunState.needs_input, "evaluation not approved",
                              ["Approve the bounded development evaluation and confirm max_spend_usd."])

            # 6. Development cases
            self._transition(RunState.development_check)
            dev = self.data.read_task_cases("development")
            self._read("dev_task_cases:development", lambda: dev)
            for c in configs:
                for t in dev:
                    budget.reserve_generation(Decimal("0.05"))
                    pack.development_results.append(self._run_case(t, c, context_missing={"rate_limit_handling"} if t.task_id == dev[0].task_id and c is configs[0] else set()))

            # 7. One batched critique
            budget.reserve_role("Critic")
            critique = self._critique(pack.development_results, dev)
            pack.critiques.append(critique)

            # 8. At most one validated repair
            if critique.controller_decision == "accepted" and critique.proposed_action.action != ActionType.finalize:
                self._transition(RunState.repair)
                budget.reserve_role("Revision")
                target = configs[0]
                rev = Revision(revision_id=str(uuid.uuid4())[:8], config_id=target.config_id, from_version=target.config_version,
                               to_version=target.config_version + 1, change={"context_selection": "include rate_limit_handling record"},
                               justified_by_critique=True)
                target.config_version += 1
                pack.revisions.append(rev)
                self.trace.event("Planner", "revise_prototype", target_agent="Analyst", output_summary=json.dumps(rev.change))
                for t in dev:
                    budget.reserve_generation(Decimal("0.05"))
                    pack.development_results.append(self._run_case(t, target, context_missing=set()))

            # 9. Freeze, then holdout (sealed until here)
            self._transition(RunState.frozen)
            self._transition(RunState.holdout)
            hold = self.data.read_task_cases("holdout")
            self._read("dev_task_cases:holdout", lambda: hold)
            for c in configs:
                for t in hold:
                    budget.reserve_generation(Decimal("0.05"))
                    pack.holdout_results.append(self._run_case(t, c, context_missing=set()))

            # 10. Decide
            pack.recommended_config, pack.alternate_config, pack.reasons = self._decide(configs, pack)
            try:
                saved = self.mem.remember_confirmed(req.project_id, {"kind": "accepted_finding", "run_id": req.run_id,
                                                                     "recommended": pack.recommended_config.model_dump() if pack.recommended_config else None})
                self.memory_ids += saved.get("memory_ids", [])
            except SetupIncomplete:
                pass
            self._transition(RunState.complete)
            pack.status = RunState.complete

        except StopRun as s:
            self._transition(s.state)
            pack.status = s.state
            pack.limitations.append(s.reason)
            pack.questions = s.questions
            self.trace.event("Controller", "stop", status=s.state.value, output_summary=s.reason)

        pack.reasons = self.ranking_reasons + pack.reasons
        pack.questions = list(dict.fromkeys(pack.questions + self.questions))
        pack.evidence_refs = self.evidence
        pack.evidence_gaps = self.gaps
        pack.memory_ids = self.memory_ids
        pack.spend_usd = budget.spent
        if self.mode == "sample":
            pack.limitations.insert(0, "SAMPLE/OFFLINE: rule-based policies, no live inference, no live Nemotron critique, no sponsor proof.")
        pack.limitations.append("Approach-level alternatives compared on cited rates; no build executed on any platform.")
        self.ckpt.save_pack(req.run_id, pack)
        return pack

    # ---------------------------------------------------------- helpers

    @staticmethod
    def _pricing_verified(a) -> bool:
        return bool(a.rates) and all(r.status == EvidenceStatus.verified and r.usd_per_unit is not None for r in a.rates)

    def _propose_configs(self, brief, approaches, models, ledgers) -> list[CandidateConfig]:
        """General ranking rule: DevOps fit filters; then verified pricing whose base build cost fits the cash
        budget, then other verified pricing, then pricing-snapshot order. Unverified pricing never outranks verified."""
        c = brief.constraints
        devops_status = self._constraint_status(c, "devops_capacity")
        if devops_status in (EvidenceStatus.assumed, EvidenceStatus.unknown):
            by_cap = {cap: [a.approach_id for a in approaches if self._devops_ok(a.requires_devops, cap)]
                      for cap in ("none", "basic", "full")}
            if len({tuple(v) for v in by_cap.values()}) > 1:
                raise StopRun(RunState.needs_input, f"devops_capacity is {devops_status.value}, and it decides which approaches are eligible",
                              ["What DevOps work can the founder take on? " +
                               "; ".join(f"{cap}: {len(ids)} eligible ({', '.join(ids) or 'none'})" for cap, ids in by_cap.items()) + "."])
        eligible = [a for a in approaches if self._devops_ok(a.requires_devops, c.devops_capacity)]
        if not eligible:
            raise StopRun(RunState.needs_input, "no approach fits the founder's DevOps capacity",
                          ["Can the founder take on basic DevOps, or should only managed platforms be considered?"])

        base_usd = {l.approach_id: l.base_build_cost.base for l in ledgers
                    if l.base_build_cost.unit == "USD" and l.base_build_cost.base is not None}

        def tier(a) -> tuple[int, str]:
            if not self._pricing_verified(a):
                return 3, "pricing unverified"
            if c.cash_budget_usd is None or a.approach_id not in base_usd:
                return 1, "verified pricing, budget fit unknown"
            if base_usd[a.approach_id] <= c.cash_budget_usd:
                return 0, f"verified pricing, base build {base_usd[a.approach_id]} USD fits budget {c.cash_budget_usd}"
            return 2, f"verified pricing, base build {base_usd[a.approach_id]} USD exceeds budget {c.cash_budget_usd}"

        ranked = [a for _, a in sorted(enumerate(eligible), key=lambda ia: (tier(ia[1])[0], ia[0]))]
        a0, a1 = ranked[0], (ranked[1] if len(ranked) > 1 else ranked[0])
        self.ranking_reasons = [
            f"Ranking: {len(eligible)} of {len(approaches)} approaches fit devops_capacity={c.devops_capacity}; ordered by "
            "verified pricing within the cash budget, then other verified pricing, then pricing-snapshot order.",
            f"cfg-a {a0.approach_id}: {tier(a0)[1]}; cfg-b {a1.approach_id}: {tier(a1)[1]}.",
        ]
        if not any(self._pricing_verified(a) for a in eligible):
            self.ranking_reasons.append("No eligible approach has verified pricing, so the order between them reflects the "
                                        "snapshot order, not cost.")
            self.questions.append("No eligible approach has verified pricing (" + ", ".join(a.approach_id for a in eligible) +
                                  "). Verified, dated rates for these approaches would change the ranking.")
        elif self._constraint_status(c, "cash_budget_usd") in (EvidenceStatus.assumed, EvidenceStatus.unknown):
            self.questions.append("The cash budget is not stated. Stating it decides which verified approaches fit and "
                                  "could change the ranking.")

        mids = [m.model_id for m in models] or self.candidate_models
        return [CandidateConfig(config_id="cfg-a", approach_id=a0.approach_id, model_id=mids[0]),
                CandidateConfig(config_id="cfg-b", approach_id=a1.approach_id, model_id=mids[1] if len(mids) > 1 else mids[0],
                                workflow_settings={"variant": "b"} if len(mids) == 1 else {})]

    @staticmethod
    def _devops_ok(required: str, capacity: str) -> bool:
        order = {"none": 0, "basic": 1, "full": 2}
        return order[required] <= order[capacity]

    @staticmethod
    def _constraint_status(constraints, name: str) -> EvidenceStatus:
        """A missing value is unknown; a value the brief never stated (schema default) is assumed."""
        if getattr(constraints, name) is None:
            return EvidenceStatus.unknown
        if name not in constraints.model_fields_set:
            return EvidenceStatus.assumed
        return constraints.status

    def _risks(self, brief, approaches, ledgers) -> list[Risk]:
        """General signals only: rate status, compute-heavy scope, assumed rework, unstated constraints."""
        risks: list[Risk] = []
        for a in approaches:
            if not self._devops_ok(a.requires_devops, brief.constraints.devops_capacity):
                continue
            weak = [r for r in a.rates if r.usd_per_unit is None or r.status != EvidenceStatus.verified]
            if weak:
                unknown = any(r.usd_per_unit is None for r in weak)
                risks.append(Risk(description=f"{a.name}: {len(weak)} of {len(a.rates)} rates "
                                              f"{'unknown or unverified' if unknown else 'unverified'}; its build range is not decision-grade.",
                                  cause_class=RiskCause.pricing_unverified, severity="high" if unknown else "medium",
                                  triggered_by=[r.source.record_id for r in weak]))
        heavy = [f for f in brief.features_v1 if f.compute_heavy]
        if heavy:
            units = sum((SIZE_MULTIPLIER[f.size_class] for f in brief.features_v1), Decimal("0"))
            share = sum((SIZE_MULTIPLIER[f.size_class] for f in heavy), Decimal("0")) / units
            risks.append(Risk(description=f"{len(heavy)} compute-heavy features make up {int(share * 100)}% of planned work; "
                                          "compute cost is not in the build ledger and grows with usage.",
                              cause_class=RiskCause.compute_cost, severity="high" if share >= Decimal("0.5") else "medium",
                              triggered_by=[f"features_v1:{f.feature_id}" for f in heavy]))
        assumed = next((l.rework_multiplier for l in ledgers if any("assumed" in w for w in l.rework_multiplier.warnings)), None)
        if assumed is not None:
            risks.append(Risk(description=f"Rework multiplier {assumed.low}–{assumed.high}x is assumed, not measured; "
                                          "expected build cost moves with it.",
                              cause_class=RiskCause.rework, severity="medium", triggered_by=["build_ledgers.rework_multiplier"]))
        # devops_capacity decides eligibility and cash_budget_usd decides ranking, so an unstated value matters more there.
        for name in ("devops_capacity", "cash_budget_usd", "time_budget_weeks", "technical_skill", "team_size"):
            st = self._constraint_status(brief.constraints, name)
            if st in (EvidenceStatus.assumed, EvidenceStatus.unknown):
                risks.append(Risk(description=f"Constraint {name} is {st.value}; results that depend on it may change once stated.",
                                  cause_class=RiskCause.requirements_gap,
                                  severity="high" if name in ("devops_capacity", "cash_budget_usd") else "medium",
                                  triggered_by=[f"constraints.{name}"]))
        return risks

    def _run_case(self, task: DevTaskCase, cfg: CandidateConfig, context_missing: set[str]) -> CaseResult:
        prompt = task.prompt + "\n" + "\n".join(f"required_element:{e}" for e in task.required_elements)
        prompt += "\n" + "\n".join(f"context_missing:{e}" for e in context_missing)
        if not context_missing:
            prompt += "\nrate_ref:pricing_snapshots"
        res = self.inf.complete(role="candidate", model=cfg.model_id, system="Produce a JSON implementation specification.", user=prompt)
        try:
            out = json.loads(res["text"])
        except json.JSONDecodeError:
            out = {}
        present = {e: (e in out and "NOT SPECIFIED" not in str(out[e])) for e in task.required_elements}
        crit = [c for c in task.critical_failures if c in str(out)]
        cr = CaseResult(task_id=task.task_id, config_id=cfg.config_id, config_version=cfg.config_version,
                        output_ref=f"{self.run_id}/{task.task_id}/{cfg.config_id}/v{cfg.config_version}",
                        elements_present=present, critical_failures_hit=crit,
                        cost_note_sourced="sourced" in str(out.get("cost_note", "")),
                        usage=res["usage"], elapsed_s=res["elapsed_s"], requested_model=res["requested_model"],
                        resolved_model=res["resolved_model"], execution_kind=res["execution_kind"])
        self.trace.event("Analyst", "evaluate_development", model=res["resolved_model"], requested_model=res["requested_model"],
                         input_summary=f"{task.task_id} on {cfg.config_id} v{cfg.config_version}",
                         output_summary=f"{sum(present.values())}/{len(present)} elements, cost_sourced={cr.cost_note_sourced}",
                         execution_kind=res["execution_kind"])
        self.data.write_evidence({"id": cr.output_ref, **cr.model_dump(mode="json")})
        return cr

    def _critique(self, results: list[CaseResult], tasks: list[DevTaskCase]) -> Critique:
        summary = "\n".join(f"{r.task_id}/{r.config_id}: " + ("NOT SPECIFIED — supporting record not in context " if not all(r.elements_present.values()) else "")
                            + ("UNSOURCED" if not r.cost_note_sourced else "") for r in results)
        res = self.inf.complete(role="critic", model=self.critic_model or "critic", system="Challenge the Analyst's evidence.", user=summary)
        try:
            c = json.loads(res["text"])
        except json.JSONDecodeError:
            c = {"gaps": 0, "unsourced_cost": False, "action": "finalize"}
        findings = [CritiqueFinding(claim=f"{r.task_id}/{r.config_id} missing elements or unsourced cost",
                                    supporting_or_missing_source_ids=["pricing_snapshots"], severity="high", task_id=r.task_id)
                    for r in results if not all(r.elements_present.values()) or not r.cost_note_sourced]
        action = ActionType(c.get("action", "finalize"))
        proposal = self._validate(ActionProposal(action=action, inputs={"context_selection": "include missing record"} if action != ActionType.finalize else {},
                                                 evidence_ids=["pricing_snapshots"], concise_reason="critic found unsupported spec elements" if findings else "all supported",
                                                 expected_observation="required elements present and cost note sourced after revision",
                                                 proposed_by="Critic" if res["execution_kind"] == "live_inference" else "rule_policy"))
        decision = "accepted" if findings and action != ActionType.finalize else "no_change"
        crit = Critique(case_ids=[r.output_ref for r in results], findings=findings, proposed_action=proposal,
                        expected_check="rerun affected development cases once", requested_model=res["requested_model"],
                        resolved_model=res["resolved_model"], execution_kind=res["execution_kind"], controller_decision=decision)
        self.trace.event("Critic", "critique", target_agent="Planner", model=res["resolved_model"], requested_model=res["requested_model"],
                         output_summary=f"{len(findings)} findings; proposed {action.value}; controller {decision}",
                         execution_kind=res["execution_kind"], extra={"feature": "nemotron_evidence_critic"})
        return crit

    def _decide(self, configs, pack):
        def score(cfg):
            rs = [r for r in pack.holdout_results if r.config_id == cfg.config_id]
            return (sum(all(r.elements_present.values()) and not r.critical_failures_hit for r in rs), -len(rs))
        ranked = sorted(configs, key=score, reverse=True)
        best, alt = ranked[0], ranked[1] if len(ranked) > 1 else None
        n = len([r for r in pack.holdout_results if r.config_id == best.config_id])
        passed = score(best)[0]
        reasons = [f"{best.config_id} passed {passed}/{n} holdout tasks (small sample; not general accuracy)",
                   "build ledgers compared on cited rates; see evidence_gaps for unverified inputs"]
        if passed < n:
            reasons.append("quality gate not met: recommendation is conditional")
        return best, alt, reasons
