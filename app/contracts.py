"""Typed contracts shared by UI, CLI, controller, tools and report builder.

Every record that crosses a boundary is defined here. Model text never becomes
code or SQL; it becomes one of these structures, validated by the controller.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, StringConstraints, computed_field, model_validator


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
PositiveDecimal = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
Fraction = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]
NonNegativeInt = Annotated[int, Field(ge=0, strict=True)]
PositiveInt = Annotated[int, Field(gt=0, strict=True)]


class PublicInput(BaseModel):
    """Reject misspelled/unsupported founder controls instead of discarding them."""
    model_config = ConfigDict(extra="forbid")


def require_unique(values: list[str], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{label} must be unique")


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
    transport_ref: Optional[str] = None
    query_id: Optional[str] = None
    content_sha256: Optional[str] = None
    snapshot_id: Optional[str] = None


# -------------------------------------------------------------- founder brief

class AssumptionInput(PublicInput):
    """A supplied estimate stays assumed unless evidence was explicitly declared.

    Defaults cannot acquire verified status from metadata alone. Null means
    unknown. Preserve this metadata when serializing/reloading a request.
    """
    field_status: dict[str, EvidenceStatus] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _record_assumptions(self):
        statuses = dict(self.field_status)
        excluded = {"field_status", "source", "status", "brief_id", "brief_version", "feature_id"}
        declared = getattr(self, "status", EvidenceStatus.assumed)
        if "status" not in self.model_fields_set:
            declared = EvidenceStatus.assumed
        for name in type(self).model_fields:
            if name in excluded:
                continue
            value = getattr(self, name)
            if value is None:
                statuses[name] = EvidenceStatus.unknown
            elif name not in self.model_fields_set:
                statuses[name] = EvidenceStatus.assumed
            else:
                statuses.setdefault(name, declared)
        object.__setattr__(self, "field_status", statuses)
        return self


class BuildConstraints(AssumptionInput):
    cash_budget_usd: Optional[NonNegativeDecimal] = None
    time_budget_weeks: Optional[NonNegativeDecimal] = None
    team_size: PositiveInt = 1
    technical_skill: Literal["none", "scripting", "professional"] = "scripting"
    devops_capacity: Literal["none", "basic", "full"] = "none"
    status: EvidenceStatus = EvidenceStatus.assumed


class FeatureItem(PublicInput):
    feature_id: NonBlank
    title: NonBlank
    size_class: Literal["S", "M", "L", "XL"]
    compute_heavy: bool = False


class UsageAssumptions(AssumptionInput):
    active_users: Optional[NonNegativeInt] = None
    workflows_per_user_month: Optional[NonNegativeDecimal] = None
    calls_per_workflow: Optional[PositiveDecimal] = None
    paying_fraction: Optional[Fraction] = None
    subscription_price_usd: Optional[NonNegativeDecimal] = None
    status: EvidenceStatus = EvidenceStatus.unknown


class FounderBrief(AssumptionInput):
    brief_id: NonBlank
    brief_version: NonBlank
    product_concept: NonBlank
    target_user: NonBlank
    features_v1: list[FeatureItem] = Field(default_factory=list)
    constraints: BuildConstraints = Field(default_factory=BuildConstraints)
    quality_needs: list[NonBlank] = Field(default_factory=list)
    alternatives_considered: list[NonBlank] = Field(default_factory=list)
    usage: UsageAssumptions = Field(default_factory=UsageAssumptions)
    ai_features: list[FeatureProfile] = Field(default_factory=list)
    growth_stages: list[Stage] = Field(default_factory=lambda: default_stages(), min_length=1)
    monthly_ai_budget_usd: Optional[NonNegativeDecimal] = None
    switch_threshold_usd: NonNegativeDecimal = Decimal("100")
    source: Optional[SourceRef] = None

    @model_validator(mode="after")
    def _unique_ids(self):
        require_unique([f.feature_id for f in self.ai_features], "AI feature IDs")
        require_unique([f.feature_id for f in self.features_v1], "Build feature IDs")
        require_unique([s.name for s in self.growth_stages], "Stage names")
        return self


# --------------------------------------------------------- pricing snapshots

class RateCategory(str, Enum):
    input_tokens = "input_tokens"
    output_tokens = "output_tokens"
    cached_input_tokens = "cached_input_tokens"
    reasoning_tokens = "reasoning_tokens"
    cache_write_tokens = "cache_write_tokens"                 # cached_input_tokens is the cache-read rate
    long_context_input_tokens = "long_context_input_tokens"   # whole-request rate above the threshold
    long_context_output_tokens = "long_context_output_tokens"
    long_context_cached_input_tokens = "long_context_cached_input_tokens"
    long_context_cache_write_tokens = "long_context_cache_write_tokens"
    audio_input_tokens = "audio_input_tokens"
    audio_output_tokens = "audio_output_tokens"
    credits = "credits"
    seat_month = "seat_month"
    hosting_month = "hosting_month"


class Rate(BaseModel):
    category: RateCategory
    unit: str                        # "1M tokens" | "credit" | "seat/month" | "month"
    usd_per_unit: Optional[NonNegativeDecimal]  # None == unknown, and stays unknown
    status: EvidenceStatus
    source: SourceRef


class ApproachProfile(BaseModel):
    """A development approach the founder could commit to (e.g. app-builder, IDE agent + own hosting, API-only)."""
    approach_id: str
    name: str
    rates: list[Rate]
    credits_per_task_class: Optional[dict[str, NonNegativeDecimal]] = None  # S/M/L/XL -> credits, when the platform bills in credits
    tokens_per_task_class: Optional[dict[str, NonNegativeDecimal]] = None   # S/M/L/XL -> tokens (in+out), when billed by token
    requires_devops: Literal["none", "basic", "full"] = "none"
    notes: list[str] = Field(default_factory=list)
    source: SourceRef


class LeverCombination(BaseModel):
    """A cited provider rule for an exact combination; pairwise support is not triple support."""
    model_config = ConfigDict(extra="forbid")
    levers: list[Literal["prompt_caching", "batch_api", "long_context_cliff"]] = Field(min_length=2, max_length=3)
    supported: bool
    source: SourceRef

    @model_validator(mode="after")
    def _distinct_levers(self):
        require_unique(self.levers, "Levers in a pricing combination")
        return self


class ModelPricingTerms(BaseModel):
    """Provider terms that decide lever eligibility (07 §5.1). None == unknown, so the lever is not applied."""
    cache_min_prefix_tokens: Optional[NonNegativeInt] = None
    cache_ttl_minutes: Optional[PositiveDecimal] = None
    batch_available: Optional[bool] = None
    batch_discount: Optional[Fraction] = None          # 0.5 == 50% off input and output
    long_context_threshold_tokens: Optional[NonNegativeInt] = None
    lever_combinations: list[LeverCombination] = Field(default_factory=list)
    status: EvidenceStatus = EvidenceStatus.unknown

    @model_validator(mode="after")
    def _unique_combinations(self):
        require_unique(["/".join(sorted(item.levers)) for item in self.lever_combinations], "Pricing combinations")
        return self


class AudioConversion(BaseModel):
    """Seconds of audio to billed audio tokens. Always an estimate until measured from API usage fields."""
    input_tokens_per_second: Optional[NonNegativeDecimal] = None
    output_tokens_per_second: Optional[NonNegativeDecimal] = None
    basis: Literal["estimated"] = "estimated"
    status: EvidenceStatus = EvidenceStatus.unverified
    source: Optional[SourceRef] = None


class IntelligenceScore(BaseModel):
    """A published capability index for a model. It only ranks the shortlist; it never replaces measurement."""
    score: NonNegativeDecimal
    score_source: str
    score_date: str
    status: EvidenceStatus = EvidenceStatus.unverified


class MarketReference(BaseModel):
    """A catalog snapshot used for ranking and separately labeled hypothetical serving scenarios."""
    catalog: Literal["OpenRouter"] = "OpenRouter"
    catalog_id: Optional[str] = Field(default=None, exclude_if=lambda value: value is None)
    snapshot_date: str
    list_price_input_usd_per_m: Optional[NonNegativeDecimal] = None
    list_price_output_usd_per_m: Optional[NonNegativeDecimal] = None
    usage_rank: Optional[PositiveInt] = None          # 1 == most used in the catalog snapshot
    # Catalog reference only. None == the snapshot did not carry the field, which stays unknown, not "text only".
    input_modalities: Optional[list[str]] = Field(default=None, exclude_if=lambda value: value is None)
    output_modalities: Optional[list[str]] = Field(default=None, exclude_if=lambda value: value is None)
    # True when the catalog lists a Hugging Face ID. A signal that weights are published, not a licence finding.
    open_weights_signal: Optional[bool] = Field(default=None, exclude_if=lambda value: value is None)
    status: EvidenceStatus = EvidenceStatus.unverified

    @computed_field
    @property
    def label(self) -> str:
        return f"market reference ({self.catalog}, {self.snapshot_date})"


class DispatchPolicy(PublicInput):
    """Route-specific, cited upper bounds; never inferred from expected output or sample prices."""
    max_prompt_bytes: PositiveInt
    prompt_tokens_per_byte: PositiveDecimal
    prompt_overhead_tokens: NonNegativeInt
    max_output_tokens: PositiveInt
    completion_limit_includes_reasoning: Literal[True]
    billing_mode: Literal["input_output_only"]
    source: SourceRef


class ModelProfile(BaseModel):
    model_id: str                    # as exposed by Nightshift GET /v1/models
    provider_label: str              # e.g. "nvidia" — informational
    tier: Optional[Literal["frontier", "mid_tier", "open_source"]] = None
    required: bool = False           # open_source: the explicitly pinned route, always a candidate regardless of score
    rates: list[Rate]
    terms: ModelPricingTerms = Field(default_factory=ModelPricingTerms)
    audio: Optional[AudioConversion] = None   # None == audio not priced for this model; stays unknown
    intelligence: Optional[IntelligenceScore] = None
    market: Optional[MarketReference] = None
    source: SourceRef
    dispatch_policy: Optional[DispatchPolicy] = None


class ShortlistEntry(BaseModel):
    """One snapshot model and why it was or was not selected as its tier's candidate. Reference data shown here
    (score, market reference, price per intelligence point) never feeds stage tables, switch points or the model stack."""
    model_id: str
    tier: Optional[str] = None
    nightshift_route: Optional[bool] = None   # None == not checked (sample mode)
    intelligence: Optional[IntelligenceScore] = None
    market: Optional[MarketReference] = None
    price_per_intelligence_point_usd: Optional[Decimal] = None
    price_per_intelligence_point_label: Optional[str] = None
    selected: bool = False
    selected_for: list[str] = Field(default_factory=list, exclude_if=lambda value: not value)   # feature IDs it was chosen for
    reason: str


# ------------------------------------------------- AI features and stages (07 §2, §5.1)

CheckKind = Literal["max_words", "required_json_fields", "forbidden_terms", "regex", "human_review"]


class RubricCheck(PublicInput):
    """A deterministic check on a model output; these and human review decide pass/fail, never a model.

    params by kind (json_field optional for all but required_json_fields: check one field of a JSON output):
      max_words            {"limit": int}
      required_json_fields {"fields": [str, ...]}
      forbidden_terms      {"terms": [str, ...]}           case-insensitive substring match
      regex                {"pattern": str, "must_match": bool = true, "ignore_case": bool = false}
      human_review         {}  no machine result; pending until a reviewer records one
    """
    check_id: NonBlank
    description: NonBlank
    kind: CheckKind = "human_review"
    params: dict = Field(default_factory=dict)
    critical: bool = True            # a cheaper model must pass every critical check to qualify a switch point

    @model_validator(mode="after")
    def _params_match_kind(self):
        p = self.params
        allowed = {
            "max_words": {"limit", "json_field"},
            "required_json_fields": {"fields"},
            "forbidden_terms": {"terms", "json_field"},
            "regex": {"pattern", "must_match", "ignore_case", "json_field"},
            "human_review": set(),
        }[self.kind]
        if set(p) - allowed:
            raise ValueError(f"rubric check {self.check_id}: unsupported params {sorted(set(p) - allowed)}")
        if "json_field" in p and (not isinstance(p["json_field"], str) or not p["json_field"].strip()):
            raise ValueError(f"rubric check {self.check_id}: json_field must be nonblank")
        if any(key in p and not isinstance(p[key], bool) for key in ("must_match", "ignore_case")):
            raise ValueError(f"rubric check {self.check_id}: matching flags must be booleans")
        ok = {
            "max_words": lambda: type(p.get("limit")) is int and p["limit"] > 0,
            "required_json_fields": lambda: isinstance(p.get("fields"), list) and p["fields"]
                                            and all(isinstance(f, str) and f.strip() for f in p["fields"])
                                            and len(set(p["fields"])) == len(p["fields"]),
            "forbidden_terms": lambda: isinstance(p.get("terms"), list) and p["terms"]
                                       and all(isinstance(t, str) and t.strip() for t in p["terms"]),
            "regex": lambda: isinstance(p.get("pattern"), str) and bool(p["pattern"].strip()),
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


class HumanReview(PublicInput):
    """A reviewer's result for one check on one feature × model; it overrides the machine result."""
    feature_id: NonBlank
    model_id: NonBlank
    check_id: NonBlank
    passed: bool
    reviewer: NonBlank
    note: str = ""


class FeatureProfile(AssumptionInput):
    """One AI feature of the founder's SaaS idea. Volume fields are the founder's estimate."""
    feature_id: NonBlank
    description: NonBlank
    example_input: NonBlank
    mode: Literal["interactive", "background"]
    modality: list[Literal["text", "audio_in", "audio_out", "image_in", "image_out"]] = Field(
        default_factory=lambda: ["text"], min_length=1)
    audio_seconds_per_use: Optional[NonNegativeDecimal] = None   # applied to each audio direction in modality
    revenue_per_use: Optional[NonNegativeDecimal] = None          # present -> AI cost per use as a share of revenue per use
    uses_per_user_month: Optional[NonNegativeDecimal] = None
    calls_per_use: PositiveDecimal = Decimal("1")
    static_prefix_tokens: NonNegativeInt = 0    # instructions repeated on every call; part of the input
    expected_output_words: Optional[NonNegativeInt] = None   # used only to estimate output tokens offline
    # Share of uses served from a cache of previously generated outputs (e.g. the same sentence spoken again);
    # a production-setup projection, not measured. distinct_outputs sizes the one-time cache fill.
    output_reuse_rate: Optional[Fraction] = None
    distinct_outputs: Optional[PositiveInt] = None
    rubric_checks: list[RubricCheck] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_checks(self):
        require_unique([c.check_id for c in self.rubric_checks], "Rubric check IDs within a feature")
        require_unique(self.modality, "Modalities within a feature")
        return self


class Stage(PublicInput):
    name: NonBlank
    active_users: NonNegativeInt
    status: EvidenceStatus = EvidenceStatus.assumed


def default_stages() -> list[Stage]:
    """Editable defaults (07 §5.1), labeled assumed."""
    return [Stage(name="Prototype", active_users=50), Stage(name="Launch", active_users=500),
            Stage(name="Traction", active_users=5000), Stage(name="Scale", active_users=50000)]


class TokenUsage(BaseModel):
    """Per-call tokens. measured == from API usage fields only; estimated == 4/3 rule on words.
    output_tokens is the completion count and already INCLUDES reasoning_tokens (OpenAI-compatible usage).
    Decimal so a mean over samples is kept exactly."""
    input_tokens: NonNegativeDecimal
    output_tokens: NonNegativeDecimal
    reasoning_tokens: Optional[NonNegativeDecimal] = None   # breakdown of output_tokens; None == unknown, never coerced to zero
    audio_input_tokens: Optional[NonNegativeDecimal] = None    # measured only; None -> estimated from seconds if the feature has audio
    audio_output_tokens: Optional[NonNegativeDecimal] = None
    basis: Literal["measured", "estimated"]
    method: str
    truncated: bool = False   # measured output stopped at max_tokens, so output_tokens is a lower bound

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
    receipt_id: Optional[str] = None
    provider: Optional[str] = None
    provider_kind: Optional[str] = None
    max_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    truncated: bool = False                  # the answer was cut at max_tokens; its text is incomplete


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
    monthly_usd: Optional[NonNegativeDecimal]
    billed: bool = True              # False == breakdown only (reasoning is inside output); never added to the bill
    note: str = ""


class LeverLine(BaseModel):
    """Shown separately from the gross cost, never silently netted."""
    lever: Literal["prompt_caching", "batch_api", "output_cap", "long_context_cliff", "output_reuse"]
    applies: bool
    reason: str
    monthly_delta_usd: Optional[Annotated[Decimal, Field(allow_inf_nan=False)]] = None   # negative == saving, positive == surcharge
    one_time_usd: Optional[NonNegativeDecimal] = None        # output_reuse: filling the cache once; never added to a monthly total
    label: Optional[str] = None                   # "projected (production setup)" for caching, batch and output reuse
    _exact_monthly_delta: Optional[Decimal] = PrivateAttr(default=None)


class StageCostRow(BaseModel):
    feature_id: str
    stage: str
    active_users: NonNegativeInt
    model_id: str
    tier: Optional[str] = None
    calls_per_month: Optional[NonNegativeDecimal]
    cost_per_call_usd: Optional[NonNegativeDecimal]
    token_basis: Literal["measured", "estimated"]
    lines: list[CostLine]
    gross_monthly_usd: Optional[NonNegativeDecimal]
    levers: list[LeverLine]
    monthly_with_levers_usd: Optional[NonNegativeDecimal]
    cost_per_use_usd: Optional[NonNegativeDecimal] = None
    revenue_per_use_usd: Optional[NonNegativeDecimal] = None
    revenue_share: Optional[NonNegativeDecimal] = None   # AI cost per use / revenue per use; None when revenue absent
    lower_bound: bool = False        # True when an unknown component (e.g. reasoning tokens) is excluded
    rate_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # Unrounded values for downstream rules (switch points, revenue risk); not serialized.
    _exact_gross: Optional[Decimal] = PrivateAttr(default=None)
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


class OpenRouterProjectionTable(BaseModel):
    """Conditional OpenRouter serving cost, separate from the actual-route operating table."""
    feature_id: str
    pricing_scope: Literal["openrouter_listed_token_scenario"] = "openrouter_listed_token_scenario"
    rows: list[StageCostRow] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
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


class StageTotal(BaseModel):
    """R9: the monthly AI cost of all features together at one growth stage, for one way of choosing models.
    AI-only: non-AI operating costs are outside the model, and one-time build costs stay in the build ledger.
    Unknown feature costs are never counted as zero; the total then covers the known features only."""
    scenario: Literal["recommended", "cheapest_per_feature", "single_model"]
    pricing_scope: Literal["actual_route", "openrouter_listed_token_scenario"]
    model_id: Optional[str] = None                        # single_model only
    stage: str
    active_users: NonNegativeInt
    feature_models: dict[str, Optional[str]] = Field(default_factory=dict)
    feature_costs: dict[str, Optional[Decimal]] = Field(default_factory=dict)   # None == unknown
    monthly_usd: Optional[Decimal] = None                 # sum of the known feature costs; None when none is known
    complete: bool = False                                # every feature has a known cost
    lower_bound: bool = True                              # incomplete, or a summed row leaves out an unknown component
    revenue_usd: Optional[Decimal] = None                 # active users x paying fraction x subscription price
    ai_contribution_usd: Optional[Decimal] = None         # revenue - AI cost; at most this when the cost is a lower bound
    ai_contribution_margin: Optional[Decimal] = None      # contribution / revenue, only when revenue > 0
    budget_fit: Literal["within", "over", "unknown", "no_budget"] = "no_budget"
    note: str = ""


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


class RunRequest(PublicInput):
    schema_version: Literal["1.1"] = "1.1"
    project_id: Annotated[NonBlank, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]
    run_id: Annotated[NonBlank, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]  # also the idempotency key and trace filename
    brief: FounderBrief
    evaluation_approved: bool = False
    max_spend_usd: Annotated[NonNegativeDecimal, Field(le=25)] = Decimal("0")
    sample_mode: Optional[bool] = None
    human_reviews: list[HumanReview] = Field(default_factory=list)
    sampling_profile: Literal["production", "validation"] = "production"
    candidate_tiers: list[Literal["frontier", "mid_tier", "open_source"]] | None = None
    # Optional founder choice of 1-3 candidate routes for every feature, replacing the automatic choice. The controller
    # still validates each (offered, priced, modality, one per tier) and executes only routes with a verified profile.
    candidate_models: Optional[list[NonBlank]] = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="before")
    @classmethod
    def _migrate_v1(cls, value):
        """Legacy envelopes normalize to 1.1; they receive the same strict validation."""
        if isinstance(value, dict) and value.get("schema_version", "1.0") == "1.0":
            return {**value, "schema_version": "1.1"}
        return value

    @model_validator(mode="after")
    def _feature_count(self):
        if not 2 <= len(self.brief.ai_features) <= 5:
            raise ValueError("A founder run requires 2–5 AI features")
        if self.candidate_tiers is not None:
            if self.sampling_profile != "validation":
                raise ValueError("candidate_tiers is available only for validation sampling")
            if not 2 <= len(self.candidate_tiers) <= 3 or len(set(self.candidate_tiers)) != len(self.candidate_tiers):
                raise ValueError("candidate_tiers requires two or three unique candidate tiers")
        if self.candidate_models is not None:
            if not 1 <= len(self.candidate_models) <= 3 or len(set(self.candidate_models)) != len(self.candidate_models):
                raise ValueError("candidate_models requires one to three unique route IDs")
            if self.candidate_tiers is not None:
                raise ValueError("candidate_models and candidate_tiers cannot be combined")
        return self


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


class ReadinessCheck(BaseModel):
    """Observed diagnostic evidence; skipped required checks never establish readiness."""
    name: NonBlank
    status: Literal["pass", "fail", "skip", "not_verified"]
    required: bool = True
    detail: str = ""


class ReadinessResult(BaseModel):
    scope: Literal["sponsor_integration", "live_diagnostic"] = "sponsor_integration"
    checks: list[ReadinessCheck] = Field(default_factory=list)
    # Orthogonal integration facts. These describe what is known about a route
    # without promoting it to sponsor readiness or paid-dispatch eligibility.
    dimensions: list[ReadinessCheck] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_checks(self):
        require_unique([check.name for check in self.checks], "readiness check names")
        require_unique([check.name for check in self.dimensions], "readiness dimension names")
        return self

    @computed_field
    @property
    def status(self) -> Literal["ready", "not_ready", "incomplete", "not_verified"]:
        required = [check for check in self.checks if check.required]
        if any(check.status == "fail" for check in required):
            return "not_ready"
        if any(check.status == "skip" for check in required):
            return "incomplete"
        if not required or any(check.status == "not_verified" for check in required):
            return "not_verified"
        return "ready"


def unverified_sponsor_readiness() -> ReadinessResult:
    # A completed pack or a connectivity diagnostic proves none of these end-to-end requirements.
    return ReadinessResult(checks=[ReadinessCheck(name=name, status="not_verified", detail=detail) for name, detail in (
        ("zetaris_roundtrip", "Requires sourced reads and evidence write/readback (M06)."),
        ("hmem_persistence", "Requires pinned-engine restart, recall, isolation and audit (M07)."),
        ("nightshift_candidates", "Requires identified, usage-bearing candidate executions (M08)."),
        ("nemotron_feature", "Requires a working feature with corroborated Nemotron identity (M08)."),
    )])


class DispatchRecord(BaseModel):
    operation_id: str
    logical_id: str
    attempt: PositiveInt
    role: Literal["Planner", "Analyst", "Critic", "Revision", "Diagnostic"]
    requested_model: str
    resolved_model: Optional[str] = None
    provider_request_id: Optional[str] = None
    provider_receipt_id: Optional[str] = None
    provider: Optional[str] = None
    provider_kind: Optional[str] = None
    state: Literal["dispatching", "completed", "unknown", "not_dispatched", "overrun"]
    reserved_usd: NonNegativeDecimal
    actual_usd: Optional[NonNegativeDecimal] = None
    prompt_token_bound: PositiveInt
    max_tokens: PositiveInt
    usage: dict = Field(default_factory=dict)
    error_type: Optional[str] = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class DecisionPack(BaseModel):
    schema_version: Literal["1.1"] = "1.1"
    run_id: str
    project_id: str
    execution_mode: Literal["live", "sample"]
    status: RunState
    readiness: ReadinessResult = Field(default_factory=unverified_sponsor_readiness)
    monthly_ai_budget_usd: Optional[NonNegativeDecimal] = None
    switch_threshold_usd: NonNegativeDecimal = Decimal("100")
    reasons: list[str] = Field(default_factory=list)
    candidate_shortlist: list[ShortlistEntry] = Field(default_factory=list)
    model_stack: list[ModelStackEntry] = Field(default_factory=list)
    stage_tables: list[StageCostTable] = Field(default_factory=list)
    openrouter_projection_tables: list[OpenRouterProjectionTable] = Field(default_factory=list)
    stage_totals: list[StageTotal] = Field(default_factory=list)
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
    spend_usd: NonNegativeDecimal = Decimal("0")
    reserved_spend_usd: NonNegativeDecimal = Decimal("0")
    dispatch_count: NonNegativeInt = 0
    transport_retries: NonNegativeInt = 0
    selected_samples_per_pair: NonNegativeInt = 0
    sampling_profile: Literal["production", "validation"] = "production"
    candidate_tiers: list[Literal["frontier", "mid_tier", "open_source"]] = Field(
        default_factory=lambda: ["frontier", "mid_tier", "open_source"])
    operations: list[DispatchRecord] = Field(default_factory=list)
    unpublished_evidence_ids: list[str] = Field(default_factory=list)
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


# ------------------------------------------------- modality capability (catalog reference)

# Feature modality -> (catalog direction, catalog modality name a model must list).
MODALITY_CAPABILITY = {"text": ("input", "text"), "audio_in": ("input", "audio"), "image_in": ("input", "image"),
                       "audio_out": ("output", "audio"), "image_out": ("output", "image")}


def covers_modalities(market: Optional[MarketReference], modalities) -> Optional[bool]:
    """True/False when the catalog reference says whether a model covers every feature modality; None when it
    does not carry the field (unknown, never assumed text-only). A text feature always needs text output too."""
    if market is None or market.input_modalities is None or market.output_modalities is None:
        return None
    have = {"input": set(market.input_modalities), "output": set(market.output_modalities)}
    needed = {MODALITY_CAPABILITY[m] for m in modalities} | {("output", "text")}
    return all(name in have[direction] for direction, name in needed)
