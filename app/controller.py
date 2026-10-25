"""Bounded controller: validates every proposed action against schema, allowlist-by-state,
founder authorization, spend reservation and hard call limits before anything executes.

v4 feature-sampling loop (Planning/07 §3): estimate every feature × candidate; with approval, run each
feature's example input on each candidate (live, measured usage) or nothing (sample, 4/3 estimates);
deterministic rubric checks and human review decide pass/fail; the Critic only flags and proposes one
action; at most one validated repair; then the stage cost tables and the model stack.

Hard limits per approved run: 1 Planner call, 1 Critic call, ≤1 revision (repair) call;
candidate generations ≤ 30; ≤ 2 transport retries globally.

Sealed-source rule (architecture §5): retrospective_actuals and holdout task rows are
readable only in state >= frozen, and never by Planner/Analyst/Critic prompts.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.adapters.base import DataLayer, Inference, Memory, SetupIncomplete
from app.contracts import (
    ActionProposal, ActionType, BuildPanel, Critique, CritiqueFinding, DecisionPack, EvidenceGap, EvidenceStatus,
    FeatureProfile, FeatureRun, FeatureSample, ModelProfile, ModelStackEntry, Observation, OutputCapRerun,
    RateCategory, Revision, Risk, RiskCause, RunRequest, RunState, ShortlistEntry, SourceRef, TokenUsage,
)
from app.economics import (SIZE_MULTIPLIER, build_ledger, cost_per_call, estimate_feature_tokens,
                           recommend_model_stack, stage_cost_table)
from app.rubric import evaluate, json_fields_requested, parse_json_object
from app.trace import Trace

MAX_ROLE_CALLS = {"Planner": 1, "Critic": 1, "Revision": 1}
MAX_CANDIDATE_GENERATIONS = 30
MAX_TRANSPORT_RETRIES = 2
SAMPLES_PER_PAIR = 2                      # 07 §7 call budget; 1 when 2 would not fit under the cap
CANDIDATE_TIERS = ("frontier", "mid_tier", "open_source")
AUTO_ROUTE = "meterless/auto"             # a router alias, never a candidate or a Critic route
DEFAULT_RESERVATION = Decimal("0.05")     # per call, when rates or estimates are unknown
RESERVATION_HEADROOM = Decimal("3")       # estimated per-call cost × 3, reconciled to the measured cost
MAX_DOMAIN_RISKS = 8
CRITIC_FINDING_KINDS = {"unsupported_claim", "token_gap", "output_too_long"}
VERDICT_KEYS = {"pass", "passed", "passes", "fail", "failed", "verdict", "score", "grade", "approved"}
NOT_ADVICE = "Model-generated; not legal, medical or financial advice."
AUDIO_NOT_EXECUTABLE = ("audio modality: not executable through chat completions; audio is priced from the "
                        "per-second conversion (estimated) and no audio is sent")

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

    def reserve_spend(self, est_cost: Decimal):
        if self.spent + est_cost > self.max_spend:
            raise StopRun(RunState.partial, f"spend reservation {self.spent + est_cost} exceeds max_spend {self.max_spend}")
        self.spent += est_cost

    def reserve_generation(self, est_cost: Decimal):
        if self.candidate_generations >= MAX_CANDIDATE_GENERATIONS:
            raise StopRun(RunState.partial, f"candidate generation cap ({MAX_CANDIDATE_GENERATIONS}) reached")
        self.reserve_spend(est_cost)
        self.candidate_generations += 1

    def reconcile(self, reserved: Decimal, actual: Optional[Decimal]):
        """Replace a reservation with the measured cost once known; an unknown cost keeps the reservation."""
        if actual is not None:
            self.spent += actual - reserved


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


def _measured_usage(usage: dict) -> tuple[Optional[TokenUsage], Optional[str]]:
    """TokenUsage from OpenAI-compatible usage fields only; completion_tokens already includes reasoning."""
    pt, ct = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if not isinstance(pt, int) or not isinstance(ct, int):
        return None, "response carried no prompt_tokens/completion_tokens"
    rt = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    try:
        return TokenUsage(input_tokens=Decimal(pt), output_tokens=Decimal(ct),
                          reasoning_tokens=None if not isinstance(rt, int) else Decimal(rt),
                          basis="measured", method="API usage fields"), None
    except ValueError:
        return None, "reasoning_tokens exceeds completion_tokens; confirm Nightshift usage semantics"


def _mean_usage(usages: list[TokenUsage]) -> TokenUsage:
    n = Decimal(len(usages))
    reasoning = [u.reasoning_tokens for u in usages]
    return TokenUsage(input_tokens=sum((u.input_tokens for u in usages), Decimal("0")) / n,
                      output_tokens=sum((u.output_tokens for u in usages), Decimal("0")) / n,
                      reasoning_tokens=None if None in reasoning else sum(reasoning, Decimal("0")) / n,
                      basis="measured", method=f"mean of {len(usages)} API usage samples")


class Controller:
    def __init__(self, data: DataLayer, inference: Inference, memory: Memory, trace: Trace,
                 execution_mode: str, checkpoints: Optional[Checkpoints] = None,
                 critic_model: str = "", planner_model: str = "", open_model: str = ""):
        self.data, self.inf, self.mem, self.trace = data, inference, memory, trace
        self.mode = execution_mode
        self.ckpt = checkpoints or Checkpoints()
        self.critic_model = critic_model
        self.planner_model = planner_model
        self.open_model = open_model          # the pinned Nemotron route (METERLESS_OPEN_MODEL)
        self.state = RunState.approved
        self.evidence: list[SourceRef] = []
        self.gaps: list[EvidenceGap] = []
        self.memory_ids: list[str] = []
        self.questions: list[str] = []      # non-blocking: what would change the result
        self.limitations: list[str] = []
        self.output_caps: list[OutputCapRerun] = []

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
        if any(k.startswith("constraints.") for k in p.inputs):
            raise StopRun(RunState.failed, "proposal attempted to change a founder constraint")
        return p

    def _call(self, role: str, model: str, system: str, user: str, budget: Budget, max_tokens: Optional[int] = None):
        """One Nightshift request with the global transport-retry budget. SetupIncomplete is never swallowed."""
        while True:
            try:
                return self.inf.complete(role=role, model=model, system=system, user=user, max_tokens=max_tokens)
            except SetupIncomplete:
                raise
            except Exception as e:  # transport or HTTP failure
                if budget.transport_retries >= MAX_TRANSPORT_RETRIES:
                    raise StopRun(RunState.partial, f"{role} request to {model} failed: {type(e).__name__}: {str(e)[:200]}")
                budget.transport_retries += 1
                self.trace.event(role, "transport_retry", status="error", retry_count=budget.transport_retries,
                                 requested_model=model, output_summary=f"{type(e).__name__}: {str(e)[:200]}")

    # -------------------------------------------------------------- run

    def run(self, req: RunRequest) -> DecisionPack:
        self.run_id = req.run_id
        budget = Budget(max_spend=req.max_spend_usd)
        pack = DecisionPack(run_id=req.run_id, project_id=req.project_id, execution_mode=self.mode,
                            status=RunState.approved, trace_path=str(self.trace.path))

        if not self.ckpt.claim(req.run_id):
            raise DuplicateRun(f"run_id {req.run_id} already exists; idempotent refusal, no work dispatched")

        brief = req.brief
        candidates: list[ModelProfile] = []
        runs: dict[tuple[str, str], FeatureRun] = {}
        repairs: list[FeatureRun] = []
        try:
            # 0. Recall confirmed assumptions (H-MEM). Visible failure if the engine is not wired.
            try:
                recalled = self.mem.recall(req.project_id, {"kind": "confirmed_constraint"})
                self.memory_ids = recalled.get("memory_ids", [])
                self.trace.event("Analyst", "hmem_recall", memory_ids=self.memory_ids,
                                 output_summary=f"{len(self.memory_ids)} memories", extra={"engine_revision": recalled.get("engine_revision")})
            except SetupIncomplete as e:
                self.trace.event("Analyst", "hmem_recall", status="error", output_summary=str(e))
                self.limitations.append(f"H-MEM unavailable: {e}")

            # 1. Brief provenance
            for fld, st in brief.field_status.items():
                if st != EvidenceStatus.verified:
                    self.gaps.append(EvidenceGap(field=fld, status=st, note="see founder brief provenance"))
            for f in brief.ai_features:
                for fld, st in f.field_status.items():
                    if st != EvidenceStatus.verified:
                        self.gaps.append(EvidenceGap(field=f"ai_features:{f.feature_id}.{fld}", status=st,
                                                     note="founder estimate or default; editable"))

            # 2. Pricing evidence and candidates
            self._transition(RunState.investigating)
            obs = self._read("pricing_snapshots", self.data.read_approaches)
            if obs.status != "ok":
                raise StopRun(RunState.needs_input, "pricing unavailable", ["Which models and approaches should be priced?"])
            approaches = self.data.read_approaches()
            models = self.data.read_models()
            self.evidence += [a.source for a in approaches] + [m.source for m in models]
            route_list = self.inf.list_models() if self.mode == "live" else []   # GET /v1/models is free
            candidates, pack.candidate_shortlist = self._candidates(models, set(route_list) if self.mode == "live" else None)

            # 3. Critic route, before any paid call
            self._check_critic_route(candidates, route_list)

            # 4. Build panel (secondary): missing build inputs add questions and never stop the run
            pack.build_ledgers = [build_ledger(a, brief.features_v1) for a in approaches]
            pack.build_panel = self._build_panel(brief, approaches, pack.build_ledgers)
            self.questions += pack.build_panel.questions
            pack.risks = self._risks(brief, approaches, pack.build_ledgers)
            self.trace.event("Analyst", "build_panel", execution_kind="rule_policy",
                             output_summary=f"{len(pack.build_ledgers)} build ledgers; ranked "
                                            f"{', '.join(pack.build_panel.ranked_approach_ids) or 'none (input missing)'}")

            if not brief.ai_features:
                raise StopRun(RunState.needs_input, "the brief lists no AI features",
                              ["List 2–5 AI features: what the AI does, one example input, and whether it is "
                               "interactive or background (07 §2)."])
            if not candidates:
                raise StopRun(RunState.needs_input, "no candidate models with a tier in the pricing snapshots",
                              ["Which frontier, mid-tier and open-source routes should be compared?"])

            # 5. Estimate every feature × candidate (free); the stage tables exist even if the run stops later
            for f in brief.ai_features:
                est = estimate_feature_tokens(f)
                if f.uses_per_user_month is None:
                    self.questions.append(f"How many times per month does a user use {f.feature_id}? Its cost is unknown without it.")
                if est is None:
                    self.questions.append(f"About how long is a typical {f.feature_id} output (words)? "
                                          "Its token estimate is unknown without it.")
                for m in candidates:
                    runs[(f.feature_id, m.model_id)] = FeatureRun(
                        feature_id=f.feature_id, model_id=m.model_id, tier=m.tier, executed=False, estimated=est,
                        not_executed_reason=self._not_executable(f) or (
                            "sample mode: not executed; tokens estimated with the 4/3 rule" if self.mode == "sample"
                            else "awaiting an approved live run"))
                self.trace.event("Analyst", "estimate_tokens", execution_kind="rule_policy",
                                 input_summary=f.feature_id,
                                 output_summary="unknown" if est is None else
                                 f"estimated {est.input_tokens} in / {est.output_tokens} out per call (4/3 rule)")

            # 6. Approval gate before any paid work
            if not req.evaluation_approved:
                raise StopRun(RunState.needs_input, "evaluation not approved",
                              ["Approve the bounded feature evaluation and confirm max_spend_usd."])

            # 7. Planner: domain risks only, live only
            pack.risks += self._domain_risks(brief, budget)

            # 8. Sampling
            self._transition(RunState.development_check)
            self._sample(brief, candidates, runs, budget, req)

            # 9. Critic flags, one proposal; the controller validates it
            budget.reserve_role("Critic")
            critique, target = self._critique(brief, runs, budget)
            pack.critiques.append(critique)

            # 10. At most one validated repair: a measured re-run with an output cap
            if target is not None:
                self._transition(RunState.repair)
                budget.reserve_role("Revision")
                rev, rerun = self._repair(brief, candidates, runs, target, budget, req)
                pack.revisions.append(rev)
                repairs.append(rerun)

            self._transition(RunState.frozen)
            self._transition(RunState.complete)
            pack.status = RunState.complete

        except StopRun as s:
            self._transition(s.state)
            pack.status = s.state
            self.limitations.append(s.reason)
            pack.questions = s.questions
            self.trace.event("Controller", "stop", status=s.state.value, output_summary=s.reason)

        # 11. Project whatever is known: measured where executed, estimated otherwise
        if runs:
            self._project(pack, brief, candidates, runs)
            pack.feature_runs = list(runs.values()) + repairs
        if pack.status == RunState.complete:
            try:
                saved = self.mem.remember_confirmed(req.project_id, {"kind": "accepted_finding", "run_id": req.run_id,
                                                                     "model_stack": [e.model_dump(mode="json") for e in pack.model_stack]})
                self.memory_ids += saved.get("memory_ids", [])
            except SetupIncomplete:
                pass

        pack.questions = list(dict.fromkeys(pack.questions + self.questions))
        pack.evidence_refs = self.evidence
        pack.evidence_gaps = self.gaps
        pack.memory_ids = self.memory_ids
        pack.spend_usd = budget.spent
        pack.limitations = list(dict.fromkeys(self.limitations))
        if self.mode == "sample":
            pack.limitations.insert(0, "SAMPLE/OFFLINE: no live inference; tokens estimated with the 4/3 rule; rubric "
                                       "checks not run; switch points pending; no sponsor proof.")
        pack.limitations.append("Build panel: approaches compared on cited rates; no build executed on any platform.")
        self.ckpt.save_pack(req.run_id, pack)
        return pack

    # ---------------------------------------------------------- candidates and Critic route

    @staticmethod
    def _rank_key(m: ModelProfile, order: int):
        """Shortlist ranking only: intelligence score (highest first), then market usage rank, then snapshot order."""
        score = m.intelligence.score if m.intelligence else None
        rank = m.market.usage_rank if m.market and m.market.usage_rank is not None else None
        return (score is None, -(score or 0), rank is None, rank or 0, order)

    @staticmethod
    def _price_per_point(m: ModelProfile) -> tuple[Optional[Decimal], Optional[str]]:
        """Blended list price (3:1 input:output, USD per 1M tokens) ÷ intelligence score. Shortlist display only."""
        mk, iq = m.market, m.intelligence
        if mk is None or iq is None or iq.score <= 0 or None in (mk.list_price_input_usd_per_m, mk.list_price_output_usd_per_m):
            return None, None
        blended = (3 * mk.list_price_input_usd_per_m + mk.list_price_output_usd_per_m) / 4
        value = (blended / iq.score).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        return value, (f"USD per 1M tokens per intelligence point: {mk.label} list price blended 3:1 input:output ÷ "
                       f"{iq.score_source} score ({iq.score_date}); reference only, not used in costs")

    def _candidates(self, models: list[ModelProfile], routes: Optional[set[str]]) -> tuple[list[ModelProfile], list[ShortlistEntry]]:
        """One candidate per tier, from Nightshift routes only (live). The open-source tier is always the Nemotron
        route (METERLESS_OPEN_MODEL, else the snapshot row marked required), regardless of score. Other tiers take
        the top-ranked eligible model. Reference data ranks the shortlist and never replaces measurement."""
        def is_route(m):
            return None if routes is None else m.model_id in routes
        chosen: dict[str, tuple[ModelProfile, str]] = {}
        for tier in CANDIDATE_TIERS:
            in_tier = [(i, m) for i, m in enumerate(models) if m.tier == tier]
            if tier == "open_source":
                pinned = next((m for _, m in in_tier if self.open_model and m.model_id == self.open_model), None)
                if self.open_model and pinned is None:
                    raise StopRun(RunState.needs_input, f"METERLESS_OPEN_MODEL {self.open_model} has no price snapshot row",
                                  ["Add a price snapshot for the pinned Nemotron route, or correct METERLESS_OPEN_MODEL."])
                required = pinned or next((m for _, m in in_tier if m.required), None)
                if required is not None:
                    if is_route(required) is False:
                        raise StopRun(RunState.needs_input, f"Nemotron route {required.model_id} is not offered by Nightshift",
                                      ["Enable the Nemotron route in Nightshift, or pin the route it offers in METERLESS_OPEN_MODEL."])
                    chosen[tier] = (required, "the required open-source (Nemotron) route; always a candidate, regardless of score")
                    continue
                self.limitations.append("No Nemotron route is pinned (METERLESS_OPEN_MODEL or a required snapshot row); "
                                        "the open-source candidate is chosen by ranking.")
            eligible = [(i, m) for i, m in in_tier if is_route(m) is not False]
            if not eligible:
                self.limitations.append(f"No {tier} candidate that is a Nightshift route in the pricing snapshots.")
                continue
            top = min(eligible, key=lambda im: self._rank_key(im[1], im[0]))[1]
            chosen[tier] = (top, "top-ranked eligible route in its tier (intelligence score, then market usage rank, "
                                 "then snapshot order)")
        selected = {m.model_id for m, _ in chosen.values()}
        shortlist = []
        for m in models:
            ppp, ppp_label = self._price_per_point(m)
            if m.model_id in selected:
                reason = chosen[m.tier][1]
            elif is_route(m) is False:
                reason = "not a Nightshift route; never a candidate"
            elif m.tier == "open_source" and m.tier in chosen and "required" in chosen[m.tier][1]:
                reason = "the open-source tier is fixed to the required Nemotron route"
            elif m.tier in CANDIDATE_TIERS:
                reason = f"ranked below {chosen[m.tier][0].model_id}" if m.tier in chosen else "not eligible"
            else:
                reason = "no candidate tier"
            shortlist.append(ShortlistEntry(model_id=m.model_id, tier=m.tier, nightshift_route=is_route(m),
                                            intelligence=m.intelligence, market=m.market,
                                            price_per_intelligence_point_usd=ppp, price_per_intelligence_point_label=ppp_label,
                                            selected=m.model_id in selected, reason=reason))
        if routes is None:
            self.limitations.append("Candidate routes are checked against Nightshift only in live mode.")
        self.trace.event("Controller", "select_candidates", execution_kind="rule_policy",
                         output_summary="; ".join(f"{t}: {m.model_id}" for t, (m, _) in chosen.items())
                                        + f" ({len(models)} snapshot models shortlisted)")
        return [chosen[t][0] for t in CANDIDATE_TIERS if t in chosen], shortlist

    def _check_critic_route(self, candidates: list[ModelProfile], route_list: list[str]):
        """The Critic must not use a candidate's route when Nightshift offers another; otherwise the trace says so.
        Checked before any paid call. GET /v1/models is free."""
        if self.mode == "sample":
            self.trace.event("Controller", "critic_route_check", execution_kind="rule_policy",
                             output_summary="sample mode: no Critic call")
            return
        cand = {m.model_id for m in candidates}
        routes = route_list
        others = [r for r in routes if r not in cand and r != AUTO_ROUTE]
        if self.critic_model and self.critic_model not in cand and self.critic_model != AUTO_ROUTE:
            if routes and self.critic_model not in routes:
                raise StopRun(RunState.needs_input, f"Critic route {self.critic_model} is not offered by Nightshift",
                              [f"Set METERLESS_CRITIC_MODEL to one of: {', '.join(others) or 'no non-candidate route available'}."])
            self.trace.event("Controller", "critic_route_check", requested_model=self.critic_model,
                             output_summary="Critic route is not a candidate route")
            self.limitations.append("Critic independence is checked by route, not by lab; a different route from the "
                                    "same lab as a candidate is not detected.")
            return
        if others:
            raise StopRun(RunState.needs_input,
                          "Critic route is unset, the router alias, or a candidate's route, while Nightshift offers others",
                          [f"Set METERLESS_CRITIC_MODEL to a route that is not a candidate: {', '.join(others)}."])
        self.critic_model = self.critic_model if self.critic_model in cand else candidates[0].model_id
        self.trace.event("Controller", "critic_shares_candidate_route", requested_model=self.critic_model,
                         output_summary="Nightshift offers no non-candidate route; the Critic shares a candidate's route")
        self.limitations.append(f"The Critic uses candidate route {self.critic_model}; Nightshift offered no other route. "
                                "Its flags are not independent of that candidate.")

    # ---------------------------------------------------------- build panel

    @staticmethod
    def _pricing_verified(a) -> bool:
        return bool(a.rates) and all(r.status == EvidenceStatus.verified and r.usd_per_unit is not None for r in a.rates)

    def _build_panel(self, brief, approaches, ledgers) -> BuildPanel:
        """General ranking rule: DevOps fit filters; then verified pricing whose base build cost fits the cash
        budget, then other verified pricing, then pricing-snapshot order. Unverified pricing never outranks verified.
        A missing input that decides eligibility leaves the ranking empty and asks; it never stops the run."""
        c = brief.constraints
        by_cap = {cap: [a.approach_id for a in approaches if self._devops_ok(a.requires_devops, cap)]
                  for cap in ("none", "basic", "full")}
        panel = BuildPanel(eligible_by_devops_capacity=by_cap)
        devops_status = self._constraint_status(c, "devops_capacity")
        if devops_status in (EvidenceStatus.assumed, EvidenceStatus.unknown) and len({tuple(v) for v in by_cap.values()}) > 1:
            panel.reasons.append(f"devops_capacity is {devops_status.value}, and it decides which approaches are eligible; "
                                 "no build ranking until it is stated.")
            panel.questions.append("Build panel: what DevOps work can the founder take on? " +
                                   "; ".join(f"{cap}: {len(ids)} eligible ({', '.join(ids) or 'none'})" for cap, ids in by_cap.items()) + ".")
            return panel
        eligible = [a for a in approaches if self._devops_ok(a.requires_devops, c.devops_capacity)]
        if not eligible:
            panel.reasons.append("No approach fits the founder's DevOps capacity.")
            panel.questions.append("Build panel: can the founder take on basic DevOps, or should only managed platforms be considered?")
            return panel

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
        panel.ranked_approach_ids = [a.approach_id for a in ranked]
        panel.reasons += [
            f"Ranking: {len(eligible)} of {len(approaches)} approaches fit devops_capacity={c.devops_capacity}; ordered by "
            "verified pricing within the cash budget, then other verified pricing, then pricing-snapshot order.",
            "; ".join(f"{a.approach_id}: {tier(a)[1]}" for a in ranked[:2]) + ".",
        ]
        if not any(self._pricing_verified(a) for a in eligible):
            panel.reasons.append("No eligible approach has verified pricing, so the order between them reflects the "
                                 "snapshot order, not cost.")
            panel.questions.append("Build panel: no eligible approach has verified pricing (" + ", ".join(a.approach_id for a in eligible) +
                                   "). Verified, dated rates for these approaches would change the ranking.")
        elif self._constraint_status(c, "cash_budget_usd") in (EvidenceStatus.assumed, EvidenceStatus.unknown):
            panel.questions.append("Build panel: the cash budget is not stated. Stating it decides which verified "
                                   "approaches fit and could change the ranking.")
        return panel

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
                risks.append(Risk(description=f"Constraint {name} is {st.value}; build-panel results that depend on it may change once stated.",
                                  cause_class=RiskCause.requirements_gap,
                                  severity="high" if name in ("devops_capacity", "cash_budget_usd") else "medium",
                                  triggered_by=[f"constraints.{name}"]))
        return risks

    # ---------------------------------------------------------- Planner: domain risks

    def _domain_risks(self, brief, budget: Budget) -> list[Risk]:
        """Domain risks come only from the live Planner, labeled model-generated and not advice. Never hard-coded."""
        if self.mode == "sample":
            self.gaps.append(EvidenceGap(field="domain_risks", status=EvidenceStatus.unknown,
                                         note="domain risk review requires live mode"))
            self.limitations.append("Domain risk review requires live mode.")
            self.trace.event("Planner", "domain_risk_review", execution_kind="rule_policy",
                             output_summary="domain risk review requires live mode")
            return []
        budget.reserve_role("Planner")
        budget.reserve_spend(DEFAULT_RESERVATION)
        ids = [f.feature_id for f in brief.ai_features]
        user = json.dumps({"idea": brief.product_concept, "target_user": brief.target_user,
                           "features": [{"feature_id": f.feature_id, "description": f.description, "mode": f.mode,
                                         "modality": f.modality} for f in brief.ai_features]})
        system = ("You review a SaaS idea for domain risks: privacy, regulatory, safety, consent, licensing. Name only "
                  "risks the idea itself raises. Do not give legal, medical or financial advice. Return JSON: "
                  '{"domain_risks": [{"description": str, "severity": "low"|"medium"|"high", "feature_ids": [str]}]}')
        res = self._call("Planner", self.planner_model or self.critic_model, system, user, budget)
        obj = parse_json_object(res["text"])
        risks: list[Risk] = []
        if obj is None or not isinstance(obj.get("domain_risks"), list):
            self.limitations.append("Planner returned no valid domain-risk JSON; no domain risks are reported.")
        else:
            for item in obj["domain_risks"][:MAX_DOMAIN_RISKS]:
                if not isinstance(item, dict) or not isinstance(item.get("description"), str) or not item["description"].strip():
                    continue
                sev = item.get("severity") if item.get("severity") in ("low", "medium", "high") else "medium"
                fids = [x for x in item.get("feature_ids", []) if x in ids] if isinstance(item.get("feature_ids"), list) else []
                risks.append(Risk(description=f"{item['description'].strip()} ({NOT_ADVICE})", cause_class=RiskCause.domain,
                                  severity=sev, origin="model_generated",
                                  triggered_by=[f"ai_features:{x}" for x in fids] or ["brief.product_concept"]))
        self.trace.event("Planner", "domain_risk_review", model=res["resolved_model"], requested_model=res["requested_model"],
                         route_id=res.get("route_id"), execution_kind=res["execution_kind"],
                         output_summary=f"{len(risks)} model-generated domain risks")
        return risks

    # ---------------------------------------------------------- sampling

    @staticmethod
    def _not_executable(f: FeatureProfile) -> Optional[str]:
        return AUDIO_NOT_EXECUTABLE if {"audio_in", "audio_out"} & set(f.modality) else None

    @staticmethod
    def _prompt(f: FeatureProfile) -> str:
        fields = json_fields_requested(f)
        parts = [f"You are the AI feature '{f.description}' in a product. Respond to the user's input as that feature would."]
        if fields:
            parts.append("Respond with one JSON object containing the fields: " + ", ".join(fields) + ".")
        if f.rubric_checks:
            parts.append("Requirements: " + "; ".join(c.description for c in f.rubric_checks) + ".")
        return " ".join(parts)

    @staticmethod
    def _rates(m: ModelProfile):
        r = {x.category: x.usd_per_unit for x in m.rates}
        return r.get(RateCategory.input_tokens), r.get(RateCategory.output_tokens)

    def _reservation(self, m: ModelProfile, est: Optional[TokenUsage]) -> Decimal:
        p_in, p_out = self._rates(m)
        if est is None or p_in is None or p_out is None:
            return DEFAULT_RESERVATION
        return cost_per_call(est, p_in, p_out) * RESERVATION_HEADROOM

    def _execute(self, f: FeatureProfile, m: ModelProfile, est, budget: Budget, ref: str,
                 max_tokens: Optional[int] = None) -> FeatureSample:
        reserved = self._reservation(m, est)
        budget.reserve_generation(reserved)
        res = self._call("Analyst", m.model_id, self._prompt(f), f.example_input, budget, max_tokens=max_tokens)
        usage, why = _measured_usage(res.get("usage") or {})
        p_in, p_out = self._rates(m)
        budget.reconcile(reserved, None if usage is None or p_in is None or p_out is None else cost_per_call(usage, p_in, p_out))
        if why:
            self.limitations.append(f"{f.feature_id} on {m.model_id}: {why}; its cost uses the estimate.")
        s = FeatureSample(output_ref=ref, output_text=res["text"], usage=usage, raw_usage=res.get("usage") or {},
                          latency_s=res.get("elapsed_s"), requested_model=res.get("requested_model"),
                          resolved_model=res.get("resolved_model"), route_id=res.get("route_id"), max_tokens=max_tokens)
        self.trace.event("Analyst", "run_feature", model=res.get("resolved_model"), requested_model=res.get("requested_model"),
                         route_id=res.get("route_id"), execution_kind=res["execution_kind"], input_summary=ref,
                         output_summary="usage unavailable" if usage is None else
                         f"measured {usage.input_tokens} in / {usage.output_tokens} out"
                         + ("" if usage.reasoning_tokens is None else f" (incl. {usage.reasoning_tokens} reasoning)"))
        try:
            self.data.write_evidence({"id": ref, "feature_id": f.feature_id, "model_id": m.model_id, **s.model_dump(mode="json")})
        except NotImplementedError:
            self.limitations.append("Evidence writeback to the data layer is not wired yet; runs are kept in the pack only.")
        return s

    def _finish_run(self, run: FeatureRun, f: FeatureProfile, samples: list[FeatureSample], req: RunRequest):
        run.executed, run.samples, run.not_executed_reason = True, samples, None
        usages = [s.usage for s in samples]
        if all(u is not None for u in usages):
            run.measured_mean = _mean_usage(usages)
            if run.estimated is not None and run.estimated.output_tokens:
                run.output_gap_ratio = (run.measured_mean.output_tokens / run.estimated.output_tokens).quantize(Decimal("0.01"))
        run.rubric = evaluate(f, run.model_id, [s.output_text for s in samples], req.human_reviews)

    def _sample(self, brief, candidates, runs, budget: Budget, req: RunRequest):
        """Run each executable feature's example input on each candidate. Sample mode executes nothing."""
        features = {f.feature_id: f for f in brief.ai_features}
        executable = [k for k in runs if self._not_executable(features[k[0]]) is None]
        if self.mode == "sample":
            self.trace.event("Analyst", "run_feature", execution_kind="rule_policy",
                             output_summary=f"sample mode: {len(executable)} feature × candidate pairs not executed; "
                                            "no outputs produced; rubric checks not run")
            return
        n = SAMPLES_PER_PAIR if len(executable) * SAMPLES_PER_PAIR + 1 <= MAX_CANDIDATE_GENERATIONS else 1
        if n < SAMPLES_PER_PAIR:
            self.limitations.append(f"{len(executable)} feature × candidate pairs: one sample each to fit the generation cap.")
        by_id = {m.model_id: m for m in candidates}
        for key in executable:
            f, m, run = features[key[0]], by_id[key[1]], runs[key]
            samples = [self._execute(f, m, run.estimated, budget, f"{self.run_id}/{f.feature_id}/{m.model_id}/s{i + 1}")
                       for i in range(n)]
            self._finish_run(run, f, samples, req)

    # ---------------------------------------------------------- Critic

    def _critique(self, brief, runs, budget: Budget) -> tuple[Critique, Optional[tuple[str, str, int]]]:
        """The Critic flags; it never passes or fails an output. Returns the critique and a validated repair target."""
        executed = [r for r in runs.values() if r.executed]
        if self.mode == "sample" or not executed:
            why = "sample mode: no outputs to flag" if self.mode == "sample" else "no executed outputs to flag"
            self.trace.event("Critic", "critique", execution_kind="rule_policy", output_summary=why)
            return Critique(case_ids=[], findings=[], expected_check="none", execution_kind="rule_policy",
                            controller_decision="no_change",
                            proposed_action=ActionProposal(action=ActionType.finalize, concise_reason=why,
                                                           expected_observation="none", proposed_by="rule_policy")), None
        budget.reserve_spend(DEFAULT_RESERVATION)
        features = {f.feature_id: f for f in brief.ai_features}
        payload = [{"feature_id": r.feature_id, "model_id": r.model_id,
                    "rubric": [c.description for c in features[r.feature_id].rubric_checks],
                    "estimated_output_tokens": None if r.estimated is None else str(r.estimated.output_tokens),
                    "measured_output_tokens": None if r.measured_mean is None else str(r.measured_mean.output_tokens),
                    "output_excerpt": r.samples[0].output_text[:1200]} for r in executed]
        system = ("You review outputs of AI features. Only FLAG issues; never pass, fail or score an output. Finding kinds: "
                  "unsupported_claim (a claim not supported by the input), token_gap (estimated vs measured tokens differ "
                  "materially), output_too_long (longer than the requirements need). Propose at most one corrective action: "
                  '{"action": "apply_output_cap", "feature_id": str, "model_id": str, "max_output_tokens": int} or '
                  '{"action": "move_to_cacheable_prefix", "feature_id": str}. Return JSON: {"findings": [{"kind": str, '
                  '"feature_id": str, "model_id": str, "claim": str, "severity": "low"|"medium"|"high"}], '
                  '"proposed_action": object or null}')
        res = self._call("Critic", self.critic_model, system, json.dumps(payload), budget)
        obj = parse_json_object(res["text"]) or {}
        if not obj:
            self.limitations.append("Critic returned no valid JSON; no findings recorded.")
        dropped = sorted(VERDICT_KEYS & set(obj))
        findings: list[CritiqueFinding] = []
        known = set(runs)
        for item in obj.get("findings", []) if isinstance(obj.get("findings"), list) else []:
            if not isinstance(item, dict):
                continue
            dropped += sorted(VERDICT_KEYS & set(item))
            if item.get("kind") not in CRITIC_FINDING_KINDS or (item.get("feature_id"), item.get("model_id")) not in known:
                continue
            findings.append(CritiqueFinding(claim=str(item.get("claim", ""))[:500], kind=item["kind"],
                                            feature_id=item["feature_id"], model_id=item["model_id"],
                                            severity=item.get("severity") if item.get("severity") in ("low", "medium", "high") else "medium",
                                            supporting_or_missing_source_ids=[f"{self.run_id}/{item['feature_id']}/{item['model_id']}"]))
        if dropped:
            self.trace.event("Controller", "critic_verdict_ignored", output_summary=f"dropped verdict fields: {', '.join(dropped)}")
        proposal, decision, target, why = self._validate_critic_action(obj.get("proposed_action"), findings, runs)
        crit = Critique(case_ids=[f"{self.run_id}/{r.feature_id}/{r.model_id}" for r in executed], findings=findings,
                        proposed_action=proposal, expected_check="one measured re-run of the affected feature and model",
                        requested_model=res["requested_model"], resolved_model=res["resolved_model"],
                        execution_kind=res["execution_kind"], controller_decision=decision)
        self.trace.event("Critic", "critique", target_agent="Controller", model=res["resolved_model"],
                         requested_model=res["requested_model"], route_id=res.get("route_id"), execution_kind=res["execution_kind"],
                         output_summary=f"{len(findings)} flags; proposed {proposal.action.value}; controller {decision}: {why}")
        return crit, target

    def _validate_critic_action(self, a, findings, runs):
        """Only an output cap on a measured, flagged feature × model is executable. A prefix move is recorded."""
        def prop(action, inputs, reason):
            return self._validate(ActionProposal(action=action, inputs=inputs, concise_reason=reason,
                                                 expected_observation="measured output tokens fall and critical checks still pass",
                                                 proposed_by="Critic"))
        if not isinstance(a, dict) or not a.get("action"):
            return prop(ActionType.finalize, {}, "no action proposed"), "no_change", None, "no action proposed"
        inputs = {k: v for k, v in a.items() if k != "action" and k not in VERDICT_KEYS}
        if a["action"] == ActionType.move_to_cacheable_prefix.value:
            ok = any(k[0] == a.get("feature_id") for k in runs)
            why = ("recorded as a recommendation; a prefix move is not executable as a measured re-run" if ok
                   else "unknown feature_id")
            if ok:
                self.questions.append(f"Critic recommendation (not executed): move static instructions for "
                                      f"{a['feature_id']} into a cacheable prefix.")
            return prop(ActionType.move_to_cacheable_prefix, inputs, why), "no_change" if ok else "rejected", None, why
        if a["action"] != ActionType.apply_output_cap.value:
            return prop(ActionType.finalize, {}, "unsupported action"), "rejected", None, f"unsupported action {a['action']!r}"
        key, cap = (a.get("feature_id"), a.get("model_id")), a.get("max_output_tokens")
        run = runs.get(key)
        flagged = any(f.kind == "output_too_long" and (f.feature_id, f.model_id) == key for f in findings)
        if run is None or run.measured_mean is None:
            why = "target was not executed with measured usage"
        elif not flagged:
            why = "no output_too_long flag for the target"
        elif not isinstance(cap, int) or isinstance(cap, bool) or not 0 < cap < run.measured_mean.output_tokens:
            why = "max_output_tokens must be a positive integer below the measured output"
        else:
            return prop(ActionType.apply_output_cap, inputs, "output longer than the rubric needs"), "accepted", (key[0], key[1], cap), "validated"
        return prop(ActionType.apply_output_cap, inputs, why), "rejected", None, why

    # ---------------------------------------------------------- repair

    def _repair(self, brief, candidates, runs, target, budget: Budget, req: RunRequest):
        fid, mid, cap = target
        f = next(x for x in brief.ai_features if x.feature_id == fid)
        m = next(x for x in candidates if x.model_id == mid)
        original = runs[(fid, mid)]
        rev = Revision(revision_id=str(uuid.uuid4())[:8], config_id=f"{fid}/{mid}", from_version=1, to_version=2,
                       change={"max_tokens": cap}, justified_by_critique=True)
        self.trace.event("Controller", "repair", output_summary=f"re-run {fid} on {mid} once with max_tokens={cap}")
        sample = self._execute(f, m, original.estimated, budget, f"{self.run_id}/{fid}/{mid}/repair", max_tokens=cap)
        rerun = FeatureRun(feature_id=fid, model_id=mid, tier=m.tier, executed=False, estimated=original.estimated, is_repair=True)
        self._finish_run(rerun, f, [sample], req)
        criticals = [c.check_id for c in f.rubric_checks if c.critical]
        broke = [c for c in criticals if original.rubric and original.rubric.checks.get(c) and not rerun.rubric.checks.get(c)]
        if rerun.measured_mean is None:
            self.limitations.append(f"Output-cap re-run of {fid} on {mid} has no measured usage; the cap is not applied.")
        elif broke:
            self.limitations.append(f"Output-cap re-run of {fid} on {mid} failed critical checks {', '.join(broke)}; "
                                    "the cap is not applied.")
        else:
            self.output_caps.append(OutputCapRerun(feature_id=fid, model_id=mid, critic_flagged=True, rerun=rerun.measured_mean))
        return rev, rerun

    # ---------------------------------------------------------- projection

    def _project(self, pack: DecisionPack, brief, candidates, runs):
        live_executed = self.mode == "live" and any(r.executed for r in runs.values())
        for f in brief.ai_features:
            pair = [runs[(f.feature_id, m.model_id)] for m in candidates]
            tokens = {r.model_id: r.measured_mean for r in pair if r.measured_mean is not None}
            rubric = [r.rubric for r in pair if r.rubric is not None]
            table = stage_cost_table(f, candidates, tokens, brief.growth_stages, rubric, output_caps=self.output_caps)
            pack.stage_tables.append(table)
            pack.risks += table.risks
            if live_executed:   # features that could not run (audio) are reported as "no candidate passes", with why
                pack.model_stack += recommend_model_stack(f, table, candidates, rubric)
            else:
                why = ("requires live run: sample mode does not execute features or run rubric checks" if self.mode == "sample"
                       else "requires live run: no feature was executed in this run")
                pack.model_stack += [ModelStackEntry(feature_id=f.feature_id, stage=s.name, status="requires_live_run", reason=why)
                                     for s in table.stages]
        self.trace.event("Analyst", "calculate_cost", execution_kind="rule_policy",
                         output_summary=f"{len(pack.stage_tables)} stage cost tables; "
                                        f"{sum(len(t.switch_points) for t in pack.stage_tables)} switch points, "
                                        f"{sum(len(t.pending_switch_points) for t in pack.stage_tables)} pending")
