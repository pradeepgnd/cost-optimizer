"""Typed contracts shared by UI, CLI, controller, tools and report builder.

Every record that crosses a boundary is defined here. Model text never becomes
code or SQL; it becomes one of these structures, validated by the controller.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


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


class ModelProfile(BaseModel):
    model_id: str                    # as exposed by Nightshift GET /v1/models
    provider_label: str              # e.g. "nvidia" — informational
    tier: Optional[Literal["frontier", "mid_tier", "open_source"]] = None
    rates: list[Rate]
    terms: ModelPricingTerms = Field(default_factory=ModelPricingTerms)
    source: SourceRef


# ------------------------------------------------- AI features and stages (07 §2, §5.1)

class RubricCheck(BaseModel):
    check_id: str
    description: str
    critical: bool = True            # a cheaper model must pass every critical check to qualify a switch point


class FeatureProfile(BaseModel):
    """One AI feature of the founder's SaaS idea. Volume fields are the founder's estimate."""
    feature_id: str
    description: str
    example_input: str
    mode: Literal["interactive", "background"]
    uses_per_user_month: Optional[Decimal] = None
    calls_per_use: Decimal = Decimal("1")
    static_prefix_tokens: int = 0    # instructions repeated on every call; part of the input
    expected_output_words: Optional[int] = None   # used only to estimate output tokens offline
    rubric_checks: list[RubricCheck] = Field(default_factory=list)
    field_status: dict[str, EvidenceStatus] = Field(default_factory=dict)


class Stage(BaseModel):
    name: str
    active_users: int
    status: EvidenceStatus = EvidenceStatus.assumed


def default_stages() -> list[Stage]:
    """Editable defaults (07 §5.1), labeled assumed."""
    return [Stage(name="Prototype", active_users=50), Stage(name="Launch", active_users=500),
            Stage(name="Traction", active_users=5000), Stage(name="Scale", active_users=50000)]


class TokenUsage(BaseModel):
    """Per-call tokens. measured == from API usage fields only; estimated == 4/3 rule on words."""
    input_tokens: int
    output_tokens: int
    reasoning_tokens: Optional[int] = None   # None == unknown; never coerced to zero
    basis: Literal["measured", "estimated"]
    method: str


class RubricResult(BaseModel):
    feature_id: str
    model_id: str
    checks: dict[str, bool]
    execution_kind: Literal["live_inference", "rule_policy"]


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


class CaseResult(BaseModel):
    task_id: str
    config_id: str
    config_version: int
    output_ref: str
    elements_present: dict[str, bool]
    critical_failures_hit: list[str]
    cost_note_sourced: bool
    usage: dict = Field(default_factory=dict)
    elapsed_s: Optional[float] = None
    requested_model: Optional[str] = None
    resolved_model: Optional[str] = None
    execution_kind: Literal["live_inference", "rule_policy"]
    human_review: Optional[Literal["confirmed", "rejected", "pending"]] = "pending"


class CritiqueFinding(BaseModel):
    claim: str
    supporting_or_missing_source_ids: list[str]
    severity: Literal["low", "medium", "high"]
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
    name: Literal["input", "output", "reasoning", "retries"]
    monthly_usd: Optional[Decimal]
    note: str = ""


class LeverLine(BaseModel):
    """Shown separately from the gross cost, never silently netted."""
    lever: Literal["prompt_caching", "batch_api", "output_cap", "long_context_cliff"]
    applies: bool
    reason: str
    monthly_delta_usd: Optional[Decimal] = None   # negative == saving, positive == surcharge


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
    lower_bound: bool = False        # True when an unknown component (e.g. reasoning tokens) is excluded
    rate_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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
    warnings: list[str] = Field(default_factory=list)


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


class Risk(BaseModel):
    """Raised from general signals in the inputs (rates, brief, assumptions), never from a known case outcome."""
    description: str
    cause_class: RiskCause
    severity: Literal["low", "medium", "high"]
    triggered_by: list[str]          # evidence record IDs or brief field paths


class DecisionPack(BaseModel):
    run_id: str
    project_id: str
    execution_mode: Literal["live", "sample"]
    status: RunState
    recommended_config: Optional[CandidateConfig] = None
    alternate_config: Optional[CandidateConfig] = None
    reasons: list[str] = Field(default_factory=list)
    build_ledgers: list[BuildLedger] = Field(default_factory=list)
    operating_ledger: Optional[OperatingLedger] = None
    development_results: list[CaseResult] = Field(default_factory=list)
    holdout_results: list[CaseResult] = Field(default_factory=list)
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
