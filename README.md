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

For a repeatable check of all three examples, run `python scripts/check_sample_examples.py`. The checker forces sample mode in copied requests, disables private dotenv loading, blocks Python sockets and Node network calls, and uses fresh databases and logs. It retains packs, traces and a `manifest.json` in a new temporary directory and prints its location. To retain them in a chosen location, pass `--output-dir <new-directory>`; existing directories are refused. A passing check establishes the offline baseline and local H-MEM delegation; live sponsor readiness needs later checks. See the [implementation plan](docs/08-v4-Implementation-Plan.md), [revised steps](docs/17-v4-Revised-Implementation-Steps.md) and [evidence ledger](docs/v4-release-checklist.md).

## Live mode

Requires Zetaris (Docker Desktop / WSL2) and Meterless Nightshift running locally; see the Participant Setup Guide. Fill `.env` from your Zetaris and Nightshift consoles (the NVIDIA key goes in Nightshift's Providers tab, never here), then:

```bash
python run.py --input input_examples/example_1.json --output result.json
```

Source setup (scripts in `scripts/`, details in the [evidence ledger](docs/v4-release-checklist.md)): `collect_sources.py` collects and validates the OpenRouter catalog, `prepare_source_bundle.py` builds a pinned bundle (add `--include-discovered` to register every priced Nightshift route), `register_sources.py` previews or applies LocalStack/S3 registration, and `check_zetaris_sources.py` reads typed rows and checks the evidence write/readback. These need no H-MEM or model completions. The collector retains raw and normalized data, exact hashes and explicit quarantine records. Catalog prices are labeled market references; only the Planner and Critic routes carry verified Nightshift execution profiles, and other candidates are projected only. A simple operator manual will replace the earlier per-milestone guides.

Use the generated schema 1.1 bindings file through `ZETARIS_BINDINGS_FILE`. Every source row is checked against its pinned envelope hash; the earlier unbound `LIMIT 50` query is no longer the application read path. Optional build-source failure leaves the operating comparison available. Result ingestion runs in a separate publisher process, and the application retains a durable evidence outbox when write/readback is unavailable. AWS/Windows validation and applicable provider tariffs/billing bounds remain separate acceptance work. Recorded component evidence is in the [evidence ledger](docs/v4-release-checklist.md).

Preflight for the Windows host: `scripts/preflight_windows.ps1` checks RAM, CPUs, disk, WSL2, Docker allocation and ports. With `-ZetarisUrl`/`-NightshiftUrl`, it validates the actual `SELECT 1` cell and model-discovery structure using the shared Python validators. Activate the project environment first, or pass `-PythonExecutable <path>`. Required SKIP/UNKNOWN or FAIL gives exit code 1. This is machine/connectivity evidence only; the revised PowerShell script still needs execution on Windows.

Live smoke test (diagnostic only, reads `.env`): `python scripts/smoke_live.py` checks Zetaris, Nightshift discovery and the H-MEM bridge separately. Paid diagnostic completions default to **disabled**. An explicit `--max-spend-usd <amount>` between $0 and $1, plus verified route prices/token bounds, allows one tiny completion each for the Planner (`METERLESS_MODEL`) and Critic (`METERLESS_CRITIC_MODEL`) routes through the same durable dispatcher; `--diagnostic-only` sends the same two requests without billing authorization and records receipts with no cost claim. It saves a redacted Markdown table, typed JSON readiness/accounting and HTTP traces under `logs/`; `--output-dir <directory>` chooses report storage and `--no-dotenv` disables private dotenv loading. The operation ledger defaults to `<output-dir>/smoke-operations.db`; `--operations-db <path>` selects an existing ledger and `--run-id <id>` supplies a durable idempotency key. Reusing a key never replays paid work. Exit code 0 requires all six diagnostic checks to pass; a required skip or missing check is non-success. Role-route diagnostics require explicit discovery/response identity and a response request ID. Passing diagnostics do not establish working-feature or end-to-end sponsor proof; model alias/receipt verification remains open (see the ledger).

Incremental trace/readiness check (offline fixtures, no paid requests): `python -m pytest -q tests/test_trace.py tests/test_smoke_live.py`. See [M03 evidence](docs/v4-release-checklist.md#m03--trace-evidence-and-truthful-readiness).

## Verify the implementation (Steps 0–8)

Three levels, from no accounts to a bounded live run. The step numbers are those of the [implementation plan](docs/08-v4-Implementation-Plan.md); counts are from 26 October and will grow as tests are added. Anything under `data/localstack/` and `logs/` is gitignored.

### Level 1: offline (no accounts, no network)

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
(cd app/engines/hmem/reference && npm ci)          # Node 20+; needed for the real H-MEM test
python -m pytest -q -rs                             # 539 passed, 8 skipped (the 8 are the shelved retrospective)
python scripts/check_sample_examples.py             # three PASS lines
```

Per step (`-rs` shows skips; a skipped H-MEM test means Step 7 is **not** confirmed):

| Step | Command | Expected |
|---|---|---|
| 0 Baseline | the two commands above | 539 passed; 3 examples PASS |
| 1 Contracts | `python -m pytest -q tests/test_v4_contracts.py` | 89 passed |
| 2 Cost levers | `python -m pytest -q tests/test_stage_economics.py tests/test_economics.py` | 75 passed |
| 3 Traces, readiness | `python -m pytest -q tests/test_trace.py tests/test_smoke_live.py` | 110 passed |
| 4 Spend, dispatch | `python -m pytest -q tests/test_dispatch_limits.py tests/test_controller_live_fake.py` | 96 passed |
| 5 Sources | `python -m pytest -q tests/test_source_manifest.py tests/test_source_registry.py tests/test_modality.py` | 64 passed |
| 6 Zetaris adapter | `python -m pytest -q tests/test_zetaris_adapter.py tests/test_source_ingest.py tests/test_openrouter_projection.py` | 29 passed |
| 7 H-MEM | `python -m pytest -q -rs tests/test_hmem_engine.py tests/test_sample_memory.py` | 5 passed, no skips |
| 8 Nightshift, candidates | `python -m pytest -q tests/test_nightshift_adapter.py tests/test_role_routes.py tests/test_candidate_selection.py tests/test_m08_gate.py` | 36 passed |

### Level 2: read-only live (no model completions)

Needs Zetaris running in Docker, a LocalStack container named `cost-optimizer-localstack` on the same Docker network (port 4566 published, your `LOCALSTACK_AUTH_TOKEN` set), Nightshift running, and `.env` filled in from `.env.example`. Starting Zetaris and LocalStack is not scripted here; follow the Participant Setup Guide. Run in this order, replacing `<...>` with each command's printed output:

```bash
python scripts/collect_sources.py --output-dir data/localstack/openrouter/catalog            # prints snapshot_dir
python scripts/discover_source_routes.py --output data/localstack/discovery.json            # free; no completion
python scripts/prepare_source_bundle.py --catalog <SNAPSHOT_DIR> --route-map data/source_examples/routes.selected.json \
    --discovery data/localstack/discovery.json --include-discovered --brief input_examples/example_3.json \
    --output-dir data/localstack/openrouter/bundles                                          # prints bundle_dir
python scripts/register_sources.py --bundle <BUNDLE_DIR> --storage data/source_examples/localstack.json   # dry run
python scripts/register_sources.py --bundle <BUNDLE_DIR> --storage data/source_examples/localstack.json --apply \
    --bindings-output data/localstack/bindings.json --report data/localstack/registration.json            # status pass
python scripts/check_zetaris_sources.py --bindings data/localstack/bindings.json \
    --catalog-id nvidia/nemotron-3-ultra-550b-a55b --round-trip --storage data/source_examples/localstack.json \
    --run-id verify-001 --output-dir data/localstack/verify-001                              # status pass, 0 completions
python scripts/check_m08_gate.py --bindings data/localstack/bindings.json --output data/localstack/gate.json
export ZETARIS_BINDINGS_FILE=$PWD/data/localstack/bindings.json
python scripts/check_openrouter_projection.py --input input_examples/example_3.json \
    --bindings data/localstack/bindings.json --output-dir data/localstack/preview-001        # needs_input, 0 dispatches
python scripts/smoke_live.py                                                                 # Zetaris, discovery, H-MEM
```

What to look for:

- **Steps 5 and 6:** registration `status: pass` with `current_pointer_updated: false`; the Zetaris check passes `SELECT 1`, a typed model read and the evidence write and readback, with `model_completions: 0`.
- **Steps 7 and 8:** the gate shows `ready_for_bounded_dispatch`, with the Planner and Critic routes at `billing_gate: pass` and most other routes `blocked`. Blocked is correct: those candidates are projected only. `smoke_live.py` reports H-MEM and discovery separately; a required SKIP is an incomplete result, not a pass.
- **Candidate selection:** open `preview-001/pack.json`. Each feature lists its own candidates, and an audio-out feature with no capable route shows a `candidates:<feature>` evidence gap.
- **Your Nightshift must offer** `nvidia/nemotron-3-ultra-550b-a55b` and `nvidia/nemotron-3.5-lightning-30b-a3b`, or the bundle step stops with "mapped route was not offered". Edit `routes.selected.json` to the Planner and Critic routes you have.
- **Warning:** the two curated profiles in `routes.selected.json` assume a free NVIDIA Developer Program key (verified $0 rate, prototyping only). If your Nightshift key is paid or different, write profiles from your own billing terms before any live run.

### Level 3: bounded live pack (optional; sends real, rate-limited requests)

Confirms Steps 4, 6 and 8 together: the Planner, Critic and candidates through the dispatcher, with the evidence round trip. Use a fresh run ID each time.

```bash
# 1. a request: copy input_examples/example_3.json, set a new "run_id", "sampling_profile": "validation",
#    "evaluation_approved": true and "max_spend_usd": "0.50" (save as data/localstack/r5/request.json)

# 2. start the evidence publisher with a throwaway token (never put it in .env)
export SOURCE_INGEST_TOKEN=$(python -c "import secrets;print(secrets.token_hex(16))") SOURCE_INGEST_URL=http://127.0.0.1:8766
python scripts/serve_source_ingest.py --storage data/source_examples/localstack.json \
    --bindings data/localstack/bindings.json --port 8766 &

# 3. run
SAMPLE_MODE=false ZETARIS_BINDINGS_FILE=$PWD/data/localstack/bindings.json RUNS_DB=$PWD/data/localstack/r5/runs.db \
METERLESS_NO_THINKING_ROLES=Planner,Critic METERLESS_NO_THINKING_MODELS=<route that returns empty_response> \
METERLESS_REQUEST_TIMEOUT_S=150 python run.py --input data/localstack/r5/request.json --output data/localstack/r5/pack.json

# 4. stop the publisher
pkill -f serve_source_ingest.py
```

Expected in `pack.json`: `status: complete`, `dispatch_count` about 6, `spend_usd` 0 on a free key, every `operations[].state` `completed` with the requested model equal to the resolved model, `unpublished_evidence_ids` empty, and any unproven candidate marked "projected only". Without the publisher the run ends `partial` with its evidence in the outbox; `python scripts/retry_evidence.py --runs-db <db> --run-id <id> --bindings <bindings>` replays it. The settings are explained in [docs/17](docs/17-v4-Revised-Implementation-Steps.md) §6. Set `METERLESS_NO_THINKING_MODELS` only for a route that returns `empty_response` with thinking on (Lightning did).

### What these checks do not confirm

Windows execution (the preflight script was never run), a second-machine clean clone, AWS/IAM access (only LocalStack was used), and sponsor `readiness`, which stays `not_verified` until `smoke_live.py` is run on the final setup. One sample per pair supports no model-quality claim.

## Interface

`run.py` is JSON in / JSON out. Input: `RunRequest` (see `app/contracts.py`): brief (idea, target user, 2–5 `ai_features`, `growth_stages`, optional build constraints), `evaluation_approved`, `max_spend_usd`, optional `human_reviews`. Examples: `input_examples/` (three briefs: `example_1` speech therapy with audio features, `example_2` AI-agent payments, `example_3` a synthetic writing assistant; every number labeled assumed). Output: `DecisionPack` with `status ∈ {complete, partial, needs_input, failed}` or a structured `RunError`. Exit codes: 0 valid result · 2 invalid input · 3 setup incomplete · 4 operational/duplicate. Trace: `logs/trace-<run_id>.jsonl` (organizer format, `model` per request, no invented confidence) plus readable `[INFO]` lines on stderr and one `final_result` JSON line on stdout.

Every pack and successful CLI `final_result` carries a separate typed `readiness` result. A completed sample pack has `readiness.scope: sponsor_integration` and `readiness.status: not_verified`; live packs also retain that status until `scripts/smoke_live.py` has been run on the final setup (the bounded live pack in the ledger is separate evidence). The same contract is available to the future UI. Numeric token usage, including nested reasoning counts, survives trace masking. HTTP attempts and terminal success/error events share an `operation_id`, with request/query IDs, adapter source hash, configuration reference and latency.

Current request/pack schema is **1.1**. An input marked `1.0`, or without a version, is normalized to `1.1` and receives the same validation. Full runs require 2–5 AI features, nonblank required text, unique feature/check/stage identifiers, finite non-negative costs and volumes, positive calls-per-use, valid fractions and an evaluation spend input between $0 and $25. Run/project IDs use letters, digits, dots, underscores and hyphens, starting with a letter or digit. Unexpected public fields are rejected before adapter setup instead of being silently discarded. Older invalid requests, including single-feature runs, must be corrected; migration does not bypass validation.

Both build fields (`brief.features_v1` and `brief.constraints`) can be omitted. Build costs then remain unknown and approaches are not ranked without a build scope. Value defaults and founder estimates receive per-field `assumed` provenance unless evidence is explicitly declared; nulls remain `unknown`, and metadata alone cannot promote an omitted default to verified. The new `brief.monthly_ai_budget_usd` (optional) and `brief.switch_threshold_usd` (default $100) survive request/pack export. The switch threshold feeds stage tables/model selection; the monthly ceiling is recorded with an explicit limitation until aggregate budget-fit analysis (R9).

Paid execution uses [the shared dispatcher](app/dispatch.py). Planner, candidates, Critic, repair and diagnostics all require explicit output limits (at most 1,024 tokens), a pinned route's verified USD-per-million rates and a cited `dispatch_policy` bounding prompt bytes, token overhead and completion tokens including hidden reasoning. Planner/Critic routes need their own billing profiles; `meterless/auto` cannot be priced safely. Missing/unverified rates or bounds produce a partial result and an evidence gap before paid dispatch. Sample placeholder data deliberately has no such policy. In live mode only routes with a verified profile are executed; the rest are projected only.

Every attempt transactionally claims money and a slot in SQLite before entering the adapter. Charges are computed from measured usage at the applicable full input/output tariff; production cache/batch discounts are not assumed. Packs and CLI results distinguish known `spend_usd` from unresolved `reserved_spend_usd`; packs also expose `operations`, retry counts and selected samples. Unknown outcomes retain reservations and stop further spending. A usage/billing-bound overrun records the full known charge, even above the approved ceiling, and stops; the software cannot undo a runtime's violated limit. Only known pre-dispatch connect/connect-timeout/pool failures may retry, with another receipt/reservation/slot. Read/write timeouts, HTTP errors, malformed responses, missing usage and unpriced resolved identities are never automatically replayed. Correlation IDs do not imply provider idempotency. Existing run IDs are refused on restart; unresolved operations require external reconciliation, not a new automatic attempt.

The stricter [v4 call-budget policy](Planning/07-Realignment-v4.md) caps **all inference attempts, across roles and retries, at 30**. There is one logical Planner, one Critic and at most one repair, plus at most two safe retries globally. The default `sampling_profile: production` uses two samples per executable pair when the dispatch slots fit; four features need at most 29 slots including reserved repair/retry slots, while five use one sample. `sampling_profile: validation` explicitly selects one sample per pair for incremental checks. Spend is checked before each attempt; a selected sampling count does not guarantee the whole run fits the monetary budget.

For an incremental Ultra + Lightning comparison, a validation request may set `candidate_tiers: ["frontier", "mid_tier"]`. `scripts/check_m08_gate.py` checks the gate without sending a completion, and the pack records which tier is pending. Production requests keep all three tiers.

Incremental dispatch check (offline synthetic billing/HTTP fixtures): `python -m pytest -q tests/test_dispatch_limits.py tests/test_controller_live_fake.py`. See [M04 evidence](docs/v4-release-checklist.md#m04--bounded-dispatch-spend-and-restart-safety).

Incremental contract check: `python -m pytest -q tests/test_v4_contracts.py`. See [M01 evidence](docs/v4-release-checklist.md#m01--input-contracts-and-founder-controls) for the tested scope and remaining work.

## Architecture

v4 (`Planning/07-Realignment-v4.md`). The founder describes an AI SaaS idea and its 2–5 AI features; the agent measures what can be measured and labels the rest.

```
Founder idea + AI features ─► Controller (allowlist by state, call caps, spend reservation, SQLite checkpoints)
  1  Recall     H-MEM (Meterless)         earlier runs and confirmed assumptions for this idea
  2  Retrieve   Analyst ◄─ Zetaris         dated prices (input, output, cache, batch, audio, long-context),
                                           intelligence scores, OpenRouter market reference
  3  Select     Controller ◄─ Nightshift   per feature, candidates from the Nightshift routes (GET /v1/models,
                                           before any paid call) filtered by modality, any lab, no pin;
                                           shared candidate/Critic routes are disclosed
  4  Estimate   Analyst                    4/3 rule per feature × candidate, labeled estimated
     ── approval gate (evaluation_approved, max_spend_usd) ──
  5  Plan       Planner ◄─ Nightshift      domain risks only, labeled model-generated, not advice
  6  Execute    Analyst ◄─ Nightshift      each feature's example input on each candidate with a verified profile
                                           (others projected only), 2 samples (1 if the cap needs it);
                                           measured tokens from API usage fields (output includes reasoning)
  7  Check      rubric checks              deterministic pass/fail (max_words, required_json_fields,
                                           forbidden_terms, regex) + human review; no model grades
  8  Critique   Critic ◄─ Nightshift       flags only: unsupported claims, token gaps, over-long output;
                                           proposes one action; controller validates it
  9  Repair     Analyst ◄─ Nightshift      at most one: re-run one feature × model with an output cap
 10  Project    economics (Decimal)        stage cost tables, levers, switch points, model stack
     └─ frozen ─► complete ─► DecisionPack ─► H-MEM (accepted decisions)
```

**Candidate shortlist.** Candidates are chosen **per feature**, from any lab, not pinned. A model is eligible for a feature when it is a Nightshift route (live mode), has a reference price in the pinned source, and its catalog entry lists the modalities the feature needs (text, audio in or out, image in or out). A catalog entry that carries no modality data stays eligible and is labeled unknown, never assumed text-only. A feature that no model covers gets no candidates and an evidence gap. Sample mode says the route check needs live mode.

- **Tiers (frontier, mid-tier, open-source):** a tier curated in the route map wins; otherwise open-weights models (the catalog lists a Hugging Face ID; a signal, not a licence finding) are open-source and the rest split by reference price, upper half frontier and lower half mid-tier. This is a price-rank proxy, labeled as such.
- **One candidate per tier, per feature:** a route with a verified rate and dispatch policy ranks first, because it can be measured; then intelligence score, OpenRouter usage rank and snapshot order. Routes without a verified policy are projected from the catalog reference and not executed: they get estimated tokens, unknown quality, a `projected only` reason on every run row and an evidence gap, and they are never recommended. Only the Planner and Critic routes stop a run when unproven. If every chosen candidate is projected only, the run ends `partial`.
- **Optional override:** `METERLESS_OPEN_MODEL` forces the open-source candidate. It is not required. If set to a route that has no price row or that Nightshift doesn't offer, the run stops for input before any paid call.
- **In the pack:** `candidate_shortlist` lists every snapshot model, with:
  - whether it's a Nightshift route;
  - its intelligence score, with source and date;
  - its market reference, labeled *market reference (OpenRouter, date)*;
  - its price per intelligence point (list price blended 3:1 input:output ÷ score), labeled with source and date;
  - which features it was chosen for, and why it was or wasn't selected.
- **Reference data stays separate from actual-route costs.** OpenRouter catalog rows may price a clearly labeled hypothetical serving table. Actual-route stage tables, switch points and model-stack recommendations use the applicable execution price snapshot and rubric checks; market prices never authorize paid dispatch.

**Decision pack.** Two ledgers, never summed:

- **Operating ledger by growth stage** (primary): monthly AI cost per feature, per candidate, at Prototype 50 · Launch 500 · Traction 5,000 · Scale 50,000 active users (editable, labeled assumed). Levers appear as separate lines, applied only when eligible: prompt caching, batch API and output reuse are labeled *projected (production setup)*; the output cap uses a measured re-run; the long-context cliff is a warning. AI cost per use is shown against revenue per use when given; above 100% raises a high-severity risk.
- **Build panel** (secondary): build approaches, expected build cost with an assumed rework multiplier, and checkpoints. A missing build input adds a question; it never stops the run.
- **Model stack** per feature and stage: the cheapest candidate that passes every critical rubric check; a higher-quality one only if it costs less than the switch threshold ($100/month default) more; never one that loses money per use while a qualified alternative doesn't. **Switch points**: the first stage where a cheaper candidate is projected to cost at least the threshold less and passes every critical check.
- Measured versus estimated tokens per feature, evidence gaps, risks, limitations, and the trace.

**Lever calculations.** The original standard-rate cost is the baseline. The calculator then uses both input and output usage from an accepted cap fixture/rerun, selects the applicable whole-request tariff, and chooses the cheapest supported cache/batch scenario. Combining provider discounts requires an exact `terms.lever_combinations` rule with supported status and a verified, dated citation; pairwise support does not imply three-way support. Long-context caching also needs explicit long-context cache-read/write rates. Missing required surcharge prices leave the decision total unknown and prevent cost-based qualification. Batch discounts text charges only. Output reuse recalculates paid volume and cache eligibility; its one-time fill uses effective request pricing, without assuming prompt-cache hits. Totals retain Decimal precision; displayed lines may differ from the displayed total by rounding.

Incremental calculator check: `python -m pytest -q tests/test_stage_economics.py tests/test_economics.py`. Synthetic calculator regression artifacts show the batch-plus-cap case at $1.1055 exact / $1.11 displayed. They are calculator fixtures, not real model or sponsor evidence. Selection and human approval of a real repaired configuration remain open (R7).

**Sample mode** runs steps 1–4 and 10 on bundled data with zero network calls: nothing is executed, no outputs exist, rubric checks don't run, switch points stay pending, the model stack says *requires live run*, and domain-risk review is reported as requiring live mode. Audio features are never sent to Nightshift in either mode; audio is priced from per-second conversions, labeled estimated.

Hard limits per run: 1 logical Planner, 1 logical Critic, ≤1 logical repair, ≤30 total inference attempts including every role/retry, ≤2 known pre-dispatch retries; spend reserved transactionally before every attempt and reconciled to measured usage-based cost. `retrospective_actuals` and holdout tasks remain unreadable before `frozen` (an attempt is logged `denied_sealed`); the v3.4 retrospective that used them is shelved (`scripts/compare_retrospective.py`).

## Code map

| Path | Role |
|---|---|
| `run.py` | Only entry point: JSON in, JSON out |
| `app/controller.py` | Run state allowlist, call caps, spend reservation, candidate selection, Planner/Analyst/Critic sequence |
| `app/contracts.py`, `app/source_contracts.py` | Every data structure, including modality fields |
| `app/economics.py`, `app/rubric.py` | Decimal cost engine; deterministic rubric checks |
| `app/dispatch.py` | Durable spend gate: reserve, call, reconcile |
| `app/source_registry.py`, `app/source_snapshots.py` | Pinned source bundles and catalog normalization |
| `app/adapters/` | `sample.py` (offline), `live_zetaris.py`, `live_nightshift.py`, `validation.py` |
| `app/engines/hmem/` | Meterless H-MEM bridge |
| `app/trace.py` | JSONL trace in the organizer's format |
| `scripts/` | Source collection, registration, gates, smoke test, evidence publisher |
| `tests/` | Offline suite |

## Sponsor technology

| Sponsor | Role in this project | Proof |
|---|---|---|
| Zetaris | Data layer: price snapshots for every candidate (S3-backed sources) and writeback of measured runs | `app/adapters/live_zetaris.py`; trace `zetaris_query` events with query IDs |
| Meterless H-MEM | The idea's memory: confirmed assumptions recalled at the start of a run; accepted model-stack decisions saved at the end | `app/engines/hmem/`; `tests/test_hmem_engine.py` |
| Meterless Nightshift | The router for every model call: Planner, per-feature candidates and the Critic; requested and resolved model logged per request | `app/adapters/live_nightshift.py`; trace `nightshift_request` and `run_feature` events |
| NVIDIA Nemotron | Planner and Critic run on Nemotron through Nightshift (`07` v4.3); candidates are not tied to a lab. Corroborated resolved identity per request is the NVIDIA evidence | Trace `select_candidates` (chosen routes) and `run_feature` events (`model` per request) |
| Cursor | Used by Shrie for UI and Zetaris work | — |

No model grades the comparison. The Critic only flags issues and proposes one action, which the controller validates. The Critic is independent of the candidates unless one of them runs on the same route or lab; then the trace and the pack's limitations disclose the shared lab.

## Build status

The offline suite covers contracts, Decimal economics, durable dispatch, source collection/publication, typed Zetaris reads, ingestion/outbox recovery, the controller loop, rubric checks, trace, CLI, sample adapters and the repeatable sample checker. The current plan, findings and remaining work are in [docs/08](docs/08-v4-Implementation-Plan.md) and [docs/17](docs/17-v4-Revised-Implementation-Steps.md), with evidence in the [ledger](docs/v4-release-checklist.md). As of 26 October the suite has 538 passing tests (8 shelved retrospective tests skipped); local H-MEM, the Planner/Critic role routes and a clean bounded live pack pass, and memory influence on a later run, human-review binding, stage totals and the UI remain open.

| Component | State |
|---|---|
| Contracts, economics, dispatch, sources/Zetaris, controller, rubric checks, trace, CLI, sample adapters | implemented with known gaps; 538 tests pass, 8 shelved retrospective tests skipped |
| Zetaris live adapter | typed pinned reads, preserved provenance, external ingestion/readback and durable outbox implemented; LocalStack component proof passes; applicable execution-tariff/model evidence remains pending |
| Nightshift live adapter | The Planner (Lightning) and Critic (Ultra) calls go through the spend-checking Dispatcher on a free NVIDIA Developer Program key, and the model that actually answered is logged; a clean bounded pack (`r5-live-20261026-113150-e`, 6 dispatches, $0) is recorded in the ledger. Only those two routes have verified execution profiles; other candidates are projected only. |
| H-MEM bridge | M07 local reference PASS: pinned Node bridge, save/restart/recall/isolation/audit and blocked-network sample delegation (checks in the ledger). Decision influence remains open (R8). |
| Streamlit UI | not started (`streamlit_app.py` does not exist yet; R10) |
| Pricing snapshots | sample mode uses unverified placeholders; live mode reads a dated OpenRouter catalog reference (market reference only) plus verified $0 profiles for the two role routes |
| Retrospective comparison script | shelved in v4 |

## Limitations

- Economics are modeled estimates from entered assumptions and the rates in the price snapshots, not financial advice. Small samples throughout; no claim about a model's quality beyond the measured tasks.
- Sample-mode prices, intelligence scores and market references are unverified placeholders. Live catalog prices are dated market references, not billing evidence; the two verified $0 profiles assume a free NVIDIA Developer Program key and are for prototyping only.
- Audio is priced from per-second conversions, not measured; audio and image inputs are never sent to a model. Image feature costs are unknown, not zero.
- Prompt caching, batch API and output reuse are projections for a production setup, not measured in our runs.
- The self-host break-even is not shown: it needs a cited throughput figure for the selected open-model variant.
- Founder-impact evidence so far comes only from the founder's own ideas (self-evaluation).
- Build-approach costs are compared on rates; no build was executed on any platform.

## Pre-existing components

None. All code and data were created on or after 23 October 2026.
