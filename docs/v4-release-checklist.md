# v4 evidence ledger and release checklist

Updated 2026-10-26. The step-by-step plan and findings table are in [08-v4-Implementation-Plan.md](08-v4-Implementation-Plan.md), and the candidate, billing and NVIDIA revisions are in [17-v4-Revised-Implementation-Steps.md](17-v4-Revised-Implementation-Steps.md); this file records what was actually run and what it showed, including negative results. A PASS applies only to its stated scope. Planned tests and required integration skips are never converted into PASS results. New entries append the exact command, environment, expected and actual result, revision and artifact path.

## Current status

| Step | Status | Where |
|---|---|---|
| M00 Baseline and recovery inventory | PASS, scoped | below |
| M01 Input contracts and founder controls | PASS, scoped | below |
| M02 Composed cost levers | PASS, scoped | below |
| M03 Trace evidence and truthful readiness | PASS, scoped (Windows unverified) | below |
| M04 Bounded dispatch, spend and restart safety | PASS, scoped | below |
| M05–M06 Source pipeline and Zetaris evidence round trip | PASS for components; usage-rights review and real AWS/IAM unverified | below |
| M07 Real H-MEM, offline delegation | PASS, local reference scope | below |
| M08 Nightshift identity and first live pack | Superseded by R1 and R5, both PASS | below |
| R0 Requirement split | Decided and written into `07` v4.3 and `CLAUDE.md`; Narin sign-off and the official rule quote still open | `07` §4, `docs/17` §2 |
| R1 Planner and Critic role routes | PASS | below |
| R2 Modality-aware catalog and contracts | PASS | below |
| R3a Per-feature candidate selection | PASS | below |
| R4 Execute verified routes, project the rest | PASS | below |
| R5 First bounded live pack | PASS (clean pack `r5-live-20261026-113150-e`) | below |
| R11a Live smoke check (Planner and Critic) | PASS, diagnostic scope (2026-10-26) | below |
| R6 Task planning, grounded critique (was M09) | Not started | plan Step 9 |
| R7 Review binding, effective repair (was M10) | Not started | plan Step 10 |
| R8 Memory changes a later run (was M11) | Not started | plan Step 11 |
| R9 Stage totals, revenue, budget fit (was M12) | Not started | plan Step 12 |
| R10 Streamlit workflow (was M13) | Not started | plan Step 13 |
| R11 Release rehearsal (was M14) | Not started | plan Step 14 |

## Open items and caveats before submission

- **R0 not closed:** the official NVIDIA rule wording is not yet quoted, and Narin has not signed off on `07` v4.3.
- **Sponsor readiness:** `scripts/smoke_live.py` passed on 2026-10-26 (R11a below) at diagnostic scope. Pack `readiness` still reads `not_verified`: billing and in-run evidence readback are separate dimensions, and this is not end-to-end sponsor proof. Re-run it on the final setup before submission.
- **Local-only data:** the registered bundles, bindings, catalog copies and R5 artifacts are gitignored. A clean clone must re-collect and re-register sources (`collect_sources.py`, `prepare_source_bundle.py --include-discovered`, `register_sources.py`); this has not been rehearsed on a second machine.
- **Free key:** the NVIDIA key is a free Developer Program key (prototyping only); its rate limits are unknown, and only the Planner and Critic routes have verified profiles.
- **Quality:** one sample per pair and pending human-review checks mean no candidate qualifies yet and no quality claim is made.
- **Settings passed on the command line for R5:** thinking off for the Planner and Critic and for Lightning, a 150 s timeout, and a running evidence publisher.

## Final handoff checklist

- [x] F01 Typed Zetaris reads and evidence round trip (local; second-machine run pending)
- [x] F02 Real H-MEM works and passes restart and isolation tests (local reference)
- [x] F03 Candidate and role identities match their records; Nemotron proof attributable (R1, R5)
- [x] F04 Dated, cited source snapshots and repeatable registration
- [ ] F05 Shared-core founder UI in both modes
- [ ] F06 Validated representative tasks and rubrics from the planning workflow
- [ ] F07 Confirmed and accepted memory changes a later run
- [x] F08 Composed levers give valid totals; unknown prices preserved
- [ ] F09 Repaired tokens and quality jointly drive the recommendation
- [x] F10 Dispatch, spend limits and unknown-outcome recovery
- [x] F11 Input validation and founder controls (budget fit across stages needs R9)
- [ ] F12 Stage totals, revenue, AI contribution and margin
- [ ] F13 Critic grounding and honest lab independence
- [ ] F14 Human reviews bound to immutable outputs
- [x] F15 Traces keep usage; required SKIPs cannot report readiness (Windows unverified)
- [ ] F16 Documentation, clean-clone rehearsal, founder observations, release artifacts
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
| Revised PowerShell preflight | Windows required; unavailable here | Execute on Windows with configured Python and fixture/live endpoints | Not run on this macOS host | UNVERIFIED |

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

Catalog prices are market references, not execution tariffs; only the two role routes carry verified execution profiles (free key, 0/0). **Unverified:** source usage-rights review, real AWS/IAM, Windows. The route map no longer pins a candidate: the dead `openrouter/nvidia/nemotron-3-super-120b-a12b:free` pin (upstream 404) was removed, and Gemma was replaced earlier the same day.

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
- **What the profile claims:** a verified input and output rate of $0 per 1M tokens, a prototype-only label, a 100,000-byte prompt bound, a 2,048-token overhead (raised from 64 after the Lightning overrun) and a 1,024-token output cap. These bounds come from the probes and the R5 overrun, not from an NVIDIA document.
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
