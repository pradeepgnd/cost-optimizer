# Retrospective founder case study: AIM Volatility Lab build decision

Version 1.0 | October 23, 2026 (late evening) | Owner: Narin | Supersedes the approved-FAQ sandbox in PRD v3.3 §1, §6 and plan §5

## 0. The hard part first

This pivot is right for Impact (30 points) and wrong for nothing in the rules. A real founder who spent more than $15,000 in platform credits and would have chosen differently with a decision agent in hand is a far stronger challenge statement than a synthetic FAQ bot. Judges will remember it.

It carries three risks the FAQ design did not, and each has a control below:

1. **Hindsight leakage.** The person writing the starting brief is the person who lived the outcome. Control: §4.
2. **Grading difficulty.** Development-task outputs are harder to grade deterministically than FAQ facts. Control: §5, structured outputs with required-element rubrics plus human review, exactly as the PRD already demanded for FAQ semantics.
3. **N=1.** One founder, one project, retrospective. Control: §6 reports agreement metrics, never savings; §7 keeps one or two external founders as a secondary impact signal if hours allow.

A fourth point is not a risk but a boundary: the agent cannot execute Emergent, Cursor or any platform build. Approach-level comparison is evidence-based (verified pricing × a bounded task plan); only the model-level comparison is executed, through Nightshift. The decision pack says so.

## 1. Cost model: development versus operating

PRD v3.3 §7 modeled post-launch inference economics in detail and treated development effort as "an editable range, not a quote." For this case study the emphasis inverts: the founder's real exposure was build-phase spend, and the operating model is secondary context. Both remain in the PRD; the agent now reports them as two separate ledgers that are never summed into one number.

### 1.1 AI-assisted development cost (build phase, one-time but recurring until launch)

```text
planned_build_tasks        = founder's scoped feature list → bounded task plan (count × size class)
approach_unit_cost[a]      = verified rate for approach a (credits per task class, tokens per task class,
                             or seat price per month) from pricing_snapshots, with provenance
base_build_cost[a]         = Σ_tasks approach_unit_cost[a] × size_class_multiplier
rework_multiplier          = ASSUMED, editable, default range low 1.3 / base 1.8 / high 2.5,
                             labeled "assumed — no project-specific evidence"
expected_build_cost[a]     = base_build_cost[a] × rework_multiplier            (low/base/high)
founder_time_cost          = hours × imputed rate, reported separately, never added to cash
checkpoint_spend[a][k]     = cumulative expected_build_cost at milestone k → decision-gate threshold
```

Unknown rates stay unknown. A platform that bills in credits whose dollar value is not published yields a credits-denominated range with the conversion marked unverified.

### 1.2 Post-launch operating cost (monthly, per PRD v3.3 §7, unchanged)

Hosting tier, data feeds, inference per user, storage, support tooling. Uses the existing `calls / billable_calls / monthly_cash_cost / contribution / margin` block. For AIM Volatility Lab this is modeled from the *final* architecture and tier pricing, which are sealed until freeze (§4), so the live agent run produces a conditional operating estimate from the brief's assumptions only, and the post-freeze comparison shows how far the brief's assumptions were from the shipped reality.

### 1.3 Why the split matters to the founder

A founder choosing an AI app-builder platform is trading a low operating-skill requirement for a build-phase cost that is credit-metered and opaque. A founder choosing an IDE agent plus their own hosting trades the opposite. The decision pack must show the two ledgers side by side with their uncertainties, because the right answer depends on which uncertainty the founder can survive. That is the product thesis in one sentence, and it should be on the deck's "unique" slide.

## 2. Bounded evaluation design

### 2.1 Inputs: the starting brief

Reconstructed from pre-build artifacts only (§4 controls). Fields:

| Field | Source | Status label |
|---|---|---|
| Product concept and target user | pre-build notes, domain registration date, early positioning text | `verified` if a dated artifact exists, else `reconstructed` |
| Scoped feature list for v1 | pre-build notes or first-week task list | same |
| Founder constraints: cash budget, time budget, technical skills, solo/team | Narin's statement, dated to the pre-build period | `reconstructed — founder recollection` |
| Quality/latency needs (compute-heavy backtests, concurrency expectations) | pre-build notes if any | same |
| Known alternatives considered at the time | Narin's statement | `reconstructed` |
| Expected usage at launch (users, runs/day) | pre-build assumption or `unknown` | `unknown` is acceptable and triggers cost-only mode |

**Never in the brief:** platform chosen, model used, dollars spent, timeline that unfolded, rework incidents, final architecture, tier pricing, launch state.

### 2.2 Zetaris source sets (replace the FAQ sets)

| Source set | Contents | Access |
|---|---|---|
| `founder_briefs` | the reconstructed brief, versioned, with per-field status labels | planner, live |
| `pricing_snapshots` | dated, URL-cited rates for Emergent and two or three alternatives (an IDE-agent path such as Cursor or Claude Code with own hosting; a second app-builder; a hosted-model-API-only path), plus token rates for the candidate models behind Nightshift | planner, live |
| `dev_task_cases` | 8 development task cases derived from the v1 feature list (3 development, 5 holdout), each with required-element rubric | development cases to planner; holdout sealed until freeze |
| `evaluation_evidence` | executed case results, critiques, revisions | planner, live |
| `retrospective_actuals` | **sealed**: credits purchased and consumed by month, total spend, milestone dates, rework incidents (count, cause class, approximate credit cost), final architecture, hosting tier, operating costs | **no read permitted until state = frozen**; controller allowlist enforces; trace proves |

The actuals are the founder's own business records, de-identified to aggregates. Rules §11 permits them with the owner's authorization; the README states that authorization. Sample mode ships a clearly labeled synthetic analogue, not the real figures, unless Narin signs off on committing the aggregate.

### 2.3 Representative development tasks (what gets executed)

Tasks are drawn from the v1 feature list and chosen so a rubric can grade them without running code. Each asks for a structured implementation specification: interface, data contract, acceptance tests, failure modes, compute/cost note. Six tasks, three development and three holdout:

| # | Task (spec-level, not full implementation) | Set | Why it is representative |
|---|---|---|---|
| T1 | Specify price-history ingestion for arbitrary equity/crypto tickers: bar schema, caching, rate-limit handling, acceptance tests | dev | every later task depends on clean price history; caching and rate limits are common integration failure points |
| T2 | Specify one rule-engine contract that five mechanical trading rules implement: rule interface, parameter contract, signal record, deterministic evaluation, acceptance tests | dev | a shared contract tests whether a configuration can generalize across rules instead of special-casing each |
| T3 | Specify a walk-forward runner for one rule: window schedule, in-sample/out-of-sample split, result record, compute bound per run | dev | the core evaluation loop; compute cost per run feeds both ledgers |
| T4 | Specify a comparison of rule results against buy-and-hold on the same ticker and window: benchmark definition, metric set, data contract, acceptance tests | holdout | |
| T5 | Specify a parameter optimizer that selects on out-of-sample performance only: search space, selection rule, result cache, compute bound | holdout | |
| T6 | Specify how results are presented to a self-directed retail trader: plain-language summary, metric explanations, risk disclosure, acceptance tests | holdout | |

Each task runs through two configurations behind Nightshift (two model IDs, or two workflow configurations of one model if only one is available, labeled accordingly). The Nemotron critic reviews the three development outputs against the brief and rubric: unsupported assumptions, missing failure modes, cost claims with no source. One permitted repair, then freeze, then three holdout tasks paired. Call budget stays within the PRD cap: 6 + 3 + 6 = 15 primary generations, leaving headroom under 23.

Four approaches are priced from `pricing_snapshots`:

| Approach | Billing basis | DevOps required |
|---|---|---|
| Emergent (credit-metered AI app-builder) | credits per task class; credit-to-USD conversion must be cited or stays unverified | none |
| Replit Agent (managed app-builder with hosting) | agent usage credits plus seat price | none |
| IDE coding agent with own hosting | model tokens plus seat price; hosting separate | basic |
| Hosted model API with a hand-built app | model tokens; hosting and app built by the founder | full |

Approach-level alternatives are **not executed**. They are compared on verified pricing × the task plan, with the rework multiplier shown as an assumption. The decision pack states this limit in its first paragraph.

## 3. Minimum records needed from Narin

| # | Record | Used for | If missing |
|---|---|---|---|
| M1 | Any dated pre-build artifact: notes, a message, a domain or hosting receipt, an early positioning draft | `founder_briefs`, provenance for the no-hindsight control | brief fields carry `reconstructed — founder recollection`; the control relies on Meena's leakage review alone |
| M2 | v1 feature list as intended before build (or the earliest list that exists, dated) | `dev_task_cases` derivation | tasks are derived from the shipped feature set and labeled `derived from outcome — weaker` |
| M3 | Emergent billing: credit purchases (date, amount), consumption by month, dollar-per-credit rate | `retrospective_actuals`; `pricing_snapshots` provenance | total spend only, labeled `aggregate, month profile unknown` |
| M4 | Milestone dates: first prototype, first full backtest, metering added, pre-launch state | `retrospective_actuals`; checkpoint scoring | checkpoints scored on spend only, not time |
| M5 | Rework log: incidents where work was redone, cause class (requirements change, platform limitation, model error, scaling), approximate credit cost | `retrospective_actuals`; "did the agent surface this risk?" scoring | risk-surfacing scored as `unscorable — no incident record` |
| M6 | Model identity on Emergent ("Fable") and any per-token or per-credit pricing exposed by the platform | `pricing_snapshots` | labeled `UNVERIFIED — platform did not expose model/rate` ; no comparison against that model's list price is made |
| M7 | Final architecture and hosting tier; current monthly operating costs | post-freeze operating-ledger comparison | operating comparison omitted; cost-only build ledger stands alone |
| M8 | Public pricing pages, dated, for Emergent and the chosen alternatives (Isioma collects; Narin confirms which alternatives he actually considered) | `pricing_snapshots` | an alternative with no verifiable rate is shown as `unknown rate`, not excluded silently |

Missing-evidence labels are part of the output, not footnotes. The decision pack has a section titled "Evidence gaps" listing every `reconstructed`, `unknown`, `UNVERIFIED` and `unscorable` item.

## 4. Hindsight controls

1. **Authorship.** Narin writes the brief from M1/M2 only, in one sitting, dated, before reading any actuals back.
2. **Independent leakage review.** Meena (who did not build AIM Volatility Lab) reviews the brief against a forbidden-terms list: platform names chosen, model names used, dollar figures, dates after the build started, rework, launch state, tier prices. Any hit is removed. The review is a checked item in the release checklist.
3. **Sealed actuals.** `retrospective_actuals` is a separate Zetaris source. The controller's allowlist refuses `retrieve_evidence` against it until run state is `frozen`. The trace of the live run shows zero reads of that source before freeze. This is the same mechanism the PRD already required for holdout cases.
4. **Prompt hygiene.** Planner, Analyst and Critic prompts never mention the founder's identity or the product name; the brief is referred to as "the founder's brief." Zetaris records carry IDs, not names.
5. **Comparison runs after freeze, by a separate script,** `scripts/compare_retrospective.py`, which reads the sealed source and the frozen decision pack and emits the §6 metrics. The agent never sees its own score in the same run.

## 5. Grading

Per task, per configuration: required elements present (deterministic checklist from the rubric), unsupported claims (critic finding validated against sources), cost note sourced (rate ID cited), failure modes named. Human semantic review by Isioma confirms the checklist; the LLM critic can flag but not certify. Record denominators, before/after repair for the three development cases, and the five paired holdout results. Small-sample language throughout.

## 6. Retrospective comparison: what the tool "would have surfaced"

All metrics are agreement-with-history on one case. None is a savings figure.

| Metric | Computation | Reporting language |
|---|---|---|
| Approach coverage | Was the approach actually taken among the agent's candidates? | "named / not named" |
| Build-range bracketing | Did low–high `expected_build_cost` for that approach bracket actual spend? Where did actual fall (low/base/high/outside)? | "bracketed at the high scenario" or "actual exceeded the high scenario by X%" |
| Checkpoint timing | Cumulative actual spend at each agent-proposed checkpoint; would a gate have fired before 25%, 50%, 75% of total actual spend? | "a gate at milestone 2 would have fired at ~$Y actual, 31% of total" — counterfactual, labeled |
| Risk surfacing | Of the rework cause classes in M5, how many appear in the agent's risk list? | "3 of 5 cause classes named; 2 missed: …" |
| Alternative surfacing | Did the agent name an alternative the founder did not consider at the time (per brief field)? | "named one alternative outside the founder's set" |
| Operating-ledger drift | Brief-assumed operating cost vs actual shipped operating cost | "assumption undershot actual hosting tier by one level" |

Forbidden sentence in any artifact: "the tool would have saved $N." Permitted: "with the agent's base scenario, a founder would have seen a $Y build estimate before committing; actual spend was $Z." Both numbers shown, no subtraction presented as a result.

## 7. Founder impact beyond N=1

Narin is the primary founder observation. If hours allow after Stage D, one or two external founders run their own brief through the tool and give before/after decisions. Reduced from "two or three" in v3.3; this is a cut-first item.

## 8. Fit to 40 hours, $100, sponsor requirements

- **Hours:** Isioma's W04 changes shape, not size: pricing snapshots for four approaches and 8 task rubrics replace FAQ curation and 10 FAQ cases. Narin adds ~1 hour for M1–M7 and the brief; Meena adds ~30 minutes for leakage review. Net neutral against the 32+8 plan.
- **Cash:** 19 primary generations of spec-level output (~2–4k tokens each) are well inside the $25 evaluation line on hosted Nemotron and peer models; confirm with actual Nightshift rates before approving the run.
- **Sponsor fit:** Zetaris remains the only data layer (five source sets, one sealed); H-MEM stores the founder's confirmed constraints and the accepted development findings across the restart demo; Nightshift carries every inference; Nemotron is the evidence critic with attributable model ID. Nothing in the sponsor table changes.
- **Track fit:** investigating a complex question across multiple sources (brief, pricing, task evidence, memory) and producing an evidence-backed recommendation — the Explain-Why statement verbatim.

## 9. What changes in the other documents

PRD v3.4: §1 task statement, §2 constraints (no pre-existing work; S3; Windows host preference), R02/R05 source and case wording, §6 replaced by a pointer to this design, §7 split into build and operating ledgers. Architecture v3.4: §5 source sets and sealed-access rule, §8 topology default, §10 S3 registration. Plan v3.4: §1 decisions recorded, W04 package, §5 feedback-loop experiment restated on T1–T3, Oct 24 preflight step.

## 10. Open items for Narin, tonight or first thing

1. Confirm the four approaches to price: Emergent; one IDE-agent path (Cursor or Claude Code) with own hosting; one second app-builder; API-only. Name them so Isioma can start.
2. Locate M1 and M2. Even one dated artifact changes the brief's status from `reconstructed` to `verified`.
3. Decide whether the aggregate actual spend may be committed to the public repository for sample mode, or whether sample mode uses a synthetic analogue only. Recommendation: synthetic analogue in the repo, real aggregate in Zetaris live and in the deck with your consent. It is your figure to disclose; the judges reward candor, but the repository is permanent.
4. Confirm T1–T8 against your actual v1 intent, or substitute.
