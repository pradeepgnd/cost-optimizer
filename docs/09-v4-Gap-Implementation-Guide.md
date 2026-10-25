# v4 gap implementation guide

Created October 25, 2026; revised for priority-based, incremental testing. **M00–M04 are complete for their recorded scopes**. **M05–M06 now have implemented pipelines and passing local source-component checks; overall acceptance remains partial** for applicable execution tariffs, remaining source coverage and later measured-model evidence. M07–M14 remain pending. Follow the [Steps 5–6 manual tests](12-M05-M06-Manual-Testing.md) and [portable source evidence](m05-m06-source-checks.json). Results are also recorded in the [evidence ledger](evidence/v4-release-checklist.md). M03's Windows preflight execution remains unverified.

**Objective:** close all 16 findings in the [integration gap review](08-v4-Integration-Gap-Review.md), then demonstrate a reproducible founder workflow using Zetaris, Nightshift, Nemotron and the real H-MEM engine.

The authoritative product specification remains [07-Realignment-v4.md](../Planning/07-Realignment-v4.md), version 4.1. Integration references are the supplied **Participant Setup Guide**, updated October 21, 2026: Zetaris pp. 5–11 and 22; Meterless Engines pp. 12–15; Nightshift/Nemotron pp. 16–20; setup verification pp. 23–24. New contract names, file names and policies in this guide are proposed implementation choices, not existing APIs or sponsor endpoints.

## Priorities and incremental delivery order

**P0 — Correctness and execution safeguards:** fix these first, without requiring sponsor accounts. **P1 — Required integrations and decision evidence:** prove components separately, then connect them. **P2 — Complete founder experience and release:** required for the final v4 deliverable, after the CLI workflow is trustworthy. P2 does not mean optional. Self-host break-even and hosted deployment remain stretch items.

The milestone number matches its implementation step below. Every milestone must leave the existing sample workflow usable or provide an explicit setup/input outcome. Introduce only the contract changes required for the current milestone; do not wait for a complete redesign before testing.

| Milestone | Priority | Deliverable you can test immediately afterward | Findings | Prerequisites | Test environment |
|---|---|---|---|---|---|
| M00 | P0 | Reproducible baseline and three sample packs | F16; inventory F01/F04 | — | Offline |
| M01 | P0 | Validated operating-only input with preserved controls | F11 | M00 | Offline |
| M02 | P0 | Correct combined-lever costs; no negative monthly totals | F08 | M01 | Offline calculator fixtures |
| M03 | P0 | Usage-preserving traces and honest readiness results | F15 | M00 | Offline HTTP/engine fixtures |
| M04 | P0 | Bounded calls, spend and timeout recovery | F10 | M01, M03 | Offline scripted inference |
| M05 | P1 | Versioned real-model price data and repeatable registration | F04 | M01 | Offline manifest; live registration |
| M06 | P1 | Real Zetaris reads and an evidence write/read round trip | F01 | M03, M05 | Isolated Zetaris; no model calls |
| M07 | P1 | Real H-MEM save/restart/recall and offline adapter | F02 | M01, M03 | Local pinned engine; no providers |
| M08 | P1 | Identified Nightshift candidates and first small live CLI pack | F03 | M02–M07 | Nightshift + Zetaris + H-MEM |
| M09 | P1 | Validated task planning and grounded flags-only critique | F06, F13 | M08 | Offline scripted loop, then live |
| M10 | P1 | Output-bound human review and effective repair results | F09, F14 | M02, M04, M09 | Saved/scripted samples, then live |
| M11 | P1 | Accepted memory changes a later decision | F07 | M06, M07, M10 | Local engine + persisted evidence |
| M12 | P2 | Stack totals, editable switch threshold, revenue and margin | F11, F12 | M02, M10 | Offline stage fixtures |
| M13 | P2 | Form, results, chart, review and export | F05 | M09–M12 | Sample UI, then live UI |
| M14 | P2 | Clean-clone rehearsal and release evidence | F16; final F01–F15 verification | M00–M13 | Second-machine sample/live |

Executed results and artifact locations are tracked in the [milestone evidence ledger](evidence/v4-release-checklist.md); the table above describes delivery order rather than completion status.

Useful stopping points are **M02** (calculator correctness), **M04** (safe scripted execution), **M06** (real data path), **M07** (real engine), **M08** (first small live pack), **M10** (reviewed repair), and **M13** (complete user flow). Do not wait until M14 to discover whether the integrations work.

## How to test each increment

1. Implement one milestone, including its focused regression tests. Reproduce the relevant old defect before fixing it when practical.
2. Run the milestone's commands below, inspect the stated result and retain its evidence. Commands naming new test files are **planned deliverables of that milestone**, not files that already exist. A missing test file, zero selected tests or a skipped required integration test is not a pass. M00 records known baseline skips; those skips cannot close the corresponding functional milestone.
3. Rerun the existing sample regression suite after changes to shared contracts/controller code. Before each implementation commit, run `python -m pytest -q` as required by the project instructions. Use the configured virtual environment; `python` below assumes it is activated.
4. Keep tests isolated: temporary databases, temporary log/output directories, fixed versioned fixtures and new run IDs for new evaluations. Never delete a real run database to make a rerun pass. Repeating the same ID should exercise duplicate protection.
5. Use scripted inference and captured HTTP fixtures for repeatable regression tests. Mark all such evidence as test fixtures. Actual sponsor PASS requires the separate live acceptance action in that milestone.
6. Test M05, M06 and M07 independently; a missing Nightshift runtime must not prevent a Zetaris-only or local-engine test. Preserve the all-components smoke script for M08 onward.
7. Save `milestone, revision, command, environment, expected result, actual result, artifact paths, status` in the evidence ledger. Status is `pending`, `pass`, `fail` or `blocked`; record blockers without marking the feature complete. Proceed with independent milestones when their prerequisites are satisfied.

Continue only after the milestone’s acceptance checks pass and its evidence is recorded. Failed findings remain open; independent milestones may continue when their prerequisites are satisfied.

The live checks consume bounded model calls only where explicitly stated. Full-sized live runs are reserved for M14. Completion of a partial pack or exit code 0 alone does not demonstrate a milestone passed; inspect its required fields and evidence.

## Step 0 — Establish the baseline and recover earlier work

**Files:** [gap review](08-v4-Integration-Gap-Review.md), [README](../README.md), [CLAUDE.md](../CLAUDE.md), existing local traces, Git history.

1. Record the working revision and existing uncommitted changes. Preserve unrelated changes.
2. Run `python -m pytest -q` in the configured virtual environment. The review baseline was 100 passed and 9 skipped; record current results rather than assuming those numbers remain valid.
3. Locate the earlier Zetaris mapping/registration/writeback implementation associated with the successful local traces. Inspect history or obtain the relevant teammate's changes; compare them with current contracts before restoring them. Logs alone cannot reconstruct that code.
4. Update contributor instructions to identify `07` as authoritative and distinguish shelved retrospective work from the active workflow.
5. Start an evidence ledger, proposed path `docs/evidence/v4-release-checklist.md`, with finding ID, milestone, revision, test/command, environment, expected/actual result and artifact location. Leave results pending until executed.

**Acceptance:** a reproducible baseline and an explicit list of reusable integration changes; no earlier trace is presented as proof of the current revision.

**M00 incremental check:**

```bash
python -m pytest -q
python -m pytest -q tests/test_controller_sample.py tests/test_sample_data.py
python scripts/check_sample_examples.py
```

The implemented [sample checker](../scripts/check_sample_examples.py) runs the three CLI examples with forced sample mode, isolated databases/logs, dotenv loading disabled and Python sockets blocked. It preserves source inputs and saves copied requests, packs, traces and a manifest in a fresh temporary directory; it prints the path. Run it after shared-core changes. Pass `--output-dir <new-directory>` to retain artifacts at a chosen location; existing directories are refused. Inspect SAMPLE/OFFLINE labels, estimated stage rows, zero executed samples and no fabricated quality. M00 results and known skips are recorded in the [evidence ledger](evidence/v4-release-checklist.md); recoverable integration code is documented in the [history inventory](evidence/m00-integration-inventory.md).

## Step 1 — Complete the contracts before adapting consumers

**Files:** [contracts.py](../app/contracts.py), [controller.py](../app/controller.py), input examples and contract consumers.

1. Make the operating workflow valid without build constraints or `features_v1`. Use an empty/unknown build panel when omitted; do not invent verified build assumptions.
2. Validate 2–5 founder AI features, non-empty required text, unique feature IDs, unique stage names and unique check IDs within each feature. Separate low-level single-feature test fixtures from full founder-request validation where necessary.
3. Require finite, non-negative users, usage, prices, tokens and budget values; positive calls-per-use and cache TTL; fractions/discounts within `[0, 1]`; and `0 <= max_spend_usd <= 25`. Zero volume is valid. Reject negative and non-finite numeric values before calculation.
4. Add typed `monthly_ai_budget_usd` and `switch_threshold_usd` controls, keeping the production monthly ceiling separate from the evaluation spend ceiling. Default the switch threshold to $100 and carry both values into the pack.
5. Record `assumed` provenance for each injected default. Mark founder-entered estimates as estimates; do not automatically mark them verified.
6. Limit this increment to the public-input changes above. Introduce immutable review/configuration references in M10, memory comparison fields in M11 and aggregate result fields in M12 alongside their consumers and tests. Reuse existing `SourceRef` and evidence-status types.
7. Reject unknown public input controls or explicitly migrate them. Version schema changes and update all three examples; document any compatibility conversion for older inputs.

**Acceptance tests:** an operating-only brief succeeds; missing required founder fields fail clearly; negative/non-finite values and duplicate IDs fail; zeros work; budget/threshold edits survive parsing and serialization. Defaults are visibly assumed. Existing examples migrate without silently dropping data.

**M01 incremental check:**

```bash
python -m pytest -q tests/test_v4_contracts.py
python -m pytest -q tests/test_controller_sample.py tests/test_sample_data.py
```

The implemented [contract tests](../tests/test_v4_contracts.py) cover operating-only input, negative/non-finite values, duplicate IDs, unexpected fields, assumed defaults and round-tripped budget/threshold controls. Full-request fixtures use 2–5 features; calculator fixtures may use one. Invalid CLI input returns a structured error before adapter setup. Schema `1.0`/unversioned requests normalize to `1.1` under the same rules. Both controls appear in the exported pack; the switch threshold is already passed into the existing projection, while aggregate monthly budget-fit analysis remains M12. See [M01 results](evidence/v4-release-checklist.md#m01--input-contracts-and-founder-controls) for commands, regenerated examples and limitations.

## Step 2 — Recompute costs under composed levers

**Files:** [economics.py](../app/economics.py), `ModelPricingTerms` and stage-row contracts; [test_stage_economics.py](../tests/test_stage_economics.py).

1. Implement a pure calculation over explicitly supplied effective tokens and tariff inputs. Use accepted-cap fixtures now, without waiting for the repair workflow. Step 10 will connect selected real repair evidence to the same function. Preserve completion/reasoning semantics and full Decimal precision.
2. Evaluate whole-request long-context tariffs against that effective input. If an applicable required rate is unknown, keep the decision total unknown; an optional lower-bound display must not qualify as a known cheap alternative.
3. Apply provider-supported cache-read/write accounting and batch pricing to the effective request. Store explicit compatibility evidence for combining levers; do not assume all provider discounts stack. Unsupported combinations should appear as separate scenarios or be marked ineligible.
4. Apply retry volume consistently and output reuse to the resulting paid-call volume/cost. Keep one-time output-cache fill outside monthly totals. Disclose the assumed traffic distribution used for cache TTL projections.
5. Compute each displayed lever delta as the difference between consecutive valid scenarios. Verify gross plus exact deltas equals the effective total. Do not independently subtract a full-rate output-cap delta after discounting its original output with batch.
6. Keep production caching/batch/reuse labeled projected, and output caps labeled measured reruns. Round only presentation values.

**Regression fixture:** 1,000 calls/month, 10% retries, 1 input token, original output 1,000, accepted capped output 100, $10/$20 per million input/output, 50% batch, no other lever. Effective cost is `1100 × (1×10 + 100×20) / 1,000,000 × 0.5 = $1.1055`, displayed **$1.11**. The reviewed implementation produced **−$8.79**.

**Acceptance tests:** batch + cap fixture above; cache writes/reads + batch; long context + cap; incompatible discounts; missing surcharge prices; zero use; near-threshold precision. Negative effective costs must fail calculation validation rather than be clamped to zero.

**M02 incremental check:**

```bash
python -m pytest -q tests/test_stage_economics.py tests/test_economics.py
```

Implemented and tested: batch + cap returns $1.1055 exact / $1.11 displayed; required unknown surcharge prices cannot qualify a cheaper model, including after serialization. Accepted-cap fixtures recompute both input/output usage and long-context eligibility. Caching/batch stacking requires cited exact compatibility rules; output reuse rechecks paid volume and TTL eligibility, with fill kept separate. Negative/non-finite costs fail validation. See [calculator fixtures](evidence/m02-calculator-regressions.json) and [M02 evidence](evidence/v4-release-checklist.md#m02--composed-cost-levers). These are synthetic calculator inputs; actual repaired-configuration selection/quality remains M10, and real provider source verification remains M05–M06.

## Step 3 — Preserve evidence and make readiness checks meaningful

**Files:** [trace.py](../app/trace.py), [smoke_live.py](../scripts/smoke_live.py), [preflight_windows.ps1](../scripts/preflight_windows.ps1), both live adapters.

1. Refine secret-field matching so authorization/runtime credentials are redacted while numeric usage fields remain intact. Verify nested `completion_tokens_details.reasoning_tokens` survives.
2. Emit an attempt event before each request and a corresponding success/failure event with the same operation ID. Include requested/resolved model, query/request ID, revision/configuration reference, latency and usage when available.
3. Validate the actual `SELECT 1` cell value, not HTTP status alone. Validate discovery structure and require corroborated Nemotron identity for the Nemotron feature check.
4. Make a required SKIP produce an incomplete/non-ready outcome and non-success exit status. Keep optional checks visibly optional.
5. Parse H-MEM self-test output as JSON and inspect `status`; do not rely on spaces in the serialized JSON string.
6. Add one typed readiness result consumed by CLI/UI so a pack's completion status cannot be mistaken for sponsor readiness.

**Acceptance tests:** HTTP 200 with a SQL error or wrong cell fails; empty model discovery fails; missing required setup is not green; numeric usage survives masking; representative secrets remain redacted; failed attempts retain correlation IDs.

**M03 incremental check:**

```bash
python -m pytest -q tests/test_trace.py tests/test_smoke_live.py
```

Implemented and tested: **89 focused tests** verify numeric and nested reasoning usage, redacted file/stderr/final output, correlated attempt/terminal HTTP events (including timeout, HTTP, parse and semantic failures), strict SQL cell/discovery validation, explicit discovery/response Nemotron identity and response request IDs, required-skip exit behavior, JSON H-MEM self-tests, and typed readiness separate from pack completion. The full offline suite has **303 passing tests and 9 known skips**; all three examples were regenerated and pass the guarded sample checker. See [M03 evidence](evidence/v4-release-checklist.md#m03--trace-evidence-and-truthful-readiness) and [portable diagnostic fixtures](evidence/m03-diagnostic-regressions.json).

Scope: fixtures and an unconfigured, network-blocked diagnostic only. Shared validators are used by Windows preflight, but PowerShell is unavailable on the current host and the revised script has not been executed on Windows. Real response mappings/read-writeback remain M06, engine persistence/offline delegation remains M07, model receipts and a working Nemotron feature remain M08, and UI consumption remains M13. Pack sponsor readiness stays `not_verified` until those required proofs exist. M04 dispatch safeguards are implemented below.

## Step 4 — Enforce spend, dispatch and restart limits

**Files:** [dispatch.py](../app/dispatch.py): shared `Budget`, `Checkpoints`, `Dispatcher`; [controller.py](../app/controller.py): `_call`, `_execute`; [live_nightshift.py](../app/adapters/live_nightshift.py); [contracts.py](../app/contracts.py); [smoke_live.py](../scripts/smoke_live.py).

1. Use one dispatch wrapper for Planner, candidates, Critic and the repair. Give every paid request a validated output limit and a conservative reservation based on bounded prompt/output size and the correct route's rates. Include hidden reasoning within the runtime's confirmed completion-token limit semantics.
2. When required billing rates or trustworthy token bounds are unavailable, stop paid execution with an evidence gap. A small fixed reservation is not a demonstrated worst-case cost bound.
3. Reserve before dispatch and reconcile all roles to measured usage. Keep unresolved charges reserved; if an actual charge exceeds its reservation, record it and stop further spending rather than continuing with an understated total.
4. Persist an operation record before dispatch, then its completion/unknown state, provider correlation ID, reservation and measured charge. Use transactional claims so a restart cannot dispatch an unresolved operation again.
5. Classify failures. Retry only when dispatch is known not to have happened, or supported provider idempotency/reconciliation proves it safe. Do not assume a custom request ID makes completions idempotent. Read timeouts after dispatch and malformed successful responses are potentially charged outcomes.
6. Count and reserve each retry. Keep the global two-retry limit, one logical Planner, one logical Critic and at most one logical repair. The adopted policy is **at most 30 total inference attempts including retries**, documented in `07` and the README. Each safe transport retry consumes another reservation and dispatch slot.
7. Plan sample count before calls. Under that policy, reserve two retry slots and one repair slot: four features can use two samples (`24 + 1 Planner + 1 Critic + 1 repair + 2 retries = 29`); five features must reduce sampling to fit. Report the selected sample count.
8. Add a validated one-sample-per-pair test profile, with default production sampling unchanged when the budget fits. Apply the same dispatch wrapper and a separate bounded spend allowance to diagnostic completions; the smoke script must not bypass these safeguards.

**Acceptance tests:** over-$25 input fails; every role reconciles; budget exhaustion stops before dispatch; an ambiguous timeout is dispatched once and returned as unknown/partial; a safe retry consumes another reservation and slot; duplicate submission/restart causes no duplicate paid request.

**M04 incremental check:**

```bash
python -m pytest -q tests/test_dispatch_limits.py
python -m pytest -q tests/test_controller_live_fake.py
```

Implemented and tested: **67 dispatch tests** and **20 controller fake tests**, included in **183 focused dispatch/controller/smoke/trace tests**. The full suite passes **377 tests with 9 known skips**. Tests verify transactional reservation visibility, missing bounds/rates and zero-budget refusal, all-role reconciliation, unknown/held outcomes, exact applicable long-context tariffs, known overrun accounting, safe retries and global caps, duplicate/crash restart refusal, concurrent SQLite claims, sampling profiles, adapter/receipt correlation, and separate diagnostic allowances. Sample outputs were regenerated and all three pass with zero dispatches/reservations. See [M04 evidence](evidence/v4-release-checklist.md#m04--bounded-dispatch-spend-and-restart-safety) and [portable synthetic receipts](evidence/m04-dispatch-regressions.json).

Live execution requires real cited `ModelProfile.dispatch_policy` and rate/terms evidence for the pinned Planner, Critic and candidates; see [data contracts](../data/README.md). A founder estimate, 4/3 rule or fixed five-cent reservation cannot provide these bounds. The current sample prices/policies cannot authorize live dispatch. The runtime must confirm completion limits include hidden reasoning and the input/output tariff covers all billed categories/fees. Until this evidence is collected in M05–M08, live execution stops with a partial result and an evidence gap.

Unknown outcomes are retained for external reconciliation; restart does not automatically resume or replay them. Software records a runtime's known bound overrun and stops subsequent spending, but cannot undo an already incurred charge. Actual provider/reasoning-limit verification remains M08, Windows/second-machine execution remains unverified, and the real H-MEM test is still skipped. No model calls or external writes were made for M04. The next implementation step is **M05 / Step 5**.

## Step 5 — Prepare source snapshots and repeatable registration

**Files:** [source contracts](../app/source_contracts.py), [collector/bundle logic](../app/source_snapshots.py), [publisher/registration](../app/source_registry.py), [collector CLI](../scripts/collect_sources.py), [bundle CLI](../scripts/prepare_source_bundle.py), [registration CLI](../scripts/register_sources.py), [data guide](../data/README.md).

**Collection options:** the [OpenRouter source comparison](10-OpenRouter-Source-Options.md) recommends automated API collection into immutable S3 snapshots first, with direct Zetaris REST federation as an independent experiment. Installed REST connector classes and driver-to-OpenRouter HTTPS access have been observed; an actual SQL REST-table query remains unproven. Preserve catalog-reference versus verified-tariff semantics, and address the current 50-row model-query bound before using a full catalog. This exploration does not complete M05/M06.

1. Obtain actual route discovery and pin the priced frontier, mid-tier and Nemotron variants. Record route, resolved model identity, provider/lab, price-record ID and snapshot version in one mapping. The initial NVIDIA candidate is **Nemotron 3.5 Lightning 30B-A3B**; [the selection record](10-OpenRouter-Source-Options.md#initial-nvidia-candidate-decision) distinguishes its OpenRouter catalog ID from the NVIDIA-backed and possible OpenRouter-backed Nightshift routes. Actual execution identity, applicable production tariffs and task quality remain to be verified.
2. Collect dated source URLs for input/output rates, cache-read/write rates, minimum prefix, TTL, batch eligibility/discount, long-context thresholds/rates and intelligence index. Preserve unknown values. Record permitted uses/licence, retrieval date, object version and content hash.
3. Keep catalog/reference prices and intelligence scores separate from actual Nightshift tariffs. Catalog prices may also price a clearly labeled hypothetical OpenRouter serving scenario; they must not authorize Nightshift dispatch or decide the actual-route model stack.
4. Upload founder inputs, price snapshots and result-source data to storage Zetaris can reach. Configure bucket access on the Zetaris side; keep application runtime free of bucket secrets.
5. Restore or implement a registration script using confirmed installed APIs/Lightning SQL. Provide a read-only/dry-run plan, explicit application mode and repeat-run behavior that reuses matching sources or reports conflicts without destructive replacement.
6. Validate registration with bounded reads of the actual application records, not only a sample dataset.

**Acceptance:** a teammate can register the sources from documented steps and reproduce the exact snapshot/version through Zetaris. Bundled placeholder data stays explicitly offline/unverified.

**M05 incremental check:**

```bash
python -m pytest -q tests/test_source_manifest.py
```

Add tests/test_source_manifest.py for units, required route mapping, provenance, missing/unknown prices and content hashes. Then run the registration dry run and apply flow using the exact command documented by its implementation; query one registered model row. Save the redacted plan, registration result and returned snapshot ID. No Nightshift completion is needed.

**Implemented incremental status:** 5A collection/validation PASS; 5B route discovery and an observed three-Nemotron mapping plus a separate NVIDIA Critic route PASS, applicable execution tariffs pending; 5C LocalStack publication/registration/reuse PASS. The original Claude/Gemini example routes were not offered, so [the selected serving routes](13-M05-Serving-and-Billing-Selection.md) are Ultra (frontier), Super (mid-tier), Lightning (required open model), and local Nemotron Nano (Critic). All four are in NVIDIA's open-model family; the intended closed-frontier comparison remains unproven. The actual public fetch retained 467 raw catalog entries, 460 accepted entries and 7 explicitly quarantined invalid/unbounded-price entries. Raw responses, normalization, quarantine and manifest are retained locally and published with the bundle. Versioned tables and schema 1.1 bindings pin exact IDs/counts/envelope hashes. Sources are never dropped or replaced, and the current pointer is not switched automatically.

Catalog references are not execution tariffs. The original example map remains planned; the selected map was upgraded with retained discovery and registered as bundle `740f951a20335bd2570f7a4c`, including a separate local Nemotron Nano Critic route. A no-completion live-mode preview used Zetaris catalog rows to produce 24 explicitly labeled OpenRouter listed-token cost rows; actual Nightshift route costs remained unknown. Nightshift advertised the route IDs but did not return the active provider or billing rules. Intelligence/provider-endpoint enrichment, complete official term/tariff coverage, usage-rights review and actual billing/token-bound verification remain open. The current `.env` Critic route still overlaps the selected frontier candidate and must be changed or overridden before an application run. See the [selection record](13-M05-Serving-and-Billing-Selection.md) and [manual guide](12-M05-M06-Manual-Testing.md). AWS source access has not been validated by the LocalStack check.

## Step 6 — Complete the Zetaris adapter and evidence round trip

**Files:** [base.py](../app/adapters/base.py), [live_zetaris.py](../app/adapters/live_zetaris.py), [sample.py](../app/adapters/sample.py), [controller.py](../app/controller.py).

1. Capture sanitized `SELECT 1` and application-query responses from the installed version. Confirm request fields, including the guide's `source: "SqlEditor"`, and any asynchronous query/result behavior before implementing the parser.
2. Implement typed `read_brief`, `read_models` and `read_approaches` mappings. Validate nested rate/provenance records and fail clearly on invalid rows; do not fill missing prices with zero.
3. Change the controller retrieval helper to return validated data with its observation so each query executes once. Route every application evidence read through the existing allowlist.
4. Add the needed evaluation-evidence read interface to both live and sample adapters. Persist samples, configuration references, rubric results, critique and repair outcomes through a supported ingestion/registration path, with stable IDs and idempotent writes.
5. Read persisted evidence back through Zetaris and attach its `SourceRef` to recommendation evidence. Make unpublished local results explicit after an outage and retain pending writes for recovery.
6. Treat optional build evidence independently: missing approach prices must not prevent the primary operating comparison when model prices are available. Keep existing sealed-source restrictions intact without expanding the shelved retrospective.

**Acceptance tests:** response-shape fixtures, invalid/missing rows, one query per retrieval, write/readback ID continuity, duplicate evidence writes and outage handling. **M06 live acceptance:** a cited real price row feeds a stage cost and an explicitly labeled integration-test evidence record survives write/readback. At M08, repeat the evidence round trip with an actual measured model sample.

**M06 incremental check:**

```bash
python -m pytest -q tests/test_zetaris_adapter.py
```

Add fixture-based tests/test_zetaris_adapter.py, then run an isolated live SELECT 1, one real model-price read and a write/read round trip using a record labeled integration_test_fixture. Preserve the returned SourceRefs and IDs. This first round trip does not claim a measured model run; repeat it with real measured evidence at M08. H-MEM and Nightshift must not be prerequisites for this component check.

**Implemented incremental status:** typed pinned model/founder/optional-approach reads, preserved citation/date/status plus transport/query/hash references, one query per retrieval, independent optional build failure, separate ingestion and exact evidence readback, and durable unpublished outbox recovery are implemented. Actual local checks passed SELECT 1, three model rows, a synthetic founder brief, a queried catalog-price reference calculation, and fixture write/readback/append/restart/idempotency. A real loopback HTTP ingestion/outbox rehearsal passed failure → recovery → no-op retry with exit codes 1 → 0 → 0 and zero model completions. Sealed access restrictions remain intact.

The calculator demonstration is explicitly a **token-only OpenRouter reference scenario**, not an applicable Nightshift execution bill. The controller now exposes that scenario separately for each candidate/feature/stage, with catalog rows queried through Zetaris; it never feeds the actual-route table or recommendation. M06's execution-tariff calculation remains pending until M05 supplies the correct profiles; actual measured-sample write/readback remains M08. The source component can be manually tested now without H-MEM or inference. See [manual steps](12-M05-M06-Manual-Testing.md), [selection/projection evidence](13-M05-Serving-and-Billing-Selection.md) and [earlier recorded results](m05-m06-source-checks.json).

## Step 7 — Install and connect the real H-MEM engine

**Files:** [H-MEM directory](../app/engines/hmem/README.md), [bridge.py](../app/engines/hmem/bridge.py), [sample.py](../app/adapters/sample.py), [run.py](../run.py), [test_hmem_engine.py](../tests/test_hmem_engine.py).

1. Pin the actual sponsor reference revision. Choose a reproducible vendoring/package strategy, include required licence/attribution, and add the lockfile and installation instructions needed by a clean clone.
2. Implement `bridge.mjs` against the reference's actual memory acquisition, retrieval and audit functions. Honor the wrapper contract: structured stdin, JSON-only stdout, logs on stderr, timeout and engine revision.
3. Scope persistent storage by validated project identity. Confirm the chosen reference operations function offline without hidden inference/network calls.
4. Implement a temporary-scope JSON self-test. Wire offline/sample memory to the real bridge when available; remove the path that returns `None` after a successful availability check.
5. Propagate missing/broken engine status explicitly to readiness. Never replace the engine with a Python dictionary or claim a skipped test passed.

**Acceptance:** the existing real feature test runs without skipping and proves save → new process → recall → other-project isolation → audit. Sample mode with the engine installed passes under blocked network access and produces structured memory results.

**M07 incremental check:**

```bash
python -m pytest -q -rs tests/test_hmem_engine.py
python -m pytest -q tests/test_sample_memory.py tests/test_controller_sample.py
```

Add tests/test_sample_memory.py for delegation and missing/broken engine outcomes. The real engine test must report PASS with zero required skips; a green pytest process that skipped it does not close M07. Demonstrate save, new process, recall, other-project isolation and audit. Rerun the sample helper with network blocked and confirm installing the engine does not break sample mode.

## Step 8 — Verify Nightshift model identity and usage

**Files:** [live_nightshift.py](../app/adapters/live_nightshift.py), candidate selection and `_execute` in [controller.py](../app/controller.py), proposed route mapping from step 5.

1. Retain the existing authorization, `meterless-app`, `meterless-scope`, discovery and completion paths. Confirm behavior against the installed runtime and preserve sanitized response fixtures.
2. Resolve a discovered route to its pinned, priced model identity. If runtime responses use aliases, correlate the operation with a Nightshift receipt/log; do not require literal route/model string equality when a documented mapping proves equivalence.
3. Treat absent or mismatched identity as unverified. Retain the output for inspection, but withhold model-specific comparison/award claims until its identity and pricing are reconciled.
4. Capture valid non-negative input, completion and reasoning counts, raw usage, latency and request ID. Confirm on a real response that completion includes reasoning; report reasoning as a breakdown only.
5. Run one small bounded request per candidate through the app's adapter using the dispatch safeguards. Store sanitized proof with revision and mapping references.

**Acceptance tests:** matching identity, documented alias, wrong variant, missing usage, reasoning exceeding completion and malformed responses. **Live acceptance:** three identified responses, including a concrete Nemotron-backed feature, all through Nightshift.

**M08 incremental check:**

```bash
python -m pytest -q tests/test_nightshift_adapter.py
python scripts/smoke_live.py
```

Add tests/test_nightshift_adapter.py for response/identity fixtures. Once those pass, run live smoke, then one tiny CLI evaluation: 2 text features, 3 candidates, 1 sample per pair, pre-supplied frozen rubrics and bounded outputs. Reserve up to 11 dispatches including Planner, Critic, one repair and two safe retries; choose a spend ceiling no greater than $0.50 and stop if verified rates/bounds cannot fit. Force sample_mode=false in this dedicated request, use a fresh run ID and record the actual dispatch count. Save pack, trace, resolved models, usage, Zetaris evidence readback and engine revision. Pending human review is acceptable at this checkpoint; do not call it a final reviewed recommendation.

## Step 9 — Implement representative task planning and grounded critique

**Files:** [controller.py](../app/controller.py): `_domain_risks`, `_prompt`, `_critique`, `_check_critic_route`; [contracts.py](../app/contracts.py), [rubric.py](../app/rubric.py).

1. Validate missing cost-critical founder inputs before paid work. Return structured questions, or let the founder explicitly confirm visibly assumed estimates; do not silently spend against an unusable workload.
2. Expand the existing single Planner call to return representative task instructions, output bounds, 3–5 deterministic checks per task, required human-review checks and domain risks. It may propose candidates from the retrieved eligible shortlist; the controller enforces the three roles and mandatory Nemotron route.
3. Validate the plan against typed contracts. Use approved, bounded check templates; never execute model-generated code or SQL. Freeze the same task/check definitions across candidates and save their version/hash.
4. For semantic quality bars such as factuality, require output-bound human review. Format checks alone must not be presented as proof of those semantic claims. The Planner proposes checks; it does not score candidate outputs.
5. Build Critic context from approved example inputs/facts, source references, bounded excerpts across samples, deterministic check results and input/output token comparisons. Disclose any omitted/truncated coverage.
6. Select a Critic from a non-candidate lab when supported by reliable route metadata; otherwise disclose shared/unknown lab identity. Preserve flags-only output and one controller-validated corrective action.
7. In sample mode, use explicit deterministic planning/templates where supported, or return clarification/conditional economics. Do not invent generated outputs, model evaluations or live quality scores.

**Acceptance tests:** a normal founder brief produces a usable frozen task plan; invalid plan JSON consumes its call and stops honestly; missing critical inputs prevent execution; invalid citations/actions are rejected; Critic verdict fields cannot affect grades; lab disclosure is accurate.

**M09 incremental check:**

```bash
python -m pytest -q tests/test_v4_planning.py tests/test_rubric.py
python -m pytest -q tests/test_controller_live_fake.py
```

Add tests/test_v4_planning.py. Start from the basic founder fields instead of pre-supplied rubrics and show a typed frozen task plan; missing cost-critical values return questions before dispatch. Assert critic context contains approved input and both token directions, that unsupported verdicts cannot change grades, and that invalid plans consume their permitted call. Repeat the M08 tiny profile once with live planning after the scripted checks pass.

## Step 10 — Bind human reviews and apply repair evidence consistently

**Files:** `HumanReview`, `FeatureRun`, `Revision` and result contracts; [rubric.py](../app/rubric.py); `_finish_run`, `_repair`, `_project` and checkpoints in [controller.py](../app/controller.py).

1. Bind each review to project/run, feature, resolved model, immutable output/sample references, configuration hash and check ID. Record reviewer, result, note and time. A batch review must identify every output it covers.
2. Persist executed samples before entering a review-pending condition. Add a shared review/finalization operation for CLI/UI that loads those immutable samples without calling models again. Repeated submission of the same review/finalization must be idempotent.
3. Keep original and repair runs as separate versions. Invalidate affected human approvals when output, prompt, model or configuration changes.
4. Accept a repair as the effective configuration only after measured usage is available and every critical check, including required human review, passes. Otherwise retain the original qualified configuration or report that none qualifies.
5. Have projection select tokens, rubric, tariff/model identity and output cap from that same effective version. Keep explicit original → proposed repair → accepted/rejected/pending evidence in the pack.

**Acceptance tests:** stale/cross-run reviews cannot approve new output; repairs require fresh semantic review; fail → pass changes qualification; pass → fail is rejected; pending stays pending; repeated finalization dispatches no model calls. A successful repair changes both the projected cost and quality evidence together.

**M10 incremental check:**

```bash
python -m pytest -q tests/test_review_finalize.py tests/test_rubric.py
python -m pytest -q tests/test_controller_live_fake.py tests/test_stage_economics.py
```

Add tests/test_review_finalize.py using saved/scripted outputs. Verify stale review rejection, repair fail-to-pass and pass-to-fail behavior, all-critical-check qualification and finalization with zero new generations. Save before/after effective configuration IDs, rubric results and costs. Rerun the M02 lever regression against a selected repair configuration. Exercise an actual cap only if a live Critic proposes a validated one; retain an honest no-repair live path otherwise.

## Step 11 — Use confirmed memory on later runs

**Files:** [controller.py](../app/controller.py), H-MEM bridge, founder/result contracts and Zetaris evidence records.

1. Define compatible record kinds for `confirmed_assumption` and `accepted_decision`, with project scope, source/run IDs, version, status and supersession references. Use matching save/recall filters.
2. Add explicit assumption confirmation and decision acceptance actions. Evaluation approval authorizes bounded testing; it does not automatically accept the resulting recommendation.
3. Store compact accepted facts and evidence references. Recall actual context at the next run, validate it against current structured inputs, and use current confirmed inputs to override superseded memory.
4. Feed valid recalled assumptions into planning/projection and produce a dated comparison of prior versus current users, prices, selected models and costs. Separate workload changes from price/model changes.
5. Read current prices from Zetaris every time. Memory must never become an alternative price authority. Keep live and sample records distinguished so offline recommendations cannot become live measured evidence.
6. Support a projection-only rerun when only volume/stage assumptions change: reuse compatible persisted samples, retaining their original execution time and IDs. Changing task, rubric, prompt or model identity requires new evaluation/review as appropriate. Do not label reused measurements as newly executed calls.

**Acceptance:** confirm a constraint, complete/accept a decision, restart, and rerun at a changed stage. The pack shows the recalled fact influencing the plan and explains the change. A different project cannot retrieve it; current confirmed values supersede old memory.

**M11 incremental check:**

```bash
python -m pytest -q tests/test_memory_workflow.py
python -m pytest -q -rs tests/test_hmem_engine.py
```

Add tests/test_memory_workflow.py. Accept a confirmed assumption/decision, stop and restart, then rerun with one changed stage assumption. Assert recalled context is used, current confirmed values win, project isolation holds and before/after differences have source references. Save both run IDs, memory IDs and the comparison. Reusing saved samples for an unchanged task must not trigger extra paid generation.

## Step 12 — Aggregate stage costs, revenue and budget fit

**Files:** [economics.py](../app/economics.py), [contracts.py](../app/contracts.py), `_project` in [controller.py](../app/controller.py).

1. Aggregate effective recommended feature costs into one monthly stack total per stage, retaining feature-level tables and comparable candidate totals. If a required feature is unqualified or unknown, show the aggregate as incomplete/unknown and identify known components separately.
2. Propagate the founder's switch threshold into switch detection and model-stack selection. Compare the monthly stack total with `monthly_ai_budget_usd`; show the first exceeded stage and qualified alternatives.
3. Compute stage revenue as `active_users × paying_fraction × subscription_price_usd`. Compute `AI contribution = revenue − monthly AI cost` and `AI contribution margin = AI contribution / revenue` when revenue is positive.
4. Label these as AI-only contribution measures because non-AI operating costs are outside the modeled total. With absent revenue, show costs only; with zero revenue, contribution can be negative but margin is undefined.
5. Preserve build costs as a separate ledger and keep one-time costs out of monthly operating totals.

**Acceptance tests:** threshold edits move switch points; monthly-budget edits change fit; paying fraction is not treated as active-user fraction; unknown feature costs prevent a complete total; missing/zero revenue and Decimal display precision are correct.

**M12 incremental check:**

```bash
python -m pytest -q tests/test_stage_summary.py tests/test_stage_economics.py
```

Add tests/test_stage_summary.py with known feature totals, incomplete aggregates, threshold changes, ceiling crossings, missing revenue, zero revenue and 0%/100% paying fractions. Save two packs that differ only in switch threshold or monthly budget and inspect the corresponding decision change. The arithmetic checks are offline.

## Step 13 — Build the Streamlit workflow around shared operations

**Files:** proposed `streamlit_app.py` and a small shared application service; [run.py](../run.py), contracts and controller. Keep business rules in the core.

1. Expose the v4 form: idea, user, 2–5 features with example/mode/usage, editable stages, optional monthly ceiling/quality/revenue/build fields. Display assumed defaults beside their controls.
2. Show preflight/readiness, missing-input questions, task-plan details and the bounded evaluation spend. Collect evaluation authorization before paid execution.
3. Persist a stable run ID for a submitted evaluation. UI rerenders must load progress/results, not create a new paid run. Call the same idempotent core operations from UI and CLI.
4. Present samples with deterministic results and output-bound human-review controls. Finalize and accept decisions using steps 10 and 11 without regenerating samples.
5. Render recommended/alternate stacks, aggregate stage table/chart, feature drill-down, lever deltas, switch evidence, estimated/measured token comparisons, separate build panel, risks and memory changes.
6. Provide decision-pack and trace exports with source/version references. Keep `SAMPLE/OFFLINE` visible on every offline view/export; show partial, unknown and review-pending results explicitly.

**Acceptance:** one live and one offline idea traverse form → pack → review/results → export using the shared core. Double-click, rerender, review and download produce no extra generations. Charts and tables match serialized pack values.

**M13 incremental check:**

```bash
python -m pytest -q tests/test_controller_sample.py tests/test_review_finalize.py
```

After implementing and documenting streamlit_app.py, launch with python -m streamlit run streamlit_app.py. Run the sample form and compare displayed numbers with the exported pack. Double-click submit, rerender, review and download; the operation log must show no duplicate generations. Then use the same tiny live profile as M08. No model calls are needed for the sample UI check.

## Step 14 — Rehearse and collect release evidence

**Files:** README, contributor instructions, [data/README.md](../data/README.md), input/output examples, proposed evidence ledger, demo/deck links.

1. Run relevant focused tests as each behavior changes. Before committing an implementation, run the complete `python -m pytest -q` suite required by project instructions. Live sponsor proof remains separate from scripted adapter tests.
2. Regenerate the three example packs at the final schema/revision, with fresh or isolated run databases. Include an unseen in-domain input, missing-input case and changed budget/quality/volume case. Runtime must never read `output_examples/` as answers.
3. Rehearse a clean clone on a second machine using only documented instructions: install pinned Python/Node/reference dependencies; configure private access manually; register/query sources; run sample and live workflows. Install dependencies before launching the application.
4. Run three live founder ideas. Keep operation IDs, resolved identities, usage, cost, latency, deterministic results, human reviews, accepted/rejected repair and memory restart evidence. Preserve an honest no-repair path; do not force a corrective action to improve the demo.
5. Stop sponsor services and verify the documented offline path. Separately exercise sponsor outage, unknown request outcome, evidence-write outage, duplicate submission and missing-price cases. Confirm these produce useful structured outcomes with no provider bypass.
6. Obtain consented before/after decisions from the founding team’s self-evaluation and one or two outside founders. Label self-evaluation and retain negative results. Store only publication-approved feedback in the public repository.
7. Update README setup commands, real repository URL, supported runtime versions, route mapping location, engine revision/attribution and known limits. Document data registration, result persistence, recovery, sample behavior and the real memory test. Share the final video/deck and evidence links through the release ledger.
8. Reconcile all capability claims with the final traces and tested revision. Verify public artifact access and current submission requirements before submission. Record acceptance separately from code completion.

**Existing checks to run after their implementations are complete** (activate the documented virtual environment first):

```bash
python -m pytest -q
python -m pytest -q tests/test_hmem_engine.py
python scripts/smoke_live.py
```

The smoke script makes bounded live inference requests once configured; its result is diagnostic evidence, not a substitute for the three-idea rehearsal. New script paths or UI commands proposed in this guide should enter the README only after they exist and have been tested. Document platform-specific shell syntax and unique run IDs for reruns.

**Release acceptance:** every required finding has a passing check and artifact at the final revision; the real engine test is not skipped; required sponsor checks are PASS; second-machine live/sample runs succeed; founder observations and submission links are recorded. A deliberate scope change must be reflected in `07` and capability claims rather than silently marked done.

**M14 incremental check:**

```bash
python -m pytest -q
python -m pytest -q -rs tests/test_hmem_engine.py
python scripts/smoke_live.py
python scripts/check_sample_examples.py
```

Run these from the final clean clone after all planned files exist. Required integration skips are a release failure even when the overall suite is green. Complete three live ideas, an unseen sample input, missing-input and outage cases, the second-machine rehearsal, founder observations and public artifact checks. Record the exact revision; inspect pack status, readiness and artifacts rather than relying only on exit codes.

## Final handoff checklist

- [ ] F01: typed Zetaris reads and evidence round trip work from a clean setup.
- [ ] F02: pinned real H-MEM works live/offline and passes restart/isolation tests.
- [ ] F03: all candidate identities match their price records; Nemotron proof is attributable.
- [ ] F04: dated, cited source snapshots and repeatable registration are available.
- [ ] F05: shared-core founder UI works in both modes.
- [ ] F06: validated representative tasks and rubrics come from the planning workflow.
- [ ] F07: confirmed/accepted memory changes a subsequent run and reports differences.
- [ ] F08: composed levers produce valid totals with unknown prices preserved.
- [ ] F09: repaired tokens and quality jointly drive the effective recommendation.
- [ ] F10: dispatch/spend limits and unknown-outcome recovery pass.
- [ ] F11: ranges, unique IDs, optional build fields, budget, threshold and provenance pass.
- [ ] F12: stage totals, revenue, AI contribution and margin pass.
- [ ] F13: Critic receives grounding evidence and lab independence is handled honestly.
- [ ] F14: human reviews are bound to actual immutable outputs and invalidated on change.
- [ ] F15: traces preserve usage and required SKIPs cannot report readiness.
- [ ] F16: documentation, clean-clone rehearsal, founder observations and release artifacts are complete.
