# v4 evidence ledger and release checklist

Updated 2026-10-26. The step-by-step plan and findings table are in [08-v4-Implementation-Plan.md](08-v4-Implementation-Plan.md), and the candidate, billing and NVIDIA revisions are in [17-v4-Revised-Implementation-Steps.md](17-v4-Revised-Implementation-Steps.md); this file records what was actually run and what it showed, including negative results. A PASS applies only to its stated scope. Planned tests and required integration skips are never converted into PASS results. New entries append the exact command, environment, expected and actual result, revision and artifact path.

## Current status

| Step | Status | Where |
|---|---|---|
| M00 Baseline and recovery inventory | PASS, scoped | below |
| M01 Input contracts and founder controls | PASS, scoped | below |
| M02 Composed cost levers | PASS, scoped | below |
| M03 Trace evidence and truthful readiness | PASS, scoped; Windows preflight PASS (2026-10-26) | below |
| M04 Bounded dispatch, spend and restart safety | PASS, scoped | below |
| M05–M06 Source pipeline and Zetaris evidence round trip | PASS for components on LocalStack and on real AWS S3 from a Windows host (2026-10-26, 2026-10-27); usage-rights review unverified | below |
| M07 Real H-MEM, offline delegation | PASS, local reference scope | below |
| M08 Nightshift identity and first live pack | Superseded by R1 and R5, both PASS | below |
| R0 Requirement split | Decided and written into `07` v4.3 and `CLAUDE.md`; Narin sign-off and the official rule quote still open | `07` §4, `docs/17` §2 |
| R1 Planner and Critic role routes | PASS | below |
| R2 Modality-aware catalog and contracts | PASS | below |
| R3a Per-feature candidate selection | PASS | below |
| R4 Execute verified routes, project the rest | PASS | below |
| R5 First bounded live pack | PASS for dispatch, spend, identity and evidence (`r5-live-20261026-113150-e`); token and cost numbers predate the memory fix | below |
| R11a Live smoke check (Planner and Critic) | PASS, diagnostic scope (2026-10-26) | below |
| Nightshift memory isolation (unique scope per request) | PASS; Examples 1 and 3 re-measured | entries at the end |
| R6 Task planning, grounded critique (was M09) | Not started | plan Step 9 |
| R7 Review binding, effective repair (was M10) | Not started | plan Step 10 |
| R8 Memory changes a later run (was M11) | PARTIAL: recalled founder inputs (budget, price, paying fraction) fill blank fields in a later run of the same idea; memory does not change model choice | R8 entry below |
| R9 Stage totals, revenue, budget fit (was M12) | PASS, offline arithmetic and UI; recommended-stack totals stay unknown until R7 | R9 entry below |
| R10 Streamlit workflow (was M13) | Trimmed version: live runs from the UI PASS, founder candidate picks, revenue inputs, totals and a live progress panel; no human-review controls (R7); layout not reviewed in a browser | R10 entries below |
| Live proof runs (published) | PASS: examples 1–3 and an H-MEM recall run, all `complete`, $0, evidence written back (2026-10-27) | `output_examples/live/`, entry below |
| R11 Release rehearsal (was M14) | In progress: sample-mode clean clone on a second machine PASS; live clean clone on Windows with real AWS S3 PASS after two fixes (2026-10-27); video and deck pending | R11 entries below |

## Open items and caveats before submission

- **R0 not closed:** the official NVIDIA rule wording is not yet quoted, and Narin has not signed off on `07` v4.3.
- **Quote only post-fix measurements:** runs before `ui-20261026-165715` used Nightshift's shared memory scope, so their token, cost and quality numbers are unreliable. Clean runs: `ui-20261026-165715`, `ui-20261026-170134` (Example 3) and `ui-20261026-172053` (Example 1, cross-lab candidates).
- **Nightshift providers:** cross-lab candidates exist only while Nightshift's OpenRouter provider is connected (it dropped once on 26 October; 111 routes when connected, 74 without).
- **Estimates versus measurements:** estimates include the brief's assumed production system prompt, which evaluation calls do not send; measured rows may understate an app that sends one (open modelling decision).
- **Audio:** no audio-output route exists, and audio-input candidates have no audio conversion rate, so their cost is unknown.
- **Sponsor readiness:** `scripts/smoke_live.py` passed on 2026-10-26 (R11a below) at diagnostic scope. Pack `readiness` still reads `not_verified`: billing and in-run evidence readback are separate dimensions, and this is not end-to-end sponsor proof. Re-run it on the final setup before submission.
- **Local-only data:** the registered bundles, bindings, catalog copies and R5 artifacts are gitignored. A clean clone must re-collect and re-register sources (`collect_sources.py`, `prepare_source_bundle.py --include-discovered`, `register_sources.py`); a sample-mode clean clone was rehearsed on a second machine, and the live re-collect and re-register path on a Windows clean clone against real AWS S3 (R11 entries below).
- **Free key:** the NVIDIA key is a free Developer Program key (prototyping only); its rate limits are unknown, and only Ultra and Lightning have verified profiles, so only they are measured; other candidates are projected only. Market-price totals are lower bounds.
- **Quality:** one sample per pair and pending human-review checks mean no candidate qualifies yet and no quality claim is made.
- **Required live settings:** thinking off for the Planner and Critic and for both Nemotron routes, a 150 s timeout, and a running evidence publisher (README settings table). Ultra still used 1,015 of 1,024 output tokens on one sample.

## Final handoff checklist

- [x] F01 Typed Zetaris reads and evidence round trip (local, and on a Windows clean clone with real AWS S3)
- [x] F02 Real H-MEM works and passes restart and isolation tests (local reference)
- [x] F03 Candidate and role identities match their records; Nemotron proof attributable (R1, R5)
- [x] F04 Dated, cited source snapshots and repeatable registration
- [x] F05 Shared-core founder UI in both modes (trimmed; no review controls; layout not reviewed in a browser)
- [ ] F06 Validated representative tasks and rubrics from the planning workflow
- [ ] F07 Confirmed and accepted memory changes a later run (partial: founder inputs fill blanks, R8; model choice unchanged)
- [x] F08 Composed levers give valid totals; unknown prices preserved
- [ ] F09 Repaired tokens and quality jointly drive the recommendation
- [x] F10 Dispatch, spend limits and unknown-outcome recovery
- [x] F11 Input validation and founder controls (budget fit across stages added in R9)
- [x] F12 Stage totals, revenue, AI contribution and margin (R9; recommended-stack totals need R7)
- [ ] F13 Critic grounding and honest lab independence
- [ ] F14 Human reviews bound to immutable outputs
- [x] F15 Traces keep usage; required SKIPs cannot report readiness (Windows preflight PASS)
- [ ] F16 Documentation, clean-clone rehearsal, founder observations, release artifacts (clean clone PASS in sample mode on a second machine and live on Windows with real AWS S3; founder observations and release artifacts open)
- [x] F17 No candidate or tier hard-coded (optional curated tier hints and an optional override remain)

## M00 — Baseline and recovery inventory

**Status: PASS — offline baseline and history inventory only.** Checked October 25, 2026. Base revision `9936c6683b205a1a69b57ce063c11c32a0bb0c64`; branch `feature/realign-07-meena`; macOS, Python **3.12.12** in `.venv`.

At the start, `.gitignore` was already modified and the gap review/implementation guide were untracked. These were preserved. M00 adds the sample checker, its regression test, this ledger/inventory, and v4 contributor/README instructions. Core application behavior and historical integration implementations were not changed. Evidence therefore refers to this base revision **plus the working tree**, with source SHA-256 hashes in the checker manifest.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `.venv/bin/python -m pytest -q -rs` before changes | Offline Python tests | Existing suite passes; known skips recorded | 100 passed, 9 skipped | PASS, baseline only |
| `.venv/bin/python -m pytest -q tests/test_check_sample_examples.py tests/test_controller_sample.py tests/test_sample_data.py` | Isolated CLI regression; no sponsor credentials | Three-example checker plus sample regressions pass; source inputs preserved | 19 passed | PASS |
| `.venv/bin/python -m pytest -q -rs` after adding the checker/test | Offline Python tests | Existing suite and new checker test pass; known skips remain explicit | 101 passed, 9 skipped | PASS, offline scope |
| `.venv/bin/python scripts/check_sample_examples.py` | Copied requests; fresh databases/logs; dotenv disabled; Python sockets blocked | All three examples complete in sample mode with estimated costs and no fabricated execution/quality | Three PASS results; 4 / 3 / 2 feature tables; 12 / 9 / 6 unexecuted feature/candidate records | PASS |
| History inspection of `1f27731` | Local Git, read-only | Identify reusable mappings, registration, engine and diagnostics with adaptation boundaries | Recorded in integration inventory (`docs/evidence/m00-integration-inventory.md`, local only) | PASS |
| Contributor/setup instruction review | Documentation | `07` is authoritative; retrospective shelved; repeatable check documented | Updated [CLAUDE.md](../CLAUDE.md) and [README](../README.md) | PASS |

Known baseline skips: **8** shelved retrospective tests and **1** H-MEM test because the real bridge/reference is absent. The H-MEM skip leaves M07/F02 open. Current placeholder prices and live adapter gaps remain open.

### Retained sample artifacts

Check timestamp: **2026-10-25T20:49:51+00:00**. Current-machine artifact directory:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-7pk4fggq/
```

`manifest.json` records the revision, working-tree source hashes, input hashes, Python version, every assertion and artifact paths. Each `example_1/`, `example_2/` and `example_3/` contains a copied request, `pack.json`, CLI stdout/stderr, its own database and JSONL trace. These temporary artifacts are machine-local; a clean clone must rerun the checker to produce new evidence. To retain a new run at a chosen location, use a new `--output-dir` path.

The checker verifies sample labels, zero spend, three candidate tiers, all expected feature/candidate pairs, estimated rows, no executed samples, no measured usage/rubric scores, no qualified switch points, no repairs, and no live inference trace events. It ignores parent sponsor configuration and does not load `.env`. Its socket guard covers Python; Node engine offline behavior remains a separate M07 check. The checker reports `sponsor_readiness: not_verified` even on PASS.

## M01 — Input contracts and founder controls

**Status: PASS — input validation and offline contract integration.** Checked October 25, 2026 on the same base revision plus the working tree, Python 3.12.12. No live model/provider calls were made.

Implemented:

- Operating requests can omit build scope/constraints; the secondary panel reports unknown build costs and does not rank an absent build scope.
- Full run requests require 2–5 AI features. Reusable feature/calculator contracts still support a single feature. Feature IDs, build IDs, stage names and per-feature check IDs are unique; required text is nonblank.
- Costs, volumes and token counts must be finite/non-negative; calls-per-use, team size and cache TTL are positive; fractions stay in `[0, 1]`. Evaluation spend inputs cannot exceed $25. Public unknown fields are rejected before setup; run/project IDs cannot escape their trace filename scope.
- Value defaults and founder estimates are marked assumed unless explicit evidence is declared; absent/null values stay unknown. Omitted defaults cannot become verified through provenance metadata alone. Metadata survives serialization.
- Request/pack schema `1.1`; legacy `1.0`/unversioned envelopes normalize under the same validation. All three input examples were updated and matching sample outputs regenerated with isolated databases and portable trace references.
- `brief.monthly_ai_budget_usd` and `brief.switch_threshold_usd` survive pack export. The threshold reaches the existing tables/model-stack calculation. The monthly ceiling is explicitly recorded without claiming an aggregate fit calculation.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `.venv/bin/python -m pytest -q tests/test_v4_contracts.py tests/test_controller_sample.py tests/test_sample_data.py` | Offline fixtures and isolated CLI | Contract behavior and sample regressions pass | 102 passed | PASS |
| `.venv/bin/python -m pytest -q -rs` | Full offline suite | All existing and added tests pass; known skips remain explicit | 185 passed, 9 skipped | PASS, offline scope |
| `.venv/bin/python scripts/check_sample_examples.py` | Forced sample mode; dotenv disabled; Python sockets blocked | Three estimated packs with no fabricated execution or quality | Three PASS results; 4 / 3 / 2 feature tables | PASS |
| Regenerate `output_examples/example_{1,2,3}_output.json` using the real CLI | Temporary databases, Python socket guard, original example run IDs | Schema 1.1, complete offline packs and portable relative trace paths | Three outputs regenerated and asserted | PASS |

The final contract file contains **84 test cases**, including version migration, legacy validation, zero volume, duplicate/blank fields, malformed public controls, export/provenance round trips and failure before adapter setup. The scripted full-run fixture now supplies two features; the prior no-feature CLI test now expects structured invalid input. Sealed-source controls were not weakened.

Retained local sample manifest (checked at `2026-10-25T21:03:18+00:00`):

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-8iez9upq/manifest.json
```

Final example regeneration records and real traces:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-m01-portable-examples-qtgxe4uz/regeneration-manifest.json
```

These are current-machine artifacts; reproduce them from a clean clone using the checker. The latest sample manifest records the final application/input source hashes used for this milestone.

**Still open:** M02's combined-lever defect, M04's dispatch/reservation/retry enforcement, M06's live adapter/optional build-data read behavior, M12's aggregate budget fit and revenue, and the remaining sponsor/workflow milestones. The nine skips still include eight shelved retrospective tests and one unavailable real H-MEM test. F11 is addressed for public input validation and preserved controls, not for every downstream founder-control use.

## M02 — Composed cost levers

**Status: PASS — deterministic calculator and fixture evidence.** Checked October 25, 2026 on the same base revision plus working tree, Python 3.12.12. No live inference or provider-pricing lookup was performed. These results close the reproduced F08 calculator defect; real accepted-repair quality/selection stays open under M10/F09.

Implemented:

- Output caps change the entire effective text usage, including input, before whole-request long-context pricing and production discounts are calculated.
- Monthly scenarios are computed in order: original standard-rate baseline → accepted-cap usage → applicable tariff → supported caching/batch → output reuse with paid-volume eligibility recalculated. All internal amounts remain Decimal; exact deltas telescope in the interaction fixtures, with rounding discrepancies disclosed for displayed cents.
- Required unknown long-context prices leave `monthly_with_levers_usd`, cost per use and revenue share unknown. Such rows cannot qualify model choices or switch points, even after pack serialization.
- `terms.lever_combinations` records exact, supported combinations with a verified, dated source URL. Missing/unsupported/unverified rules prevent stacking; the cheapest supported standalone scenario is selected instead. Three-way support is not inferred from pairs.
- Long-context caching requires dedicated tier cache-read/write prices. Batch discounts text charges without discounting audio charges. Cache eligibility states its uniform-traffic assumption.
- Output reuse recalculates cache/batch eligibility for paid call volume. One-time fill uses effective request/tariff pricing with no assumed prompt-cache hits and never enters the monthly total.
- Negative/non-finite calculated costs and retry rates fail validation instead of being clamped or used as negative bills.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `.venv/bin/python -m pytest -q tests/test_stage_economics.py tests/test_economics.py` | Synthetic calculator fixtures | Composed-lever, precision, unknown-price and existing economics checks pass | 75 passed | PASS |
| `.venv/bin/python -m pytest -q -rs` | Full offline suite | New and existing tests pass; known skips remain explicit | 217 passed, 9 skipped | PASS, offline scope |
| `.venv/bin/python scripts/check_sample_examples.py` | Forced sample; dotenv disabled; Python sockets blocked | All three packs complete with estimates and zero executed samples | Three PASS results; 4 / 3 / 2 feature tables | PASS |
| Committed calculator fixture artifact | Synthetic inputs only | Exact batch/cap $1.1055; unknown tariff stays unknown; standalone discount and paid-volume recalculation correct | Four asserted cases PASS in JSON artifact | PASS |
| Regenerate three committed example outputs | Real CLI, temporary databases, original run IDs, socket guard | Updated calculator behavior with portable trace paths and no fabricated model calls | Three complete sample outputs regenerated | PASS |

The initial focused interaction selection reproduced **18 failing cases** before implementation. Final regressions cover capped input changes, threshold crossings, missing long-context prices, exact/unsupported combinations, source metadata, tier-specific cache prices, audio exclusions, reuse/TTL changes, one-time fill, zero volume, exact deltas and invalid costs. Calculator fixes do not validate live provider eligibility: current sample prices/terms remain placeholders.

Retained sample manifest, checked at `2026-10-25T21:22:07+00:00`:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-bkt_kttv/manifest.json
```

Example regeneration evidence:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-m02-examples-aan1zsh7/regeneration-manifest.json
```

Temporary artifacts are current-machine evidence and should be regenerated on a clean clone. m02-calculator-regressions.json retains portable synthetic inputs, computed rows, expected/actual exact totals and exact lever deltas. Its measured/verification fields are test simulations, explicitly labeled as such; they are not real API usage or sponsor proof. The known nine skips and M03–M14 gaps remain open.

## M03 — Trace evidence and truthful readiness

**Status: PASS — offline trace/diagnostic regressions and shared readiness contract.** Checked October 25, 2026 on base revision `9936c6683b205a1a69b57ce063c11c32a0bb0c64` plus the working tree, Python 3.12.12 on macOS. No live sponsor/model calls or external writes were made. The revised Windows preflight has not been executed: PowerShell is unavailable on this host.

Implemented behavior:

- Numeric token counts and nested reasoning/cache details survive redaction. Credential fields, configured credential values and bearer strings are masked in JSONL, stderr and final-result output; masking precedes summary truncation. Long model IDs and source hashes remain readable.
- Both live HTTP adapters emit an attempt before dispatch and a matching success/error terminal event with the same operation ID. Events retain request/query IDs, requested/resolved identity when available, HTTP status, latency, usage when available, adapter source hash and configuration reference. Timeout, non-2xx, JSON/shape and SQL semantic failures remain attributable.
- Shared validators require exactly one SQL cell equal to 1 and nonempty, unique model IDs in the expected discovery structure. HTTP 200 alone does not pass either check. Nemotron diagnostics require an explicit discovered/resolved Nemotron identity and a response request ID; unresolved aliases cannot pass.
- All seven smoke checks are required. Required SKIP returns `incomplete` and exit 1; missing checks cannot report ready. Markdown and JSON diagnostic artifacts have a separate `live_diagnostic` scope. H-MEM self-tests require valid JSON with `status: ok` and a successful process exit.
- Packs and successful CLI final results expose the shared typed `ReadinessResult`. Pack sponsor integration checks stay `not_verified`, even when the pack completes; diagnostic connectivity cannot promote them. Future UI consumption remains M13.
- Windows preflight delegates SQL/discovery validation to the shared Python code, masks supplied credentials, returns non-success for required SKIP/UNKNOWN/FAIL, and labels its verdict as machine/connectivity only. Python validation behavior is tested; PowerShell execution remains unverified.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `.venv/bin/python -m pytest -q tests/test_trace.py tests/test_smoke_live.py` | Offline HTTP/subprocess fixtures | Trace redaction/evidence and readiness checks pass | 89 passed | PASS |
| `.venv/bin/python -m pytest -q -rs` | Full offline suite | New and existing tests pass; known skips retained | 303 passed, 9 skipped | PASS, offline scope |
| `.venv/bin/python scripts/check_sample_examples.py` | Forced sample; dotenv disabled; Python sockets blocked | Three complete estimated packs with sponsor readiness unverified | Three PASS results; 4 / 3 / 2 feature tables | PASS |
| Smoke CLI with placeholder settings, `--no-dotenv`, isolated output and Python socket guard | No configured sponsor prerequisites | Seven required SKIPs; incomplete; exit 1 | 0 PASS / 0 FAIL / 7 SKIP; `incomplete`; exit 1 | PASS, negative-path assertion |
| Regenerate three repository example outputs through the real CLI | Temporary databases, original IDs, Python socket guard | Complete packs; final-result readiness matches pack; portable trace paths | Three outputs regenerated and asserted | PASS |
| Portable HTTP fixture traces | Synthetic model/usage/SQL payloads | Usage remains numeric; timeout and wrong SQL cell retain correlated error events | Three scenarios asserted in JSON artifact | PASS |
| Revised PowerShell preflight | Windows 11, PowerShell 7, venv Python, live Zetaris and Nightshift (2026-10-26) | Execute on Windows with configured Python and fixture/live endpoints | PREFLIGHT CHECKS PASS, 0 FAIL/WARN/SKIP/UNKNOWN ([aws-registration-check.json](aws-registration-check.json)) | PASS |

Final sample-check manifest:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-k6rouuc3/manifest.json
```

Unconfigured diagnostic and example regeneration artifacts:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-m03-evidence-2_24yps5/regeneration-manifest.json
```

m03-diagnostic-regressions.json retains portable synthetic traces, required-skip/readiness results, sample readiness assertions and working-tree source hashes. Fixtures are not installed-runtime or provider evidence. The nine skips still include eight shelved retrospective tests and one missing real H-MEM test. M04 dispatch/spend/restart enforcement, M06–M08 real integration proof and M13 UI consumption remain open. Execute the Windows preflight during the integration-host/clean-clone rehearsal; this scoped PASS does not claim Windows validation or end-to-end F15 release proof.

## M04 — Bounded dispatch, spend and restart safety

**Status: PASS — offline scripted dispatch and durable-ledger safety.** Checked October 25, 2026, `2026-10-25T21:55:55+00:00`, Python 3.12.12 on macOS. Base revision `9936c6683b205a1a69b57ce063c11c32a0bb0c64` plus the working tree. Synthetic pricing, policy and HTTP/inference fixtures only; no live model/sponsor requests or external writes were made. No run database was erased.

Implemented behavior:

- The shared `Dispatcher` handles Planner, candidates, Critic, repair and diagnostic completions. The live adapter requires a reservation context and uses the durable receipt's operation ID for its HTTP request/trace correlation.
- Every attempt has a validated positive output limit (at most 1,024), a cited route byte/token/overhead bound, confirmed completion-limit/reasoning semantics and verified required rates/terms. Unknown/missing evidence stops before paid work with a `dispatch.*` evidence gap. Planner/Critic routes must be priced explicitly; automatic router aliases cannot be reserved. Sample data remains unverified and cannot authorize paid dispatch.
- SQLite atomically claims the operation, spend reservation and dispatch slot before adapter entry. Receipts retain role, attempt, route, provider ID when available, reservation, measured usage-based charge, state, usage and source refs. Successful responses are persisted for recovery. Existing run IDs/operations cannot replay; unresolved `dispatching`/`unknown` receipts retain reservations across restarts and block further spending. Concurrent connections cannot pass an unresolved claim.
- Known spend is reconciled for every role at the applicable full input/output tariff without assuming production cache/batch discounts. Required long-context prices are included in bounds, while actual usage selects its actual whole-request tariff. Unknown charges remain separately visible in `reserved_spend_usd`. A known overrun records the full charge and blocks later work even when the charge exceeds the approved budget; the software cannot undo a runtime's violated bounds.
- Only connect/connect-timeout/pool failures known to precede dispatch may retry. Each retry creates another receipt/reservation and consumes a slot. Read/write timeouts, HTTP errors, malformed responses, missing usage and unpriced identities are potentially charged, retained and not automatically retried. No provider idempotency is assumed.
- The stricter policy is documented in `Planning/07-Realignment-v4.md` and README: 30 total attempts across roles/retries, at most two safe retries globally, one logical Planner, one logical Critic and at most one logical repair. Sampling is selected before calls: four features use two samples and reserve at most 29 slots; five use one. Explicit `validation` sampling uses one per pair. Packs report the selected profile/count, receipts and accounting.
- Smoke completions use the same dispatcher with a separately validated allowance of $0–$1, default disabled. The diagnostic ledger and run ID support duplicate refusal. Invalid allowances fail before dotenv/setup, and absent billing evidence never dispatches.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `.venv/bin/python -m pytest -q tests/test_dispatch_limits.py tests/test_controller_live_fake.py tests/test_smoke_live.py tests/test_trace.py` | Scripted/HTTP/subprocess fixtures; temporary SQLite DBs | Spend, retry/call caps, unknown/restart/concurrency, profiles and diagnostic integration pass | 183 passed, including 67 dispatch and 20 controller tests | PASS |
| `.venv/bin/python -m pytest -q -rs` | Full offline suite | Existing/new tests pass, known skips retained | 377 passed, 9 skipped | PASS, offline scope |
| `.venv/bin/python scripts/check_sample_examples.py` | Forced sample, dotenv disabled, Python sockets blocked | Three complete estimated packs; zero dispatches, spend and reservations; readiness unverified | Three PASS results; 4 / 3 / 2 feature tables | PASS |
| Six portable dispatch scenarios | Synthetic inference and cited-fixture policies | Zero-budget refusal, single ambiguous attempt, safe retry, all-role reconciliation, overrun and unknown restart refusal | Six asserted cases in JSON artifact | PASS |
| Three scripted controller sampling cases | Four/five features; fake responses only | 4/production: 2 samples, 27 actual calls; 5/production: 1 sample, 18 calls; 4/validation: 1 sample, 15 calls | All cases complete with reconciled spend and zero held amount | PASS |
| Regenerate all three example outputs via actual CLI | Fresh temporary DBs, original example IDs, Python socket guard | Portable traces, new dispatch/profile fields, complete offline packs and final-result accounting | Three outputs regenerated and asserted | PASS |

Final sample checker manifest:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-h9vcfsku/manifest.json
```

Retained test stdout/stderr, scripted packs, databases/traces and example-regeneration manifest:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-m04-evidence-stdihrbh/regeneration-manifest.json
```

m04-dispatch-regressions.json preserves synthetic billing inputs, durable receipts, expected/asserted results, sampling summaries, executed commands and working-tree source hashes. Verification flags and model/API fields in that artifact are explicitly simulated; they are not real tariff or sponsor proof. Prior scoped results remain historical. M05–M08 must collect actual route, tariff, framing/token and reasoning-limit evidence before live dispatch. Unknown-charge reconciliation remains an external evidence task; automatic replay is deliberately unsupported. The nine skips and Windows/real-engine/provider validation remain open.

## M05–M06 — Source pipeline and Zetaris evidence round trip

**Status: PASS for components** (checked 2026-10-25, extended 2026-10-26). The collector, pinned bundles, registration, typed reads, separate ingestion and readback, and the durable outbox work. No owners are assigned.

- Actual public OpenRouter collection: 467 raw records, 460 accepted catalog rows, 7 quarantined invalid or unbounded-price rows; raw files, normalization, rejection reasons, manifest and hashes retained. Snapshot `a6cff78717992be3b332c65d`. No inference was used.
- Registered under namespace `cost_optimizer_v4`, bucket `cost-optimizer-data`, prefix `cost-optimizer/v4` (LocalStack S3 emulation only). Repeated registration reuses identical objects and never changes the current pointer.
- Zetaris component checks: `SELECT 1` cell validated, typed model and brief reads with provenance, a queried catalog price feeding a labeled reference calculation, integration-test evidence write and readback, a second append, a recreated publisher and duplicate-write behavior. Fixture evidence stays `unverified`.
- Loopback ingestion and outbox: an unavailable endpoint left evidence pending, restored ingestion published it, a retry was a no-op, with zero model completions. This was repeated on real run evidence in R5.
- Current registered bundle: `87f8564d36ffd17330015ad3` (460 catalog rows, 37 model rows with modalities, two curated role profiles), bindings `data/localstack/openrouter/bindings-wide2.json`, built from the migrated catalog copy `data/localstack/openrouter/catalog-modalities/a6cff78717992be3b332c65d`. Earlier bundles are retained locally and are superseded.
- Nightshift discovery on 2026-10-26: 111 routes (51 `local-runtime`, 37 `openrouter/`, 18 `meterless/`, 5 `nvidia/`); 35 of the 37 OpenRouter routes match a catalog ID.

Catalog prices are market references, not execution tariffs; only the two role routes carry verified execution profiles (free key, 0/0). **Unverified:** source usage-rights review. Real AWS S3 and Windows pass (next section, and the R11 Windows entry). The route map no longer pins a candidate: the dead `openrouter/nvidia/nemotron-3-super-120b-a12b:free` pin (upstream 404) was removed, and Gemma was replaced earlier the same day.

### Real AWS S3 on a Windows host (2026-10-26, PASS)

Windows 11 + WSL2, Docker Desktop 4.91.0 (8 CPUs, 15.6 GiB), Python 3.13.14, local Zetaris (`verify.sh` 9/9). Full record: [aws-registration-check.json](aws-registration-check.json). Zero model completions.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `scripts\preflight_windows.ps1` with Zetaris and Nightshift | PowerShell 7, venv Python | Machine/connectivity checks pass | PREFLIGHT CHECKS PASS, 0 FAIL/WARN/SKIP/UNKNOWN | PASS |
| `register_sources.py --storage data\source_examples\aws.oah.json --apply` | Bucket `cost-optimizer-oah-k7m2q`; read-only key in the publishing terminal | Publish, register, exact row checks | 9 objects published with S3 versions; 3 tables created (1 brief, 460 catalog, 3 models); no current pointer change | PASS |
| Same command repeated | Same | Everything reused | 9/9 objects and 3/3 tables reused | PASS |
| `check_zetaris_sources.py` typed reads | Zetaris API key only | SELECT 1, typed reads, catalog arithmetic | 4/4 pass; `nvidia/nemotron-3.5-lightning` 0.07 / 0.20 per 1M, `execution_tariff: false` | PASS |
| Same with `--round-trip --storage aws.oah.json` | Read-only key in terminal | Write/readback, append, restart, duplicate | 5/5 pass; 1 S3 evidence object, 2 fixture rows in Zetaris; first attempt without the key failed before any write | PASS |
| Per-bucket `fs.s3a` credentials in Zetaris `spark-defaults.conf` | Driver restarted | Table creation without a key | Ignored; driver fell through to the EC2 metadata endpoint. Reverted | FAIL, by design not used |

The Zetaris reader is a dedicated IAM user with an inline policy only: `GetBucketLocation`, `ListBucket` on prefix `cost-optimizer/v4/` and `GetObject` on `cost-optimizer/v4/*`; the IAM policy simulator denied everything else checked. Zetaris reads S3 file stores only with a key in the table `OPTIONS`, so the publisher adds it from `ZETARIS_S3_*` in its own process; Zetaris's metadata API returns that secret masked. This bundle used the earlier catalog-only route map; the live clean clone on 2026-10-27 (R11 below) registered the current one.

## M07 — Pinned real H-MEM and offline sample delegation

**Status: PASS for the local reference scope.** Checked October 25, 2026. The unchanged Meterless H-MEM TypeScript reference and conformance vectors are vendored at revision `1742dec56a66e58eef9dda2d2b865823758ca8cd`, with its lockfile and Apache 2.0 licence. `bridge.mjs` calls the reference's `add`, `query` and audit ledger; JSON-only responses include engine revision, scoped IDs, structured context and audit refs. Project IDs are validated and stored in separate hashed directories. The Python and sample adapters verify the real bridge and fail visibly for missing/broken setup.

| Check | Actual | Status |
|---|---|---|
| `npm test` in `app/engines/hmem/reference` | 10 reference tests passed | PASS |
| `./node_modules/.bin/tsx ../conformance/runner.ts` | 13/13 sponsor checks passed | PASS |
| `NODE_OPTIONS=--require=... node app/engines/hmem/bridge.mjs --selftest` | JSON status/revision, save/restart/recall/isolation/audit under Node network guard | PASS |
| `.venv/bin/python -m pytest -q -rs tests/test_hmem_engine.py tests/test_sample_memory.py` | 5 passed, no skips; includes a second Python process and malformed project ID | PASS |
| `.venv/bin/python scripts/check_sample_examples.py` | All three examples passed with Python and Node network guards | PASS |
| `.venv/bin/python -m pytest -q -rs` | 456 passed, 8 skips (all shelved retrospective); H-MEM no longer skipped | PASS |

The `tsx` CLI conformance run required sandbox escalation for its local IPC pipe; it passed after escalation. `npm ci` completed using the pinned lockfile and reported security advisories in development dependencies. No provider call was made. This is local reference evidence, not proof that accepted memory changes a later decision (M11), that JSON-file storage is safe for concurrent production use, or that the live sponsor workflow is ready. Manual instructions: M07 verification (manual guide to be folded into the operator manual).

## M08 — Nightshift response gate (superseded by R1 and R5)

**Status: PASS for the response gate; the live-pack acceptance moved to R1 and R5.** `parse_completion_response` requires a single text choice, a nonblank resolved model and response request ID, valid non-negative prompt and completion counts, and reasoning no greater than completion. It preserves raw usage, the winning-route model, provider, kind and receipt ID in the adapter, the feature sample and the durable dispatch record. The earlier branch `feature/plan-07-impl-meena` (`1f27731`) recorded standalone Nightshift/NVIDIA completions for Lightning (`rcpt_req_6vjuc0nt`) and Ultra (`rcpt_req_51o80g0a`) on 2026-10-25. The zero-spend preview, two-model validation subset and `scripts/check_m08_gate.py` remain available.

## R1: Planner and Critic role routes (2026-10-26, PASS)

Role routes are Lightning (Planner) and Ultra (Critic), both through Nightshift, per `docs/17`. The key behind them is a free NVIDIA Developer Program key (owner-confirmed; prototyping only; no per-token tariff published), so both profiles carry verified 0/0 rates and a cited `dispatch_policy`, kept in `data/source_examples/routes.selected.json`. Bundle `1dd75acc48e1eeefa91cc167` was registered (`current_pointer_updated: false`); the read-only gate shows both role routes `billing_gate: pass`. `tests/test_role_routes.py` covers the profiles; full suite 490 passed, 8 skipped.

Bounded probes, 2026-10-26, thinking on, answer text not retained: Lightning at 512 tokens resolved to the requested route (provider nvidia, 32/273/305 usage, receipt `rcpt_req_i150tjx5`); Lightning at 64 tokens returned `empty_response`; Ultra at 512 tokens resolved to the requested route (32/67/99, receipt `rcpt_req_z20cuec3`); Ultra at 48 tokens stopped at `finish_reason: length` with 48 completion tokens. These are single samples on observed usage, not a documented guarantee that `max_tokens` includes reasoning. They were sent outside the Dispatcher, so they are not the dispatcher-recorded sponsor receipts.

Superseded by the addendum below: the Dispatcher-recorded Planner and Critic calls were then run. `openrouter/nvidia/nemotron-3-super-120b-a12b:free` is advertised but returns an upstream 404 on completion and stays unverified; it is a candidate concern (R3/R4). Free-tier rate limits for the NVIDIA key are unknown.

**R1 addendum (2026-10-26): Dispatcher-recorded role calls.** With thinking on, the Lightning Planner failed three times through the Dispatcher with HTTP 502 `empty_response` (each recorded `unknown`, not retried, as designed), although the same prompt succeeded once on the raw adapter. With thinking off it completed. `NightshiftInference` now sends `chat_template_kwargs: {"enable_thinking": false}` for roles in `no_thinking_roles` (default `("Planner",)`); `tests/test_trace.py::test_thinking_is_off_only_for_the_configured_roles` covers it. One run, `r1-roles-1793027093855334000`, 768-token cap, 2 dispatches, spend $0 (free Developer Program key; 0/0 profile):

| Role | Requested = resolved model | Provider | Usage (prompt / completion) | Finish | Request ID |
|---|---|---|---|---|---|
| Planner | `nvidia/nemotron-3.5-lightning-30b-a3b` | nvidia | 51 / 20 | stop | `chatcmpl-f387ae3f-…` |
| Critic | `nvidia/nemotron-3-ultra-550b-a55b` | nvidia | 294 / 76 | stop | `chatcmpl-7227d0c3-…` |

Both dispatch records are `completed`. Limits: one sample per role; Lightning with thinking on stays unreliable, so any other path that calls it with thinking on may fail; free-tier rate limits are still unknown. Suite: 493 passed, 8 skipped.

**R1 billing basis (why the role profiles carry a $0 rate).** Sources read on 2026-10-26, kept here because the working notes are not committed:

- **Who bills:** Meterless (https://meterless.ai/) says a cloud provider you add "bills you directly, with your own key", and its page states no rate limits. So Nightshift is not the tariff source; the serving provider is. The Nightshift `/v1/models` listing (111 routes) is identity evidence only and does not say which provider or key serves a route.
- **NVIDIA entitlement:** the NIM product docs (https://docs.api.nvidia.com/nim/docs/product, page dated 2026-08-06) say Developer Program members have free access to NIM API endpoints for prototyping, that use is for prototyping, research, development and testing only, and that production needs an NVIDIA AI Enterprise licence (from $4,500 per GPU per year, a self-hosting price and not a per-token tariff). NVIDIA's public `GET /v1/models` listed 85 models including the Ultra and Lightning IDs, as identity only.
- **Key type:** the project owner stated on 2026-10-26 that the Nightshift NVIDIA key is a free Developer Program key. No screenshot or saved copy of the account terms was kept, so this rests on that statement plus the public entitlement text above.
- **What the profile claims:** a verified input and output rate of $0 per 1M tokens, a prototype-only label, a 100,000-byte prompt bound, a 2,048-token overhead (raised from 64 after the Lightning overrun) and a 1,024-token output cap (raised to 2,048 on 2026-10-26 after Ultra's natural A4 answer, with thinking off, filled 1,024 tokens; a bundle rebuild carries it). These bounds come from the probes and the R5 overrun, not from an NVIDIA document.
- **Not found:** per-token rates, hosted rate limits and fallback rules, cache, batch or request fees, and the token-counting method. `max_tokens` behaviour with hidden reasoning is inferred from single probes (Lightning 273 completion tokens for a 3-character answer; Ultra stopped at the cap), not from an official statement.
- **Market reference only (not a tariff):** OpenRouter's endpoint list showed third-party serving prices per 1M input/output tokens of about $0.40/$1.76 to $0.625/$3.125 for Ultra and $0.025/$0.12 to $0.07/$0.20 for Lightning. These show the spread behind the catalog figures and are never used to fill an execution rate.
- **Consequence:** the $0 rate holds only while the key stays a free prototyping key. A paid or production key needs a new profile from its own billing terms.

## R2: modality-aware catalog and contracts (2026-10-26, PASS for stated scope)

Changes: `CatalogModel` keeps `input_modalities`, `output_modalities` and `hugging_face_id` from the raw catalog (missing fields stay `None`, unknown, never "text only"; malformed values are rejected). `MarketReference` carries `input_modalities`, `output_modalities` and `open_weights_signal` (Hugging Face ID present), omitted from output when unset so the offline example outputs are unchanged. `FeatureProfile.modality` accepts `image_in` and `image_out` (additive, so `schema_version` stays 1.1 and the three examples are untouched; `docs/17` had proposed a bump). `covers_modalities()` maps a feature's modalities to the catalog capability it needs and returns unknown when the catalog is silent. `Controller._not_executable` classes image as not executable (`IMAGE_NOT_EXECUTABLE`), and `stage_cost_row` reports image cost as unknown ("image_in pricing is not modeled"), never zero.

Open-weights signal check against snapshot `a6cff78717992be3b332c65d` (460 rows, 180 with a Hugging Face ID): DeepSeek, Meta-Llama, NVIDIA, Tencent and other open labs carry it on every row; Anthropic, Amazon and xAI on none; OpenAI, Google, Qwen and Mistral are mixed. A reasonable proxy, not a licence finding.

Retained snapshots made before this change no longer validate, because validation re-normalizes the raw pages and compares bytes (error: "normalized catalog does not match the retained raw pages"). A migrated copy, same snapshot ID and raw pages, is at `data/localstack/openrouter/catalog-modalities/a6cff78717992be3b332c65d`; the original is untouched. A bundle built from it, `5fb26ad27f1b532eb2a02909` (460 catalog rows, 3 model rows), carries the fields on each row. It is **not registered** in Zetaris/LocalStack, so the live read path still serves the earlier bundle without them. Tests: `tests/test_modality.py` (20 cases); full suite 513 passed, 8 skipped; `scripts/check_sample_examples.py` passes all three examples.

Not done: no candidate selection uses the fields yet (R3), image tokens and per-image pricing are not modeled, and whether Nightshift passes image content is untested.

## R3a: per-feature, modality-filtered candidate selection (2026-10-26, PASS)

Code: `Controller._candidates` now returns the union of per-feature candidates and sets `feature_candidates` (feature ID to its own list). Eligible = Nightshift route (live), reference price present, catalog modalities cover the feature (unknown coverage kept and labeled, only an explicit miss excludes). Tiers: a curated route-map tier wins, otherwise open-weights signal gives open_source and the rest split by reference price (labeled proxy). One candidate per tier per feature; a verified rate and dispatch policy ranks first, then intelligence score, usage rank, snapshot order. `METERLESS_OPEN_MODEL` is an optional override (unknown or un-offered override stops before any paid call). Runs, pairs, projection and model stack use each feature's own list; a feature with no candidate gets an evidence gap, a question and `no_candidate_passes` rows. `ShortlistEntry.selected_for` lists the features a model was chosen for. `RouteMap` no longer requires one route per tier or a required open route; `scripts/prepare_source_bundle.py --include-discovered` registers every offered `openrouter/<id>` route that the catalog prices, with no tier. `routes.selected.json` now holds only the two role routes (Ultra frontier, Lightning mid-tier hints, verified profiles); the dead Super `:free` pin is removed.

Evidence: bundle `00455b55d8de993ebbf506c2` (460 catalog rows, 37 model rows) registered in LocalStack, `current_pointer_updated: false`, bindings `data/localstack/openrouter/bindings-wide.json`. Zero-completion preview through `check_openrouter_projection.py` (status `needs_input`: evaluation not approved, 0 dispatches): example 3, two text features, got Ultra, Lightning and `openrouter/deepseek/deepseek-v4-flash-0731`; example 1, A1 (audio in) got `google/gemini-3.7-flash` and `xiaomi/mimo-v2.5` (the routes whose catalog lists audio input), A2 and A4 (text) got the Ultra/Lightning/DeepSeek set, and A3 (audio out) got no candidate and the gap `candidates:A3_speak_target`. Suite 524 passed, 8 skipped; `scripts/check_sample_examples.py` passes; `tests/test_candidate_selection.py` adds 11 cases. Tests that encoded the pin were rewritten (`test_controller_live_fake.py`, `test_source_manifest.py`, `test_m08_gate.py`, `test_role_routes.py`).

The three tracked example outputs were regenerated (`SAMPLE_MODE=true`, isolated database). Besides the new `selected_for` field they also changed for earlier drift: the H-MEM bridge now works locally, so memory IDs appear and the "H-MEM unavailable" limitation is gone, and readiness gained an empty `dimensions` list.

Not done: R4. A live run still calls `validate_routes` on every chosen candidate, so a candidate without a verified profile (for example the DeepSeek open route) stops the run. Candidate quality is unknown, usage rank is the only tie-break for unscored models, and no execution has been tried on a derived candidate.

## R4: execute verified routes, project the rest (2026-10-26, PASS; exercised live in R5)

Code: `Controller._unproven_routes` asks the Dispatcher's own `validate_routes` about each chosen candidate. A candidate it would refuse (no verified route tariff or dispatch policy) is **projected only**: its feature runs carry `not_executed_reason` "projected only: <blocker>; tokens estimated, quality unknown", it is never passed to `_sample`, it adds an evidence gap `execution:<route>` and a limitation, and its stage-table rows stay estimated and are not recommended. The run-level stop now checks only the Planner and Critic routes (`validate_routes` is unchanged and not weakened). If a brief has executable features but every chosen candidate is projected only, the run ends `partial` with that reason and no candidate dispatch. Sampling counts only executable pairs.

Evidence: `tests/test_controller_live_fake.py` adds 5 cases (mixed executed and projected candidates; projected rows estimated, priced and never recommended; samples counted over proven pairs; all-unproven ends partial with no candidate dispatch; an unproven Planner or Critic still stops before any call). Suite 529 passed, 8 skipped. A zero-completion check against registered bundle `00455b55d8de993ebbf506c2` on example 3 selected Ultra and Lightning (executable), `openrouter/deepseek/deepseek-v4-flash-0731` (projected only, gap recorded), and both role routes passed the Dispatcher check.

Not done: no live run has executed a derived candidate, so how an executed pair behaves end to end on this data is untested until R5. Projected-only rows carry no quality evidence by design.

## R5: first bounded live pack (2026-10-26, PASS; clean pack `r5-live-20261026-113150-e`)

Request: example 3 (two text features), `sampling_profile: validation` (one sample per pair), `max_spend_usd: 0.50`, fresh run ID, isolated database, registered bundle `87f8564d36ffd17330015ad3` (37 model rows, bindings `data/localstack/openrouter/bindings-wide2.json`). Roles Planner = Lightning, Critic = Ultra. Selected per feature: Ultra and Lightning (executed) and `openrouter/deepseek/deepseek-v4-flash-0731` (projected only). Artifacts, all under gitignored paths: `data/localstack/r5/pack4.json`, `data/localstack/r5/runs4.db`, `logs/trace-r5-live-20261026-112757-d.jsonl`, request `data/localstack/r5/request4.json`.

Result of run `r5-live-20261026-112757-d`: 6 dispatches, all `completed`, spend $0 (free Developer Program key, 0/0 profiles). Planner and Critic resolved to the requested Lightning and Ultra routes; the four candidate pairs (2 features x Ultra, Lightning) each have one measured sample (for example `summarize_notes`: Ultra 1912 in / 450 out, Lightning 1864 / 136). The DeepSeek rows carry "projected only" and an evidence gap and were never dispatched. Rubric: `summarize_notes` Ultra failed `has_summary_and_actions` and `concise`, Lightning passed both; the other checks are human review and pending, so every model-stack row is `no_candidate_passes` (a correct result, not a recommendation). The Critic flagged 4 findings and proposed an output cap, which the controller rejected; it shares Ultra with a candidate and says so. No quality claim is made.

Zetaris evidence round trip: during the run no publisher was listening, so 5 records stayed in the local outbox and the controller correctly demoted the pack from `complete` to `partial`. Afterwards a loopback publisher (`scripts/serve_source_ingest.py`, throwaway token held in the shell, not `.env`) and `scripts/retry_evidence.py` replayed all 5 records: 5 published, 0 pending, readback identity and SHA matched the stored payloads, 0 model completions. The retained pack was not rewritten, so it still reads `partial`.

Earlier attempts the same day, kept as negative results (all $0): (1) `r5-live-20261026-112305` stopped `overrun`: Lightning measured 945 prompt tokens for a 639-byte prompt against a bound of 703 (Ultra counted 141 for the same prompt), so both profiles' `prompt_overhead_tokens` went from 64 to 2048 and the bundle was rebuilt; the cause (likely structured-output text added server-side) is not confirmed. (2) `r5-live-20261026-112434-b` stopped on an Ultra `ReadTimeout` at 60 s (it normally takes about 21 s); `METERLESS_REQUEST_TIMEOUT_S` now sets the timeout, default still 60. (3) `r5-live-20261026-112620-c` stopped when the Critic, with thinking on, used the whole 1,024-token cap (`NonStopFinish`); roles can now run with thinking off through `METERLESS_NO_THINKING_ROLES` (default Planner), and this run used Planner and Critic. Lightning also needs `METERLESS_NO_THINKING_MODELS=nvidia/nemotron-3.5-lightning-30b-a3b`, because with thinking on it returned `empty_response` in 5 of 7 calls. All three settings were passed on the command line for this run, are optional, and are documented in `.env.example`; none are in `.env`.

Not done or unproven: the `partial` pack was not re-run with the publisher up, so no retained pack is `complete` with in-run evidence IDs; sponsor `readiness` stays `not_verified` because it is set by `scripts/smoke_live.py`, not this run; the Critic and Planner calls ran with thinking off, so no claim is made about their behaviour with thinking on; free-tier rate limits are unknown; one sample per pair is too small for any quality conclusion; image and audio features were not run. Suite: 538 passed, 8 skipped.

**R5 addendum (2026-10-26): clean pack.** Run `r5-live-20261026-113150-e` repeated the request with the loopback evidence publisher running (throwaway token held in the shell, not `.env`; stopped afterwards) and the same command-line settings (`METERLESS_NO_THINKING_MODELS` Lightning, `METERLESS_NO_THINKING_ROLES=Planner,Critic`, `METERLESS_REQUEST_TIMEOUT_S=150`), bundle `87f8564d36ffd17330015ad3`. Result: status **complete**, 6 dispatches all `completed`, spend $0, `unpublished_evidence_ids` empty, one H-MEM memory ID saved. Planner and Critic resolved to Lightning and Ultra; four candidate pairs measured (`summarize_notes`: Ultra 2092 in / 453 out, Lightning 2095 / 136; `weekly_digest`: Ultra 790 / 148, Lightning 790 / 60); DeepSeek projected only with its gap and never dispatched. The Critic flagged 4 findings and its proposed cap was rejected by the controller; every model-stack row is `no_candidate_passes` (human-review checks pending). Artifacts (gitignored): `data/localstack/r5/pack5.json`, `data/localstack/r5/runs5.db`, `logs/trace-r5-live-20261026-113150-e.jsonl`. The earlier `partial` pack and its replay (`…112757-d`) stay as the record of the publisher-down case.

Same limits as above: one sample per pair, thinking off for Planner and Critic, rate limits unknown, sponsor `readiness` still set only by `scripts/smoke_live.py`, no image or audio feature run. This pack is evidence the pipeline works, not a model recommendation.

## R11a: live smoke check on Planner and Critic (2026-10-26, PASS at diagnostic scope)

`scripts/smoke_live.py` was changed to check the hackathon roles, not tiers: one tiny completion each for the Planner (`METERLESS_MODEL`) and Critic (`METERLESS_CRITIC_MODEL`) routes, six required checks. Tests updated in `tests/test_smoke_live.py`; suite 539 passed, 8 skipped.

| Command | Setup | Result |
|---|---|---|
| `ZETARIS_BINDINGS_FILE=data/localstack/openrouter/bindings-wide2.json METERLESS_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b METERLESS_CRITIC_MODEL=nvidia/nemotron-3-ultra-550b-a55b METERLESS_REQUEST_TIMEOUT_S=150 python scripts/smoke_live.py --max-spend-usd 0.10 --output-dir data/localstack/smoke-r11b` | Local Zetaris/LocalStack, Nightshift with the free NVIDIA Developer Program key, pinned H-MEM bridge; requests through the durable Dispatcher | 6 pass, 0 fail, 0 skip; diagnostic readiness `ready` |

- Zetaris `SELECT 1` and a typed read of 37 model rows; Nightshift discovery listed 111 routes.
- Planner: requested and resolved `nvidia/nemotron-3.5-lightning-30b-a3b`, request ID `chatcmpl-d83e206c-d601-4cf6-9840-a3b732f38eb9`, usage prompt 29 / completion 2.
- Critic: requested and resolved `nvidia/nemotron-3-ultra-550b-a55b`, request ID `chatcmpl-1cebb341-c2bf-4dad-b567-dae7e8f346af`, usage prompt 29 / completion 2.
- Accounting: 2 dispatches, spend $0, reserved $0, both operations `completed`. The H-MEM bridge self-test passed (pinned revision `1742dec5`).
- Readiness dimensions in the JSON: route discovered pass, route registered pass, execution available pass, billing verified `not_verified`, evidence readback `not_verified`.
- An earlier run without the bindings file failed `read_models`, and one without role routes skipped both completions (`incomplete`); both are expected setup outcomes, not defects.

Not established: end-to-end sponsor readiness, billing (the $0 rate rests on the owner's confirmation of a free key), evidence readback in this run (proved in R5), quality (thinking off, 8-token cap), Windows. Report files are under `data/localstack/smoke-r11b/` (gitignored).

## R10: Streamlit workflow, first version (2026-10-26, PARTIAL)

Added `streamlit_app.py`, `app/ui_service.py`, `tests/test_ui_service.py` and `tests/test_streamlit_app.py`; `data/ui/` is gitignored. The UI holds no business rules: it builds a `RunRequest` from the form (an example is the starting template), runs `run.py` as a subprocess (the CLI's own entry point), and renders the saved pack.

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_ui_service.py tests/test_streamlit_app.py` | 11 passed (now including a live-shaped pack showing market costs, pending human review and Critic flags): all three examples round-trip through the form to a valid request; edits and new feature rows reach the request; an invalid form is reported, not raised; a run ID runs once and the second call loads the stored result; run IDs are validated; the app (Streamlit `AppTest`) runs a sample request, shows `SAMPLE/OFFLINE`, shows status `complete` and spend 0, and a rerender creates no new files |
| `python -m pytest -q` | 554 passed, 8 skipped |
| `python -m streamlit run streamlit_app.py --server.headless true` | Server started and `/_stcore/health` returned `ok` |

**Trimmed scope (decided 2026-10-26):** five views only. (1) Cost by stage: each feature's monthly cost per model at the dated OpenRouter market price (`openrouter_projection_tables`), measured tokens where a model ran and estimated where it is projected only; sample packs fall back to placeholder stage tables, labeled. (2) Measured versus estimated tokens. (3) Quality checks: deterministic pass/fail, human review pending, Critic flags. (4) Risks, limitations, evidence gaps, with the build panel collapsed. (5) Trace table and pack/trace downloads. Hidden: the actual-route tables (they show $0 on the free key), the model stack (empty until human review exists), lever drill-down and the full shortlist. A stopped run shows the trace's stop reason and a setup hint; Live mode takes the Zetaris bindings file in the sidebar.

Rendering the R5 pack `r5-live-20261026-113150-e` through the app: no exception; `summarize_notes` at Scale shows Ultra $1,545.98, Lightning $114.74 (measured tokens) and DeepSeek $65.58 (estimated, projected only), all lower bounds at market reference price.

**Adapter fix found while trimming:** in R5, Ultra (thinking on) returned its reasoning inside the content, closed by `</think>` with no opening tag, so the JSON rubric check failed on prose. `parse_completion_response` now keeps only the text after the last `</think>`; usage and billing are unchanged (reasoning is already inside completion tokens). Re-checking the retained Ultra output gives a JSON object with `summary` and `action_items`. Test: `tests/test_nightshift_adapter.py` (4 new cases). Not yet confirmed by a new live run.

Not done: aggregate stage totals and budget fit (R9); human-review controls and accepting a decision (R7); memory changes (R8); a live run from the UI was not tried; the screens were not looked at in a browser by a person, only exercised through `AppTest` and a health check; modality entry is a comma-separated text column.

### R10 live run from the UI (2026-10-26, PASS)

Driven through the app with Streamlit `AppTest` (Live mode, Example 3, bindings `data/localstack/openrouter/bindings-wide2.json`, approval ticked, $0.50 cap, evidence publisher running), with `METERLESS_MODEL` (Lightning), `METERLESS_CRITIC_MODEL` (Ultra), `METERLESS_NO_THINKING_ROLES=Planner,Critic`, `METERLESS_NO_THINKING_MODELS=nvidia/nemotron-3.5-lightning-30b-a3b` and `METERLESS_REQUEST_TIMEOUT_S=150` set before launch.

- Run `ui-20261026-144257`: status `complete`; 10 dispatches (Planner, 8 candidate samples at two per pair, Critic), all `completed` with requested equal to resolved model; spend $0, reserved $0; `unpublished_evidence_ids` empty; one H-MEM memory saved.
- The adapter fix is confirmed live: Ultra's `summarize_notes` output (thinking on) now passes `has_summary_and_actions` and `concise`, as does Lightning's. Human-review checks stay pending, so no model is recommended.
- The UI showed cost by stage at market price (`summarize_notes` at Scale: Ultra $1,547.17 and Lightning $114.74 from measured tokens; DeepSeek $65.58 estimated, projected only), measured versus estimated tokens, four Critic `token_gap` flags and the trace.
- A first attempt, `ui-20261026-144146`, ended `partial` because `METERLESS_NO_THINKING_MODELS` was not set: Lightning, with thinking on as a candidate, used all 1,024 output tokens, the receipt was `unknown` and spending stopped after 4 dispatches ($0). Kept as a negative result; the setting is required for Lightning.

### R10 live run with founder-picked candidates (2026-10-26, PASS)

Added `candidate_models` (optional, 1-3 unique routes) to the request, a controller path that uses the picks instead of the automatic choice while keeping its checks (unknown, un-offered or router-alias route, or two picks in one tier, stop the run before any paid call; a pick that can't handle a feature's modality is skipped for that feature), and a dropdown in the UI. Tests: `tests/test_candidate_selection.py`, `tests/test_v4_contracts.py`, `tests/test_ui_service.py`; suite 570 passed, 8 skipped.

Driven through the app (`AppTest`, Live, Example 3, same settings and publisher as the earlier UI run) with picks Ultra, Lightning and `openrouter/qwen/qwen3.8-27b` (the automatic open-source choice would have been DeepSeek):

- Run `ui-20261026-153312`: `complete`; 10 dispatches, all `completed`, requested equal to resolved; spend $0; no unpublished evidence; one memory saved. The request carried the three picks; the pack lists them as "chosen by the founder" and records the limitation that automatic selection was not used.
- Qwen was projected only (no verified dispatch policy): `summarize_notes` at Scale $713.99 from estimated tokens at market reference price, beside Ultra $1,547.17 and Lightning $114.74 from measured tokens.
- Not shown: tier clashes are only reported at run time, because the dropdown does not know each model's derived tier.

## R9: stage totals, revenue and budget fit (2026-10-26, PASS for stated scope)

Plan Step 12, findings F11 (rest) and F12. `StageTotal` and `DecisionPack.stage_totals` added (schema 1.1, additive); `stage_totals` in `app/economics.py`; the controller fills it after projection and no longer records the "budget fit is unknown" limitation.

- **Three ways of choosing models**, each summed across all features per stage: the recommended stack (quality-qualified only), the cheapest known candidate per feature (cost only, quality not checked) and one model for every feature it was a candidate for. Computed separately for the actual-route tables and the OpenRouter listed-price projection; the two are never mixed.
- **Unknown stays unknown:** a feature with no known cost makes the total incomplete and a lower bound, names the missing feature, and is never counted as zero. A lower-bound row makes the total a lower bound.
- **Revenue** = stage active users × paying fraction × subscription price (the paying fraction applies to active users). **AI contribution** = revenue − AI cost (an upper bound when the cost is a lower bound); **margin** = contribution ÷ revenue when revenue > 0; missing revenue shows costs only. AI-only: other operating costs and one-time build costs are excluded.
- **Budget fit:** `over` when the total, even a lower bound, exceeds the ceiling; `within` only when the total is complete and not a lower bound; otherwise `unknown`; `no_budget` without a ceiling.
- **UI:** price per paying user and paying fraction inputs; a "Monthly AI cost, all features together" table and chart at the top of Cost by stage, with the first stage over budget called out.

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_stage_summary.py` | 15 passed: known totals, recommended-only totals, unknown costs never zero, non-candidate features, budget crossings, lower bound under and over budget, paying fraction of stage users, 0% and 100% paying, missing revenue, separate pricing scopes, Decimal rounding once. The first run caught a defect (rows keyed without the stage, so later stages overwrote earlier ones), fixed before recording |
| `python -m pytest -q tests/test_ui_service.py tests/test_streamlit_app.py` | 17 passed, including revenue inputs and a sample run showing totals |
| `python -m pytest -q` | 587 passed, 8 skipped |
| `python scripts/check_sample_examples.py` | Examples 1–3 PASS after regenerating `output_examples/` |

Recomputed offline from the live UI pack `ui-20261026-153312` (assumed $15 price, 8% paying, $300 budget): at Scale, all features on Ultra $1,747.68 (budget `over`), all on Lightning or cheapest per feature $129.93, all on Qwen $969.85 (`over`); every market-price total is a lower bound, so totals under the ceiling read `unknown`, not `within`. The recommended-stack total is unknown at every stage because no model is qualified until human review exists (R7).

### R9 live run from the UI (2026-10-26, PASS)

Driven through the app (`AppTest`, Live, Example 3, automatic candidates; budget $300, price $15, paying fraction 0.08; same settings and evidence publisher as the earlier UI runs). Run `ui-20261026-154913`: `complete`, 10 dispatches all `completed` with requested equal to resolved, spend $0, no unpublished evidence, one memory saved, totals in the pack.

Monthly AI cost for both features together at the OpenRouter listed price (all lower bounds), Scale stage: cheapest per feature $80.77 (DeepSeek, estimated, $65.58 for `summarize_notes`; Lightning, measured, $15.19 for `weekly_digest`); all on Ultra $1,746.10, budget `over`; all on Lightning $129.93; all on DeepSeek $85.28 (estimated, projected only). Revenue at Scale $60,000; AI margin 97.1% (Ultra) to 99.9%. Totals below the ceiling read `unknown` because every market-price total is a lower bound. The totals dropdown was changed to plain text options so every choice can be exercised in tests.

### Live UI run with picks on Example 1, and the Ultra thinking fix (2026-10-26)

- **Failed run `ui-20261026-155047`** (Example 1; picks Ultra, DeepSeek V4 Pro, Muse Spark): Ultra as a candidate, with thinking on, used all 1,024 output tokens on a feature in 43 s; the receipt was `unknown` and spending stopped (`partial`). The evidence publisher was also not running. Kept as a negative result: Ultra needs thinking off as a candidate on harder tasks, as Lightning did.
- **Re-run `ui-20261026-155532`** with `METERLESS_NO_THINKING_MODELS` listing both Lightning and Ultra and the publisher running: `complete`, 6 dispatches all `completed`, requested equal to resolved, spend $0, no unpublished evidence, one memory saved.
- No pick covers the two audio features (`A1` audio in, `A3` audio out): each is skipped with a limitation, so every total is incomplete and names them. Monthly totals at Scale for the two text features, OpenRouter listed price, lower bounds: all on Ultra $16,013.51 (measured), all on DeepSeek V4 Pro $6,419.29 and all on Muse Spark $678.70 (both estimated, projected only).
- **Finding:** measured input tokens include the instructions sent with each example (A2: 426.5 measured against 15 estimated), while the 4/3-rule estimate counts only the example text. Projected-only rows therefore understate input cost against measured rows; at Scale, Ultra's A2 input line is $12,283.20 of $15,412.32. Not fixed; stated here and in the UI's measured-versus-estimated view.

### Estimate counts the instructions sent with each call (2026-10-26)

`estimate_feature_tokens` now adds the 4/3-rule count of the instructions the controller sends with each example (`Controller._prompt`) to the static prefix and the example input; the controller passes them to the run estimates, the actual-route stage tables and the OpenRouter projection, so projected-only rows use the same basis. Method label: "4/3 words rule (instructions + example)". Tests: `tests/test_stage_economics.py` (unit) and `tests/test_ui_service.py` (a sample run's estimates equal prefix + instructions + example). `output_examples/` regenerated; sample checker PASS for Examples 1–3; suite 589 passed, 8 skipped.

Effect against the measured runs (input tokens per call, estimate before → after, measured): Example 1 `A2` 15 → 121, measured 426.5; `A4` 530 → 578, measured 1,698.5; Example 3 `summarize_notes` 1,234 → 1,334, measured 2,095; `weekly_digest` 815 → 867, measured 815.

**Still open:** the gap is smaller but not closed, and it is not explained. Two known mismatches remain: (1) measured runs do not send the founder's assumed `static_prefix_tokens`, while estimates include them (Example 3 assumes 1,200 and 800); (2) measured counts are higher than the 4/3 rule on the sent text by an amount that varies by feature (about 300 to 1,100 tokens here), which may be tokenizer behaviour or text added before the model; a one-word smoke prompt measured 29 tokens. Not investigated further; estimated rows remain labeled estimated and lower bounds.

### Example 1 live UI run and an identical-output finding (2026-10-26, run complete; finding OPEN)

Run `ui-20261026-164648` (Example 1, automatic candidates, thinking off for both Nemotron routes, publisher running): `complete`, 10 dispatches all `completed` with requested equal to resolved, spend $0, no unpublished evidence, one memory saved. Totals incomplete: no candidate covers `A1` (audio in) or `A3` (audio out).

- **Nightshift offered 74 routes instead of 111.** The `openrouter/...` routes were missing, so only the two Nemotron routes were eligible: no open-source candidate for the text features and no audio-input candidate for `A1` (an earlier run, `ui-20261026-162348`, had Gemini 3.7 Flash and MiMo v2.5 for `A1` and DeepSeek for the text features). The app handled the change correctly; the cause is on the Nightshift side and was not investigated.
- **OPEN: identical outputs from different models.** With thinking off, Ultra and Lightning returned byte-identical text for `A4` (2,598 characters, 714 completion tokens, ending mid-sentence) in every sample of three runs (`155532`, `162348`, `164648`), and identical `A2` text in several samples, each with its own receipt, request ID and 7–10 s latency. Two different models producing the same 2,598 characters is implausible, so either Nightshift serves both route IDs from one backend when thinking is off, or a response cache returns earlier text. Until explained, Ultra-versus-Lightning measured differences under thinking off are not evidence of model differences; the requested-equals-resolved check relies on Nightshift's own report. With thinking on for Ultra (Example 3, `154913`), outputs differed.

### Probe: cause of the identical outputs (2026-10-26, cause FOUND; fix OPEN)

Eight requests through the Dispatcher on the free key ($0), thinking off for both Nemotron routes; scripts kept outside the repository.

| Probe | Result |
|---|---|
| Example 1 `A4` prompt, Ultra and Lightning, with and without a random tag in the system prompt | All four identical: 714 output tokens, 2,598 characters, fingerprint `78e5b24004` (same as the earlier runs), 6–13 s each |
| Same prompt, random tag in the user message, both routes | Both identical again (`78e5b24004`) |
| A new prompt (fictional lighthouse keeper), both routes | Different answers: Ultra 82 tokens, Lightning 105 tokens. The two route IDs are distinct models |
| `A4` prompt on Lightning with Nightshift's full receipt captured | `cache.status: miss`, `from_cache: false`; **`hmem: injected 1, reason "retrieved 1 memories", top_score 0.88`**; `context_sources: ["messages", "hmem:1 records"]`; provider input 1,542 tokens |

**Cause:** Nightshift's own memory layer (requests carry `meterless-scope: user`) retrieves a stored record for a similar prompt and injects it into the request before it reaches the model. Both models then reproduce the injected earlier answer. This is Nightshift's built-in memory, separate from the app's H-MEM engine (`app/engines/hmem/`).

**Consequences for every live measurement so far:** (1) measured input tokens include injected memory text, which explains much of the unexplained gap between measured and estimated input; (2) outputs, and so output tokens and rubric results, can be copies of earlier answers rather than the model's own work, so Ultra-versus-Lightning measured differences are not reliable evidence; (3) results can depend on earlier runs. Identity (requested equals the answering route) is still correct.

**Fix needed (open):** evaluation requests must run without memory injection. The adapter sends `meterless-scope: user`; the documented way to turn injection off was not found in the repository. Next: confirm the switch in the Nightshift documentation or with the Meterless team, then re-run the measurements.

### Fix: a unique `meterless-scope` per request (2026-10-26, PASS)

Probe first (two requests, `A4` prompt): with a unique scope, Nightshift's receipt showed `hmem: null` and context `["messages"]` only; input fell from 1,542 to 751 tokens; Ultra and Lightning gave different answers (996 and 363 output tokens). The adapter now sends no fixed `meterless-scope` and gives every request `eval-<random>` (`app/adapters/live_nightshift.py`); test `tests/test_trace.py::test_every_request_gets_its_own_meterless_scope_so_no_memory_is_shared`; suite 594 passed, 8 skipped.

Re-run from the UI, Example 1, run `ui-20261026-165715`: `complete`, 10 dispatches, $0, no unpublished evidence. Measured input per call now sits close to the estimate (A2: 142 measured, 121 estimated; A4: 751 measured, 578 estimated), and A4 outputs differ by model and by sample (Ultra 785 and 1,015 tokens; Lightning 475 and 556). Totals at Scale for the two text features, OpenRouter listed price, lower bounds: all on Ultra $6,973.69, all on Lightning or cheapest per feature $717.48 (before the fix: $9,926.27 and $1,076.86).

**Earlier live measurements are affected.** R5 and every UI run before `ui-20261026-165715` ran with the shared `user` scope, so their measured input tokens may include injected memory and their outputs may repeat earlier answers. Their dispatch, spend, identity and evidence results stand; their token, cost and quality numbers should be re-measured before being quoted.

**Watch:** Ultra used 1,015 of the 1,024 output tokens on one A4 sample with thinking off; a longer answer would hit the cap and stop the run as `partial`.

### Example 3 re-measured after the scope fix (2026-10-26, PASS)

Run `ui-20261026-170134` (UI, Live, Example 3, automatic candidates, budget $300, price $15, paying 0.08): `complete`, 10 dispatches all `completed` with requested equal to resolved, $0, no unpublished evidence, one memory saved. Nightshift still offered 74 routes, so only Ultra and Lightning were candidates.

| Feature, model | Input per call (measured / estimated) | Output per call (measured / estimated) | Automated checks |
|---|---|---|---|
| `summarize_notes`, Ultra | 141 / 1,334 | 147, 150 / 334 | both pass |
| `summarize_notes`, Lightning | 141 / 1,334 | 136, 128 / 334 | both pass |
| `weekly_digest`, Ultra | 86 / 867 | 36, 27 / 400 | none defined |
| `weekly_digest`, Lightning | 86 / 867 | 44, 44 / 400 | none defined |

Totals for both features at the OpenRouter listed price (lower bounds), Scale: all on Ultra $319.04 (budget `over`), all on Lightning or cheapest per feature $27.20; AI margin 99.47% and 99.95% against $60,000 revenue. Before the fix the same run measured $1,746.10 and $129.93. The Critic flagged four token gaps and two output-format differences.

**New finding (open, not changed):** the estimate now exceeds the measurement because it includes the brief's assumed production system prompt (`static_prefix_tokens`: 1,200 and 800), which evaluation calls do not send. Measured rows therefore leave out that assumed prefix and may understate a production app that sends one; adding the assumed prefix to measured input in projections is a modelling decision for the team.

### OpenRouter provider restored; Example 1 with cross-lab candidates (2026-10-26, PASS)

After the OpenRouter key was added in Nightshift, one request to `openrouter/google/gemma-4-31b-it:free` (outside the Dispatcher, as a provider check; returned an upstream `429` rate limit, no completion, no charge) triggered key verification. `GET /v1/models` then listed 111 routes (37 `openrouter/...`), and all 37 registered price rows were offered again.

Run `ui-20261026-172053` (UI, Live, Example 1, automatic candidates): `complete`, 10 dispatches all `completed` with requested equal to resolved, $0, no unpublished evidence, one memory saved. Candidates: `A1` Gemini 3.7 Flash and MiMo v2.5 (projected only; cost unknown, not zero, because the catalog gives no per-second audio conversion); `A2` and `A4` Ultra and Lightning (measured) and DeepSeek V4 Flash (projected only); `A3` none (no audio-output route). Totals at Scale for the two text features, OpenRouter listed price, lower bounds: all on Ultra $6,877.86, all on Lightning $712.60, all on DeepSeek (estimated) $681.42, which is also the cheapest per feature. Display nit: projected-only feature rows show no tier, because a derived tier is not copied onto the run row.

### Candidate tiers on run rows (2026-10-26, PASS)

The controller records the tier each candidate was chosen for in each feature (curated, or derived by the rules) and uses it for run rows, actual-route stage rows and OpenRouter projection rows. Test: `tests/test_candidate_selection.py::test_derived_tiers_are_recorded_per_feature_for_the_run_rows`. Live check without approval (Example 1, 0 dispatches): Gemini 3.7 Flash frontier, MiMo v2.5 open-source, Ultra frontier, Lightning mid-tier, DeepSeek V4 Flash open-source. Sample checker PASS for Examples 1–3. Suite 595 passed, 8 skipped.

## R8: memory carries founder inputs into a later run (2026-10-26, PARTIAL)

Code: a completed run saves the budget, price per paying user and paying fraction its own brief stated, with each field's evidence status, as H-MEM kind `founder_input` (alongside the existing `accepted_finding`). The next run of the same project recalls them and fills only fields its brief leaves empty, using the newest value per field. The status is kept, never upgraded; the founder's current input wins; the fill is traced as `hmem_apply` and listed in `limitations` with the source run. Before this change the run saved `accepted_finding` but recalled `confirmed_constraint`, which nothing wrote, so a later run always recalled 0 memories.

Evidence: `tests/test_hmem_founder_inputs.py` (real bridge, network blocked): run 2 with blank fields reproduces run 1's revenue per stage; a current value overrides memory; another project recalls nothing. Sample CLI check on `example_3`: with blank fields and run 1's memory, stage totals gain revenue, AI margin and budget fit (Scale `over` at a 40 USD budget); without memory they have none. The evidence-gap count is unchanged (38), because recalled values keep their original status. A headless drive of the Streamlit UI on `main` (`b9f92df`) showed the same result, the recalled note and the H-MEM trace step.

Not done: memory does not change candidate selection or the model stack, and accepted findings are saved but not read back into a decision.

## R11: clean-clone rehearsal on a second machine (2026-10-26, PASS in sample mode)

The team cloned the repository on a second machine and followed only the README's sample-mode steps. Reported as done by the team; the machine, OS, Python version and test output were not recorded here, and no artifacts from that machine are retained.

Not rehearsed on the second machine: live mode (re-collecting and re-registering sources, Zetaris, Nightshift and the evidence publisher) and Windows. Video and deck are still open.

### R11: live clean clone on Windows with real AWS S3 (2026-10-27, PASS after two fixes)

A fresh clone of `main` at `5cd41e4` on Windows 11 (WSL2, Docker Desktop, Python 3.13.14 because 3.12 is not installed, Node 24), set up from the README only: Quick start, Level 1, "Test live from start" and Level 2. Prices were registered on the real AWS bucket instead of LocalStack, and the UI ran live. Full record: [windows-clean-clone-rehearsal.json](windows-clean-clone-rehearsal.json).

| Step | Expected | Actual | Status |
|---|---|---|---|
| `pip install`, `npm ci`, `pytest -q -rs`, `check_sample_examples.py` | Suite passes; three examples PASS | 621 passed, 8 skipped (shelved retrospective; the real H-MEM test ran); 3 of 3 PASS | PASS |
| `collect_sources.py` | Catalog collected | 457 accepted, 7 quarantined of 464 | PASS |
| `discover_source_routes.py` | Routes listed, no completion | 128 routes (42 `openrouter/`, 13 `nvidia/`, 55 `local-runtime`, 18 `meterless/`); 86 before the OpenRouter key was added | PASS |
| `prepare_source_bundle.py --include-discovered` | Bundle with every priced route | `cd08406389b3f3d4dc555621`: 1 brief, 457 catalog rows, 44 models | PASS |
| `register_sources.py ... aws.oah.json --apply` | Publish and register | First attempt: bare `FileNotFoundError` before any upload, because `.env` named the bindings file this step creates (fixed in `cf209eb`). Then 9 objects published, 3 tables created, no pointer change | PASS after fix |
| `check_zetaris_sources.py --round-trip` on AWS | 5 checks | 5/5 pass, 0 completions | PASS |
| `check_m08_gate.py` | README says `ready_for_bounded_dispatch` | `incomplete`: the committed route map is `planned`. Both routes discovered, registered and `billing_gate: pass` | OPEN |
| `smoke_live.py` | Zetaris, Nightshift, H-MEM pass | 4 pass, 2 paid checks skipped by default (44 model rows, 128 routes) | PASS |
| Streamlit live, Idea C · Writing, then Idea A · Speech | Complete, $0, evidence written back | Both `complete`: 10 requests each, $0, 9 evidence records written back and read back each, empty outbox, Planner Lightning and Critic Ultra resolved as requested. The second idea's result was hidden behind the first one's (fixed in `c6e9d35`) | PASS after fix |

The publisher wrote with short-lived `aws login` credentials; Zetaris read with the read-only `zetaris-s3-reader` key, typed into masked prompts for that terminal only. Streamlit and the publisher listened on `127.0.0.1` only. The idea label "Idea 3" was renamed "Idea C" (`9cff702`).

## Live proof runs, published (2026-10-27, PASS)

Four live runs on application code identical to `main` at `1bdc9c7`, 02:37–02:41 UTC, via `run.py` with the evidence publisher running: `live-ex1-`, `live-ex2-`, `live-ex3-` and `live-ex3-recall-20261027T023748Z`. All ended `complete` with $0 spend and an empty outbox (10, 14, 10 and 10 model requests; 9, 13, 9 and 9 evidence records written to Zetaris and read back). Every Planner request resolved to `nvidia/nemotron-3.5-lightning-30b-a3b` and every Critic request to `nvidia/nemotron-3-ultra-550b-a55b`, with provider request IDs. Only the two Nemotron routes were executed; other-lab candidates were projected only. The Critic raised `token_gap` flags on Examples 1 and 2 and `unsupported_claim` flags on Example 3. The recall run left budget, price and paying fraction blank and recalled them from the `live-ex3-` run (`hmem_apply`), so its stage totals carry revenue, margin and budget fit. Requests, packs and traces are in `output_examples/live/` with a summary README; the only edit is the trace path inside each pack. `smoke_live.py` passed for Zetaris, discovery (111 routes) and the H-MEM self-test just before.

Not shown: quality qualification (human review pending) and measured candidates from other labs. A second machine and Windows are covered by the R11 Windows entry above.

