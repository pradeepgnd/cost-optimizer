"""Typed contracts shared by UI, CLI, controller, tools and report builder.

Every record that crosses a boundary is defined here. Model text never becomes
code or SQL; it becomes one of these structures, validated by the controller.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr, model_validator


# ---------------------------------------------------------------- provenance

class EvidenceStatus(str, Enum):
    verified = "verified"            # dated artifact or cited published rate
    reconstructed = "reconstructed"  # founder recollection, dated to the pre-build period
    assumed = "assumed"              # editable default, no project-specific evidence
    unknown = "unknown"              # not available; never coerced to zero
    unverified = "unverified"        # claimed by a platform/model but not independently confirmed


class SourceRef(BaseModel):
    source_set: str                  # founder_briefs | pricing_snapshots | dev_task_cases | evaluation_evidence | retrospective_actuals
    record_id: str
    version: str
    origin_url: Optional[str] = None
    verified_at: Optional[str] = None
    status: EvidenceStatus = EvidenceStatus.verified


# -------------------------------------------------------------- founder brief

class BuildConstraints(BaseModel):
    cash_budget_usd: Optional[Decimal] = None
    time_budget_weeks: Optional[Decimal] = None
    team_size: int = 1
    technical_skill: Literal["none", "scripting", "professional"] = "scripting"
    devops_capacity: Literal["none", "basic", "full"] = "none"
    status: EvidenceStatus = EvidenceStatus.reconstructed


class FeatureItem(BaseModel):
    feature_id: str
    title: str
    size_class: Literal["S", "M", "L", "XL"]
    compute_heavy: bool = False


class UsageAssumptions(BaseModel):
    active_users: Optional[int] = None
    workflows_per_user_month: Optional[Decimal] = None
    calls_per_workflow: Optional[Decimal] = None
    paying_fraction: Optional[Decimal] = None
    subscription_price_usd: Optional[Decimal] = None
    status: EvidenceStatus = EvidenceStatus.unknown


class FounderBrief(BaseModel):
    brief_id: str
    brief_version: str
    product_concept: str
    target_user: str
    features_v1: list[FeatureItem]
    constraints: BuildConstraints
    quality_needs: list[str] = Field(default_factory=list)
    alternatives_considered: list[str] = Field(default_factory=list)
    usage: UsageAssumptions = Field(default_factory=UsageAssumptions)
    ai_features: list[FeatureProfile] = Field(default_factory=list)          # 07 §2; not yet read by the controller
    growth_stages: list[Stage] = Field(default_factory=lambda: default_stages())
    field_status: dict[str, EvidenceStatus] = Field(default_factory=dict)
    source: Optional[SourceRef] = None


# --------------------------------------------------------- pricing snapshots

class RateCategory(str, Enum):
    input_tokens = "input_tokens"
    output_tokens = "output_tokens"
    cached_input_tokens = "cached_input_tokens"
    reasoning_tokens = "reasoning_tokens"
    cache_write_tokens = "cache_write_tokens"                 # cached_input_tokens is the cache-read rate
    long_context_input_tokens = "long_context_input_tokens"   # whole-request rate above the threshold
    long_context_output_tokens = "long_context_output_tokens"
    audio_input_tokens = "audio_input_tokens"
    audio_output_tokens = "audio_output_tokens"
    credits = "credits"
    seat_month = "seat_month"
    hosting_month = "hosting_month"


class Rate(BaseModel):
    category: RateCategory
    unit: str                        # "1M tokens" | "credit" | "seat/month" | "month"
    usd_per_unit: Optional[Decimal]  # None == unknown, and stays unknown
    status: EvidenceStatus
    source: SourceRef


class ApproachProfile(BaseModel):
    """A development approach the founder could commit to (e.g. app-builder, IDE agent + own hosting, API-only)."""
    approach_id: str
    name: str
    rates: list[Rate]
    credits_per_task_class: Optional[dict[str, Decimal]] = None  # S/M/L/XL -> credits, when the platform bills in credits
    tokens_per_task_class: Optional[dict[str, Decimal]] = None   # S/M/L/XL -> tokens (in+out), when billed by token
    requires_devops: Literal["none", "basic", "full"] = "none"
    notes: list[str] = Field(default_factory=list)
    source: SourceRef


class ModelPricingTerms(BaseModel):
    """Provider terms that decide lever eligibility (07 §5.1). None == unknown, so the lever is not applied."""
    cache_min_prefix_tokens: Optional[int] = None
    cache_ttl_minutes: Optional[Decimal] = None
    batch_available: Optional[bool] = None
    batch_discount: Optional[Decimal] = None          # 0.5 == 50% off input and output
    long_context_threshold_tokens: Optional[int] = None
    status: EvidenceStatus = EvidenceStatus.unknown


class AudioConversion(BaseModel):
    """Seconds of audio to billed audio tokens. Always an estimate until measured from API usage fields."""
    input_tokens_per_second: Optional[Decimal] = None
    output_tokens_per_second: Optional[Decimal] = None
    basis: Literal["estimated"] = "estimated"
    status: EvidenceStatus = EvidenceStatus.unverified
    source: Optional[SourceRef] = None


class ModelProfile(BaseModel):
    model_id: str                    # as exposed by Nightshift GET /v1/models
    provider_label: str              # e.g. "nvidia" — informational
    tier: Optional[Literal["frontier", "mid_tier", "open_source"]] = None
    rates: list[Rate]
    terms: ModelPricingTerms = Field(default_factory=ModelPricingTerms)
    audio: Optional[AudioConversion] = None   # None == audio not priced for this model; stays unknown
    source: SourceRef


# ------------------------------------------------- AI features and stages (07 §2, §5.1)

CheckKind = Literal["max_words", "required_json_fields", "forbidden_terms", "regex", "human_review"]


class RubricCheck(BaseModel):
    """A deterministic check on a model output; these and human review decide pass/fail, never a model.

    params by kind (json_field optional for all but required_json_fields: check one field of a JSON output):
      max_words            {"limit": int}
      required_json_fields {"fields": [str, ...]}
      forbidden_terms      {"terms": [str, ...]}           case-insensitive substring match
      regex                {"pattern": str, "must_match": bool = true, "ignore_case": bool = false}
      human_review         {}  no machine result; pending until a reviewer records one
    """
    check_id: str
    description: str
    kind: CheckKind = "human_review"
    params: dict = Field(default_factory=dict)
    critical: bool = True            # a cheaper model must pass every critical check to qualify a switch point

    @model_validator(mode="after")
    def _params_match_kind(self):
        p = self.params
        ok = {
            "max_words": lambda: isinstance(p.get("limit"), int) and p["limit"] > 0,
            "required_json_fields": lambda: isinstance(p.get("fields"), list) and p["fields"]
                                            and all(isinstance(f, str) for f in p["fields"]),
            "forbidden_terms": lambda: isinstance(p.get("terms"), list) and p["terms"]
                                       and all(isinstance(t, str) and t for t in p["terms"]),
            "regex": lambda: isinstance(p.get("pattern"), str) and bool(p["pattern"]),
            "human_review": lambda: True,
        }[self.kind]()
        if not ok:
            raise ValueError(f"rubric check {self.check_id}: params {p} do not fit kind {self.kind}")
        if self.kind == "regex":
            import re
            try:
                re.compile(p["pattern"])
            except re.error as e:
                raise ValueError(f"rubric check {self.check_id}: invalid regex: {e}") from None
        return self


class HumanReview(BaseModel):
    """A reviewer's result for one check on one feature × model; it overrides the machine result."""
    feature_id: str
    model_id: str
    check_id: str
    passed: bool
    reviewer: str
    note: str = ""


class FeatureProfile(BaseModel):
    """One AI feature of the founder's SaaS idea. Volume fields are the founder's estimate."""
    feature_id: str
    description: str
    example_input: str
    mode: Literal["interactive", "background"]
    modality: list[Literal["text", "audio_in", "audio_out"]] = Field(default_factory=lambda: ["text"])
    audio_seconds_per_use: Optional[Decimal] = None   # applied to each audio direction in modality
    revenue_per_use: Optional[Decimal] = None          # present -> AI cost per use as a share of revenue per use
    uses_per_user_month: Optional[Decimal] = None
    calls_per_use: Decimal = Decimal("1")
    static_prefix_tokens: int = 0    # instructions repeated on every call; part of the input
    expected_output_words: Optional[int] = None   # used only to estimate output tokens offline
    # Share of uses served from a cache of previously generated outputs (e.g. the same sentence spoken again);
    # a production-setup projection, not measured. distinct_outputs sizes the one-time cache fill.
    output_reuse_rate: Optional[Decimal] = None
    distinct_outputs: Optional[int] = None
    rubric_checks: list[RubricCheck] = Field(default_factory=list)
    field_status: dict[str, EvidenceStatus] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _reuse_in_range(self):
        if self.output_reuse_rate is not None and not Decimal("0") <= self.output_reuse_rate <= Decimal("1"):
            raise ValueError(f"{self.feature_id}: output_reuse_rate must be between 0 and 1")
        if self.distinct_outputs is not None and self.distinct_outputs <= 0:
            raise ValueError(f"{self.feature_id}: distinct_outputs must be positive")
        return self


class Stage(BaseModel):
    name: str
    active_users: int
    status: EvidenceStatus = EvidenceStatus.assumed


def default_stages() -> list[Stage]:
    """Editable defaults (07 §5.1), labeled assumed."""
    return [Stage(name="Prototype", active_users=50), Stage(name="Launch", active_users=500),
            Stage(name="Traction", active_users=5000), Stage(name="Scale", active_users=50000)]


class TokenUsage(BaseModel):
    """Per-call tokens. measured == from API usage fields only; estimated == 4/3 rule on words.
    output_tokens is the completion count and already INCLUDES reasoning_tokens (OpenAI-compatible usage).
    Decimal so a mean over samples is kept exactly."""
    input_tokens: Decimal
    output_tokens: Decimal
    reasoning_tokens: Optional[Decimal] = None   # breakdown of output_tokens; None == unknown, never coerced to zero
    audio_input_tokens: Optional[Decimal] = None    # measured only; None -> estimated from seconds if the feature has audio
    audio_output_tokens: Optional[Decimal] = None
    basis: Literal["measured", "estimated"]
    method: str

    @model_validator(mode="after")
    def _reasoning_within_output(self):
        if self.reasoning_tokens is not None and self.reasoning_tokens > self.output_tokens:
            raise ValueError("reasoning_tokens is part of output_tokens and cannot exceed it")
        return self


class RubricResult(BaseModel):
    """checks holds the effective result per check that has one (human override, else machine result);
    a check without either is listed in pending and is absent from checks."""
    feature_id: str
    model_id: str
    checks: dict[str, bool]
    execution_kind: Literal["live_inference", "rule_policy"]
    machine: dict[str, bool] = Field(default_factory=dict)
    overrides: dict[str, bool] = Field(default_factory=dict)
    pending: list[str] = Field(default_factory=list)


class FeatureSample(BaseModel):
    """One executed call of a feature's example input on one candidate."""
    output_ref: str
    output_text: str
    usage: Optional[TokenUsage] = None       # None when the response carried no usable usage fields
    raw_usage: dict = Field(default_factory=dict)
    latency_s: Optional[float] = None
    requested_model: Optional[str] = None
    resolved_model: Optional[str] = None
    route_id: Optional[str] = None
    max_tokens: Optional[int] = None


class FeatureRun(BaseModel):
    """Everything known about one feature × candidate: the estimate, measured samples, and the rubric result."""
    feature_id: str
    model_id: str
    tier: Optional[str] = None
    executed: bool
    not_executed_reason: Optional[str] = None
    estimated: Optional[TokenUsage] = None
    samples: list[FeatureSample] = Field(default_factory=list)
    measured_mean: Optional[TokenUsage] = None
    output_gap_ratio: Optional[Decimal] = None   # measured / estimated output tokens; None unless both exist
    rubric: Optional[RubricResult] = None
    is_repair: bool = False


class OutputCapRerun(BaseModel):
    """Critic found output longer than the rubric needs; the capped prompt was re-run and measured."""
    feature_id: str
    model_id: str
    critic_flagged: bool
    rerun: TokenUsage


# ------------------------------------------------------------- task cases

class DevTaskCase(BaseModel):
    task_id: str
    title: str
    prompt: str
    required_elements: list[str]     # deterministic checklist keys
    critical_failures: list[str]     # any present -> critical fail
    split: Literal["development", "holdout"]
    source: SourceRef


# --------------------------------------------------------------- planning

class ActionType(str, Enum):
    retrieve_evidence = "retrieve_evidence"
    calculate_cost = "calculate_cost"
    evaluate_development = "evaluate_development"
    revise_prototype = "revise_prototype"
    ask_founder = "ask_founder"
    apply_output_cap = "apply_output_cap"                   # executable repair: one measured re-run with max_tokens
    move_to_cacheable_prefix = "move_to_cacheable_prefix"   # recorded as a recommendation, not executed
    finalize = "finalize"


class ActionProposal(BaseModel):
    action: ActionType
    inputs: dict = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    concise_reason: str
    expected_observation: str
    proposed_by: Literal["Planner", "Critic", "rule_policy"]


class Observation(BaseModel):
    status: Literal["ok", "missing", "denied_sealed", "error", "needs_input"]
    source_ids: list[str] = Field(default_factory=list)
    version: Optional[str] = None
    result_ref: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class CandidateConfig(BaseModel):
    config_id: str
    approach_id: str
    model_id: str
    workflow_settings: dict = Field(default_factory=dict)
    config_version: int = 1


CritiqueKind = Literal["unsupported_claim", "token_gap", "output_too_long"]


class CritiqueFinding(BaseModel):
    """A flag raised by the Critic. It never passes or fails an output; rubric checks and human review do."""
    claim: str
    supporting_or_missing_source_ids: list[str]
    severity: Literal["low", "medium", "high"]
    kind: Optional[CritiqueKind] = None
    feature_id: Optional[str] = None
    model_id: Optional[str] = None
    task_id: Optional[str] = None


class Critique(BaseModel):
    case_ids: list[str]
    findings: list[CritiqueFinding]
    proposed_action: ActionProposal
    expected_check: str
    requested_model: Optional[str] = None
    resolved_model: Optional[str] = None
    execution_kind: Literal["live_inference", "rule_policy"]
    controller_decision: Optional[Literal["accepted", "rejected", "no_change"]] = None


class Revision(BaseModel):
    revision_id: str
    config_id: str
    from_version: int
    to_version: int
    change: dict
    justified_by_critique: bool


# --------------------------------------------------------------- economics

class Scenario(BaseModel):
    low: Optional[Decimal]
    base: Optional[Decimal]
    high: Optional[Decimal]
    currency: str = "USD"
    unit: str = "USD"               # "USD" or "credits (USD conversion unverified)"
    warnings: list[str] = Field(default_factory=list)


class Checkpoint(BaseModel):
    milestone: str
    cumulative_spend: Scenario
    gate_question: str


class BuildLedger(BaseModel):
    approach_id: str
    base_build_cost: Scenario
    rework_multiplier: Scenario
    expected_build_cost: Scenario
    founder_time_hours: Optional[Decimal] = None
    checkpoints: list[Checkpoint]
    rate_ids: list[str]
    not_executed_disclaimer: str = (
        "Approach-level estimate from verified rates and a bounded task plan. "
        "No build was executed on this platform."
    )


class OperatingLedger(BaseModel):
    monthly_cash_cost: Scenario
    per_workflow_cost: Scenario
    revenue: Optional[Scenario] = None
    contribution: Optional[Scenario] = None
    margin: Optional[Scenario] = None
    rate_ids: list[str]
    cost_only: bool = False


class CostLine(BaseModel):
    name: Literal["input", "output", "reasoning", "audio_input", "audio_output", "retries"]
    monthly_usd: Optional[Decimal]
    billed: bool = True              # False == breakdown only (reasoning is inside output); never added to the bill
    note: str = ""


class LeverLine(BaseModel):
    """Shown separately from the gross cost, never silently netted."""
    lever: Literal["prompt_caching", "batch_api", "output_cap", "long_context_cliff", "output_reuse"]
    applies: bool
    reason: str
    monthly_delta_usd: Optional[Decimal] = None   # negative == saving, positive == surcharge
    one_time_usd: Optional[Decimal] = None        # output_reuse: filling the cache once; never added to a monthly total
    label: Optional[str] = None                   # "projected (production setup)" for caching, batch and output reuse


class StageCostRow(BaseModel):
    feature_id: str
    stage: str
    active_users: int
    model_id: str
    tier: Optional[str] = None
    calls_per_month: Optional[Decimal]
    cost_per_call_usd: Optional[Decimal]
    token_basis: Literal["measured", "estimated"]
    lines: list[CostLine]
    gross_monthly_usd: Optional[Decimal]
    levers: list[LeverLine]
    monthly_with_levers_usd: Optional[Decimal]
    cost_per_use_usd: Optional[Decimal] = None
    revenue_per_use_usd: Optional[Decimal] = None
    revenue_share: Optional[Decimal] = None   # AI cost per use / revenue per use; None when revenue absent
    lower_bound: bool = False        # True when an unknown component (e.g. reasoning tokens) is excluded
    rate_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # Unrounded values for downstream rules (switch points, revenue risk); not serialized.
    _exact_with_levers: Optional[Decimal] = PrivateAttr(default=None)
    _exact_share: Optional[Decimal] = PrivateAttr(default=None)


class SwitchPoint(BaseModel):
    feature_id: str
    stage: str
    active_users: int
    from_model: str
    to_model: str
    to_tier: Optional[str] = None
    monthly_difference_usd: Decimal
    quality_to: Optional[str] = None     # "5/6"
    quality_from: Optional[str] = None
    quality_qualified: bool
    statement: str


class StageCostTable(BaseModel):
    feature_id: str
    stages: list[Stage]
    rows: list[StageCostRow]
    threshold_usd: Decimal
    switch_points: list[SwitchPoint] = Field(default_factory=list)          # cost and quality rule both met
    pending_switch_points: list[SwitchPoint] = Field(default_factory=list)  # cost met, quality not shown
    risks: list[Risk] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ModelStackEntry(BaseModel):
    """Recommended candidate for one feature at one stage, from rubric results and cost only."""
    feature_id: str
    stage: str
    status: Literal["recommended", "no_candidate_passes", "requires_live_run"]
    model_id: Optional[str] = None
    alternate_model_id: Optional[str] = None
    monthly_usd: Optional[Decimal] = None
    reason: str


class BuildPanel(BaseModel):
    """Secondary panel (07 §5.2): build approaches. Missing build inputs add questions; they never stop the run."""
    ranked_approach_ids: list[str] = Field(default_factory=list)   # empty when eligibility depends on a missing input
    eligible_by_devops_capacity: dict[str, list[str]] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


# ----------------------------------------------------------- run envelope

class RunState(str, Enum):
    approved = "approved"
    investigating = "investigating"
    development_check = "development_check"
    repair = "repair"
    frozen = "frozen"
    holdout = "holdout"
    complete = "complete"
    needs_input = "needs_input"
    partial = "partial"
    failed = "failed"


class RunRequest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    run_id: str                       # also the idempotency key
    brief: FounderBrief
    evaluation_approved: bool = False
    max_spend_usd: Decimal = Decimal("0")
    sample_mode: Optional[bool] = None
    human_reviews: list[HumanReview] = Field(default_factory=list)


class EvidenceGap(BaseModel):
    field: str
    status: EvidenceStatus
    note: str


class RiskCause(str, Enum):
    pricing_unverified = "pricing_unverified"
    compute_cost = "compute_cost"
    rework = "rework"
    requirements_gap = "requirements_gap"
    scope_change = "scope_change"
    platform_limitation = "platform_limitation"
    unit_economics = "unit_economics"
    domain = "domain"                # privacy, regulatory, safety: from the live Planner only


class Risk(BaseModel):
    """rule: raised from general signals in the inputs (rates, brief, assumptions), never from a known case outcome.
    model_generated: from the live Planner, labeled as such and not advice. Domain risks are never hard-coded."""
    description: str
    cause_class: RiskCause
    severity: Literal["low", "medium", "high"]
    triggered_by: list[str]          # evidence record IDs or brief field paths
    origin: Literal["rule", "model_generated"] = "rule"


class DecisionPack(BaseModel):
    run_id: str
    project_id: str
    execution_mode: Literal["live", "sample"]
    status: RunState
    reasons: list[str] = Field(default_factory=list)
    model_stack: list[ModelStackEntry] = Field(default_factory=list)
    stage_tables: list[StageCostTable] = Field(default_factory=list)
    feature_runs: list[FeatureRun] = Field(default_factory=list)
    build_panel: BuildPanel = Field(default_factory=BuildPanel)
    build_ledgers: list[BuildLedger] = Field(default_factory=list)
    # v3.4 fields kept only so the shelved compare_retrospective.py still loads old packs; the v4 controller leaves them empty.
    recommended_config: Optional[CandidateConfig] = None
    alternate_config: Optional[CandidateConfig] = None
    operating_ledger: Optional[OperatingLedger] = None
    critiques: list[Critique] = Field(default_factory=list)
    revisions: list[Revision] = Field(default_factory=list)
    evidence_refs: list[SourceRef] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)   # blocking when status == needs_input; otherwise what would change the result
    spend_usd: Decimal = Decimal("0")
    trace_path: Optional[str] = None
    disclaimer: str = (
        "Economics are modeled estimates from entered assumptions and cited rates. "
        "They are not financial advice. See evidence_gaps and limitations."
    )


class RunError(BaseModel):
    run_id: str
    status: Literal["error"] = "error"
    code: str
    message: str
    recoverable: bool
    trace_path: Optional[str] = None


# Resolve forward references to models defined further down this module.
FounderBrief.model_rebuild()
StageCostTable.model_rebuild()
RunRequest.model_rebuild()
