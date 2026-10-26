# AI SaaS Cost Advisor

**Open Agent Hackathon 2026 · Track: The Agent That Can Explain Why**

An agent that helps solo founders turn an AI SaaS idea into a costed technology plan. It runs the idea's core AI tasks on frontier and open-source models, measures real token usage and quality, and projects how monthly costs evolve from prototype to scale, including when to switch models.

**The problem.** A founder spent over $15,000 building with an AI app-builder, and no tool estimated what the app would cost to build or to run.

## Quick start (no credentials, no network)

```bash
git clone <repo> && cd <repo>
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
SAMPLE_MODE=true python run.py --input input_examples/example_1.json --output result.json
cat logs/trace-example-1.jsonl
python -m pytest -q
```

Sample mode runs the same controller, contracts and cost engine on bundled data. It makes zero network calls and executes no model: tokens are estimated with the 4/3 rule and labeled estimated, no outputs are produced, and rubric checks don't run. It never replays saved model answers and labels every output `SAMPLE/OFFLINE`. It is reproducibility for judges, not sponsor proof.

For a repeatable check of all three examples, run `python scripts/check_sample_examples.py`. The checker forces sample mode in copied requests, disables private dotenv loading, blocks Python sockets and Node network calls, and uses fresh databases and logs. It retains packs, traces and a `manifest.json` in a new temporary directory and prints its location. To retain them in a chosen location, pass `--output-dir <new-directory>`; existing directories are refused. A passing check establishes the offline baseline and local H-MEM delegation; live sponsor readiness needs later checks. See the [incremental implementation guide](docs/09-v4-Gap-Implementation-Guide.md) and [evidence ledger](docs/v4-release-checklist.md).

## Live mode

Requires Zetaris (Docker Desktop / WSL2) and Meterless Nightshift running locally; see the Participant Setup Guide. Fill `.env` from your Zetaris and Nightshift consoles (the NVIDIA key goes in Nightshift's Providers tab, never here), then:

```bash
python run.py --input input_examples/example_1.json --output result.json
```

Source setup now has an independent [Steps 5–6 manual test guide](docs/12-M05-M06-Manual-Testing.md): collect/validate a catalog, prepare pinned application records, preview/apply LocalStack or S3 registration, read typed rows and verify labeled evidence write/readback. These checks need no H-MEM or model completions. The OpenRouter collector retains raw/normalized data, exact hashes and explicit quarantine records. The [selected Ultra/Lightning/Gemma routes and OpenRouter projection](docs/13-M05-Serving-and-Billing-Selection.md) add a separate listed-token serving scenario; application model profiles keep those catalog prices separate from actual Nightshift execution tariffs.

Use the generated schema 1.1 bindings file through `ZETARIS_BINDINGS_FILE`. Every source row is checked against its pinned envelope hash; the earlier unbound `LIMIT 50` query is no longer the application read path. Optional build-source failure leaves the operating comparison available. Result ingestion runs in a separate publisher process, and the application retains a durable evidence outbox when write/readback is unavailable. AWS/Windows validation and applicable provider tariffs/billing bounds remain separate acceptance work. Recorded component evidence is in [m05-m06-source-checks.json](docs/m05-m06-source-checks.json).

Preflight for the Windows host: `scripts/preflight_windows.ps1` checks RAM, CPUs, disk, WSL2, Docker allocation and ports. With `-ZetarisUrl`/`-NightshiftUrl`, it validates the actual `SELECT 1` cell and model-discovery structure using the shared Python validators. Activate the project environment first, or pass `-PythonExecutable <path>`. Required SKIP/UNKNOWN or FAIL gives exit code 1. This is machine/connectivity evidence only; the revised PowerShell script still needs execution on Windows.

Live smoke test (diagnostic only, reads `.env`): `python scripts/smoke_live.py` checks Zetaris, Nightshift discovery and the H-MEM bridge separately. Paid diagnostic completions default to **disabled**. An explicit `--max-spend-usd <amount>` between $0 and $1, plus verified route prices/token bounds, allows one tiny completion per candidate through the same durable dispatcher. It saves a redacted Markdown table, typed JSON readiness/accounting and HTTP traces under `logs/`; `--output-dir <directory>` chooses report storage and `--no-dotenv` disables private dotenv loading. The operation ledger defaults to `<output-dir>/smoke-operations.db`; `--operations-db <path>` selects an existing ledger and `--run-id <id>` supplies a durable idempotency key. Reusing a key never replays paid work. Exit code 0 requires all seven diagnostic checks to pass; a required skip or missing check is non-success. Open-model diagnostics require explicit discovery/response identity and a response request ID. Passing diagnostics do not establish working-feature or end-to-end sponsor proof; model alias/receipt verification remains M08.

Incremental trace/readiness check (offline fixtures, no paid requests): `python -m pytest -q tests/test_trace.py tests/test_smoke_live.py`. See [M03 evidence](docs/evidence/v4-release-checklist.md#m03--trace-evidence-and-truthful-readiness).

## Interface

`run.py` is JSON in / JSON out. Input: `RunRequest` (see `app/contracts.py`): brief (idea, target user, 2–5 `ai_features`, `growth_stages`, optional build constraints), `evaluation_approved`, `max_spend_usd`, optional `human_reviews`. Examples: `input_examples/` (two founder ideas, one synthetic; every number labeled assumed). Output: `DecisionPack` with `status ∈ {complete, partial, needs_input, failed}` or a structured `RunError`. Exit codes: 0 valid result · 2 invalid input · 3 setup incomplete · 4 operational/duplicate. Trace: `logs/trace-<run_id>.jsonl` (organizer format, `model` per request, no invented confidence) plus readable `[INFO]` lines on stderr and one `final_result` JSON line on stdout.

Every pack and successful CLI `final_result` carries a separate typed `readiness` result. A completed sample pack has `readiness.scope: sponsor_integration` and `readiness.status: not_verified`; live packs also retain that status until the required integration evidence is implemented and verified in M06–M08. The same contract is available to the future UI. Numeric token usage, including nested reasoning counts, survives trace masking. HTTP attempts and terminal success/error events share an `operation_id`, with request/query IDs, adapter source hash, configuration reference and latency.

Current request/pack schema is **1.1**. An input marked `1.0`, or without a version, is normalized to `1.1` and receives the same validation. Full runs require 2–5 AI features, nonblank required text, unique feature/check/stage identifiers, finite non-negative costs and volumes, positive calls-per-use, valid fractions and an evaluation spend input between $0 and $25. Run/project IDs use letters, digits, dots, underscores and hyphens, starting with a letter or digit. Unexpected public fields are rejected before adapter setup instead of being silently discarded. Older invalid requests, including single-feature runs, must be corrected; migration does not bypass validation.

Both build fields (`brief.features_v1` and `brief.constraints`) can be omitted. Build costs then remain unknown and approaches are not ranked without a build scope. Value defaults and founder estimates receive per-field `assumed` provenance unless evidence is explicitly declared; nulls remain `unknown`, and metadata alone cannot promote an omitted default to verified. The new `brief.monthly_ai_budget_usd` (optional) and `brief.switch_threshold_usd` (default $100) survive request/pack export. The switch threshold feeds stage tables/model selection; the monthly ceiling is recorded with an explicit limitation until aggregate budget-fit analysis in M12.

Paid execution uses [the shared dispatcher](app/dispatch.py). Planner, candidates, Critic, repair and diagnostics all require explicit output limits (at most 1,024 tokens), a pinned route's verified USD-per-million rates and a cited `dispatch_policy` bounding prompt bytes, token overhead and completion tokens including hidden reasoning. Planner/Critic routes need their own billing profiles; `meterless/auto` cannot be priced safely. Missing/unverified rates or bounds produce a partial result and an evidence gap before paid dispatch. Sample placeholder data deliberately has no such policy; real evidence collection remains M05–M08.

Every attempt transactionally claims money and a slot in SQLite before entering the adapter. Charges are computed from measured usage at the applicable full input/output tariff; production cache/batch discounts are not assumed. Packs and CLI results distinguish known `spend_usd` from unresolved `reserved_spend_usd`; packs also expose `operations`, retry counts and selected samples. Unknown outcomes retain reservations and stop further spending. A usage/billing-bound overrun records the full known charge, even above the approved ceiling, and stops; the software cannot undo a runtime's violated limit. Only known pre-dispatch connect/connect-timeout/pool failures may retry, with another receipt/reservation/slot. Read/write timeouts, HTTP errors, malformed responses, missing usage and unpriced resolved identities are never automatically replayed. Correlation IDs do not imply provider idempotency. Existing run IDs are refused on restart; unresolved operations require external reconciliation, not a new automatic attempt.

The stricter [v4 call-budget policy](Planning/07-Realignment-v4.md) caps **all inference attempts, across roles and retries, at 30**. There is one logical Planner, one Critic and at most one repair, plus at most two safe retries globally. The default `sampling_profile: production` uses two samples per executable pair when the dispatch slots fit; four features need at most 29 slots including reserved repair/retry slots, while five use one sample. `sampling_profile: validation` explicitly selects one sample per pair for incremental checks. Spend is checked before each attempt; a selected sampling count does not guarantee the whole run fits the monetary budget.

For an incremental Ultra + Lightning comparison, a validation request may set `candidate_tiers: ["frontier", "mid_tier"]`. The [two-model manual guide](docs/16-M08-Two-Model-Validation.md) prepares a zero-spend request, checks its gate and runs the controller; the pack records that Gemma remains pending. Production requests keep all three tiers.

Incremental dispatch check (offline synthetic billing/HTTP fixtures): `python -m pytest -q tests/test_dispatch_limits.py tests/test_controller_live_fake.py`. See [M04 evidence](docs/evidence/v4-release-checklist.md#m04--bounded-dispatch-spend-and-restart-safety).

Incremental contract check: `python -m pytest -q tests/test_v4_contracts.py`. See [M01 evidence](docs/evidence/v4-release-checklist.md#m01--input-contracts-and-founder-controls) for the tested scope and remaining work.

## Architecture

v4 (`Planning/07-Realignment-v4.md`). The founder describes an AI SaaS idea and its 2–5 AI features; the agent measures what can be measured and labels the rest.

```
Founder idea + AI features ─► Controller (allowlist by state, call caps, spend reservation, SQLite checkpoints)
  1  Recall     H-MEM (Meterless)         earlier runs and confirmed assumptions for this idea
  2  Retrieve   Analyst ◄─ Zetaris         dated prices (input, output, cache, batch, audio, long-context),
                                           intelligence scores, OpenRouter market reference
  3  Select     Controller ◄─ Nightshift   candidate shortlist: one Nightshift route per tier (GET /v1/models,
                                           before any paid call); open-source is the required pinned route;
                                           shared candidate/Critic routes are disclosed
  4  Estimate   Analyst                    4/3 rule per feature × candidate, labeled estimated
     ── approval gate (evaluation_approved, max_spend_usd) ──
  5  Plan       Planner ◄─ Nightshift      domain risks only, labeled model-generated, not advice
  6  Execute    Analyst ◄─ Nightshift      each feature's example input on each candidate, 2 samples (1 if the cap needs it);
                                           measured tokens from API usage fields (output includes reasoning)
  7  Check      rubric checks              deterministic pass/fail (max_words, required_json_fields,
                                           forbidden_terms, regex) + human review; no model grades
  8  Critique   Critic ◄─ Nightshift       flags only: unsupported claims, token gaps, over-long output;
                                           proposes one action; controller validates it
  9  Repair     Analyst ◄─ Nightshift      at most one: re-run one feature × model with an output cap
 10  Project    economics (Decimal)        stage cost tables, levers, switch points, model stack
     └─ frozen ─► complete ─► DecisionPack ─► H-MEM (accepted decisions)
```

**Candidate shortlist.** One candidate per tier: frontier, mid-tier and open-source. In live mode only Nightshift routes are eligible; sample mode says the route check needs live mode.

- **Frontier and mid-tier:** the top-ranked eligible model by intelligence score, then OpenRouter usage rank, then snapshot order.
- **Open-source:** always the pinned required route, from `METERLESS_OPEN_MODEL` or the snapshot row marked `required`, regardless of score. The current selection is Gemma 4 31B Dense free through Nightshift's `openrouter/google/gemma-4-31b-it:free` route. Other open models can appear in the shortlist but never replace it. If the pinned route has no price snapshot or Nightshift doesn't offer it, the run stops for input before any paid call.
- **In the pack:** `candidate_shortlist` lists every snapshot model, with:
  - whether it's a Nightshift route;
  - its intelligence score, with source and date;
  - its market reference, labeled *market reference (OpenRouter, date)*;
  - its price per intelligence point (list price blended 3:1 input:output ÷ score), labeled with source and date;
  - why it was or wasn't selected.
- **Reference data stays separate from actual-route costs.** OpenRouter catalog rows may price a clearly labeled hypothetical serving table. Actual-route stage tables, switch points and model-stack recommendations use the applicable execution price snapshot and rubric checks; market prices never authorize paid dispatch.

**Decision pack.** Two ledgers, never summed:

- **Operating ledger by growth stage** (primary): monthly AI cost per feature, per candidate, at Prototype 50 · Launch 500 · Traction 5,000 · Scale 50,000 active users (editable, labeled assumed). Levers appear as separate lines, applied only when eligible: prompt caching, batch API and output reuse are labeled *projected (production setup)*; the output cap uses a measured re-run; the long-context cliff is a warning. AI cost per use is shown against revenue per use when given; above 100% raises a high-severity risk.
- **Build panel** (secondary): build approaches, expected build cost with an assumed rework multiplier, and checkpoints. A missing build input adds a question; it never stops the run.
- **Model stack** per feature and stage: the cheapest candidate that passes every critical rubric check; a higher-quality one only if it costs less than the switch threshold ($100/month default) more; never one that loses money per use while a qualified alternative doesn't. **Switch points**: the first stage where a cheaper candidate is projected to cost at least the threshold less and passes every critical check.
- Measured versus estimated tokens per feature, evidence gaps, risks, limitations, and the trace.

**Lever calculations.** The original standard-rate cost is the baseline. The calculator then uses both input and output usage from an accepted cap fixture/rerun, selects the applicable whole-request tariff, and chooses the cheapest supported cache/batch scenario. Combining provider discounts requires an exact `terms.lever_combinations` rule with supported status and a verified, dated citation; pairwise support does not imply three-way support. Long-context caching also needs explicit long-context cache-read/write rates. Missing required surcharge prices leave the decision total unknown and prevent cost-based qualification. Batch discounts text charges only. Output reuse recalculates paid volume and cache eligibility; its one-time fill uses effective request pricing, without assuming prompt-cache hits. Totals retain Decimal precision; displayed lines may differ from the displayed total by rounding.

Incremental calculator check: `python -m pytest -q tests/test_stage_economics.py tests/test_economics.py`. Synthetic [calculator regression artifacts](docs/evidence/m02-calculator-regressions.json) show the batch-plus-cap case at $1.1055 exact / $1.11 displayed. They are calculator fixtures, not real model or sponsor evidence. Selection and human approval of a real repaired configuration remain M10.

**Sample mode** runs steps 1–4 and 10 on bundled data with zero network calls: nothing is executed, no outputs exist, rubric checks don't run, switch points stay pending, the model stack says *requires live run*, and domain-risk review is reported as requiring live mode. Audio features are never sent to Nightshift in either mode; audio is priced from per-second conversions, labeled estimated.

Hard limits per run: 1 logical Planner, 1 logical Critic, ≤1 logical repair, ≤30 total inference attempts including every role/retry, ≤2 known pre-dispatch retries; spend reserved transactionally before every attempt and reconciled to measured usage-based cost. `retrospective_actuals` and holdout tasks remain unreadable before `frozen` (an attempt is logged `denied_sealed`); the v3.4 retrospective that used them is shelved (`scripts/compare_retrospective.py`).

## Sponsor technology

| Sponsor | Role in this project | Proof |
|---|---|---|
| Zetaris | Data layer: price snapshots for every candidate (S3-backed sources) and writeback of measured runs | `app/adapters/live_zetaris.py`; trace `zetaris_query` events with query IDs |
| Meterless H-MEM | The idea's memory: confirmed assumptions recalled at the start of a run; accepted model-stack decisions saved at the end | `app/engines/hmem/`; `tests/test_hmem_engine.py` |
| Meterless Nightshift | The router for every model call: Planner, all three candidates and the Critic; requested and resolved model logged per request | `app/adapters/live_nightshift.py`; trace `nightshift_request` and `run_feature` events |
| NVIDIA Nemotron | Ultra and Lightning remain candidates; a measured Nemotron-backed working feature and corroborated identity are needed for NVIDIA evidence | Trace `select_candidates` (chosen routes) and `run_feature` events (`model` per request) |
| Cursor | Used by Shrie for UI and Zetaris work | — |

No model grades the comparison. The Critic only flags issues and proposes one action, which the controller validates. It never uses a candidate's route when Nightshift offers another; when none is available, the trace and the pack's limitations say so.

## Build status

The offline suite has 483 passing tests covering contracts, Decimal economics, durable dispatch, source collection/publication, typed Zetaris reads, ingestion/outbox recovery, the controller loop, rubric checks, trace, CLI, sample adapters and the repeatable sample checker. Known correctness and integration gaps are tracked in the [gap review](docs/08-v4-Integration-Gap-Review.md) and [incremental implementation guide](docs/09-v4-Gap-Implementation-Guide.md). M07 local H-MEM integration passes; M08 live route/tariff verification and later memory influence remain open as of 25 October.

| Component | State |
|---|---|
| Contracts, economics, dispatch, sources/Zetaris, controller, rubric checks, trace, CLI, sample adapters | implemented with known gaps; 483 tests pass, 8 shelved retrospective tests skipped |
| Zetaris live adapter | typed pinned reads, preserved provenance, external ingestion/readback and durable outbox implemented; LocalStack component proof passes; applicable execution-tariff/model evidence remains pending |
| Nightshift live adapter | M08 partial: the earlier branch records real NVIDIA cloud responses for Ultra and Lightning; current discovery, receipt-aware adapter fixtures and read-only gate pass. Applicable execution tariffs, a third candidate response and the bounded live pack remain pending. See [M08 checks](docs/15-M08-Manual-Testing.md). |
| H-MEM bridge | M07 local reference PASS: pinned Node bridge, save/restart/recall/isolation/audit and blocked-network sample delegation; [manual checks](docs/14-M07-Manual-Testing.md). Decision influence remains M11. |
| Streamlit UI | in progress |
| Pricing snapshots | unverified placeholders; to be replaced with dated, cited snapshots |
| Retrospective comparison script | shelved in v4 |

## Limitations

- Economics are modeled estimates from entered assumptions and the rates in the price snapshots, not financial advice. Small samples throughout; no claim about a model's quality beyond the measured tasks.
- All prices are unverified placeholders until replaced with dated, cited snapshots; so are the intelligence scores and OpenRouter market references in the sample data.
- Audio is priced from per-second conversions, not measured; audio is never sent to a model.
- Prompt caching, batch API and output reuse are projections for a production setup, not measured in our runs.
- The self-host break-even is not shown: it needs a cited throughput figure for the selected open-model variant.
- Founder-impact evidence so far comes only from the founder's own ideas (self-evaluation).
- Build-approach costs are compared on rates; no build was executed on any platform.

## Pre-existing components

None. All code and data were created on or after 23 October 2026.
