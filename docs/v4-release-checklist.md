# v4 incremental implementation evidence

This ledger records executed checks separately from planned work. No owners are assigned. A milestone PASS applies only to its stated scope; M00 does not establish sponsor readiness or close the 16 gap findings.

## M00 — Baseline and recovery inventory

**Status: PASS — offline baseline and history inventory only.** Checked October 25, 2026. Base revision `9936c6683b205a1a69b57ce063c11c32a0bb0c64`; branch `feature/realign-07-meena`; macOS, Python **3.12.12** in `.venv`.

At the start, `.gitignore` was already modified and the gap review/implementation guide were untracked. These were preserved. M00 adds the sample checker, its regression test, this ledger/inventory, and v4 contributor/README instructions. Core application behavior and historical integration implementations were not changed. Evidence therefore refers to this base revision **plus the working tree**, with source SHA-256 hashes in the checker manifest.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `.venv/bin/python -m pytest -q -rs` before changes | Offline Python tests | Existing suite passes; known skips recorded | 100 passed, 9 skipped | PASS, baseline only |
| `.venv/bin/python -m pytest -q tests/test_check_sample_examples.py tests/test_controller_sample.py tests/test_sample_data.py` | Isolated CLI regression; no sponsor credentials | Three-example checker plus sample regressions pass; source inputs preserved | 19 passed | PASS |
| `.venv/bin/python -m pytest -q -rs` after adding the checker/test | Offline Python tests | Existing suite and new checker test pass; known skips remain explicit | 101 passed, 9 skipped | PASS, offline scope |
| `.venv/bin/python scripts/check_sample_examples.py` | Copied requests; fresh databases/logs; dotenv disabled; Python sockets blocked | All three examples complete in sample mode with estimated costs and no fabricated execution/quality | Three PASS results; 4 / 3 / 2 feature tables; 12 / 9 / 6 unexecuted feature/candidate records | PASS |
| History inspection of `1f27731` | Local Git, read-only | Identify reusable mappings, registration, engine and diagnostics with adaptation boundaries | Recorded in [integration inventory](m00-integration-inventory.md) | PASS |
| Contributor/setup instruction review | Documentation | `07` is authoritative; retrospective shelved; repeatable check documented | Updated [CLAUDE.md](../../CLAUDE.md) and [README](../../README.md) | PASS |

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
| Committed calculator fixture artifact | Synthetic inputs only | Exact batch/cap $1.1055; unknown tariff stays unknown; standalone discount and paid-volume recalculation correct | Four asserted cases PASS in [JSON artifact](m02-calculator-regressions.json) | PASS |
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

Temporary artifacts are current-machine evidence and should be regenerated on a clean clone. [m02-calculator-regressions.json](m02-calculator-regressions.json) retains portable synthetic inputs, computed rows, expected/actual exact totals and exact lever deltas. Its measured/verification fields are test simulations, explicitly labeled as such; they are not real API usage or sponsor proof. The known nine skips and M03–M14 gaps remain open.

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
| Portable HTTP fixture traces | Synthetic model/usage/SQL payloads | Usage remains numeric; timeout and wrong SQL cell retain correlated error events | Three scenarios asserted in [JSON artifact](m03-diagnostic-regressions.json) | PASS |
| Revised PowerShell preflight | Windows required; unavailable here | Execute on Windows with configured Python and fixture/live endpoints | Not run on this macOS host | UNVERIFIED |

Final sample-check manifest:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-k6rouuc3/manifest.json
```

Unconfigured diagnostic and example regeneration artifacts:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-m03-evidence-2_24yps5/regeneration-manifest.json
```

[m03-diagnostic-regressions.json](m03-diagnostic-regressions.json) retains portable synthetic traces, required-skip/readiness results, sample readiness assertions and working-tree source hashes. Fixtures are not installed-runtime or provider evidence. The nine skips still include eight shelved retrospective tests and one missing real H-MEM test. M04 dispatch/spend/restart enforcement, M06–M08 real integration proof and M13 UI consumption remain open. Execute the Windows preflight during the integration-host/clean-clone rehearsal; this scoped PASS does not claim Windows validation or end-to-end F15 release proof.

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
| Six portable dispatch scenarios | Synthetic inference and cited-fixture policies | Zero-budget refusal, single ambiguous attempt, safe retry, all-role reconciliation, overrun and unknown restart refusal | Six asserted cases in [JSON artifact](m04-dispatch-regressions.json) | PASS |
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

[m04-dispatch-regressions.json](m04-dispatch-regressions.json) preserves synthetic billing inputs, durable receipts, expected/asserted results, sampling summaries, executed commands and working-tree source hashes. Verification flags and model/API fields in that artifact are explicitly simulated; they are not real tariff or sponsor proof. Prior scoped results remain historical. M05–M08 must collect actual route, tariff, framing/token and reasoning-limit evidence before live dispatch. Unknown-charge reconciliation remains an external evidence task; automatic replay is deliberately unsupported. The nine skips and Windows/real-engine/provider validation remain open.

## M05–M06 — Implemented source pipeline and local component proof

**Status: PARTIAL overall; local source-component checks PASS.** The collector, pinned bundles, publisher/registration, typed reads, separate ingestion/readback and durable outbox are implemented. Use the [manual test guide](../12-M05-M06-Manual-Testing.md) and [portable verification](../m05-m06-source-checks.json), stored outside this ignored evidence directory. No owners are assigned.

Executed local evidence:

- Actual public OpenRouter collection: 467 raw records, 460 accepted catalog rows, 7 explicitly quarantined invalid/unbounded-price rows. Raw files, normalization, rejection reasons, manifest and hashes were retained and published. No inference was used.
- Snapshot `a6cff78717992be3b332c65d`; final bundle/bindings `0f05b990b97c5a03338355de`, schema 1.1. Registered under dedicated namespace `cost_optimizer_v4`, bucket `cost-optimizer-data`, prefix `cost-optimizer/v4`. LocalStack S3 emulation only; no existing source was dropped or patched.
- Registration and exact row checks: 460 catalog rows, 3 planned model profiles and 1 synthetic founder brief. A second application reused every identical object/table and the same release. No current pointer was changed.
- Actual Zetaris component checks: SELECT 1 cell validated, typed model/brief reads, original provenance retained, a queried catalog price fed a labeled token-reference calculation, and integration-test evidence passed write/readback, a second append, recreated-publisher state and duplicate-write checks. Fixture evidence remains `unverified`; it is not measured model evidence.
- Actual temporary loopback ingestion/outbox test: unavailable endpoint left the fixture pending (exit 1), restored ingestion published it (exit 0), and a subsequent retry was a no-op (exit 0). A floating latency value survived byte-consistent readback. Zero model completions; only a new test DB was used.
- Free Nightshift discovery retained 75 advertised routes. The example frontier/mid routes are not offered; their mapping stays planned. Lightning was advertised. No execution/variant or billing equivalence is inferred from discovery.

Final local artifact paths:

```text
data/localstack/openrouter/catalog/a6cff78717992be3b332c65d/
data/localstack/openrouter/bundles/0f05b990b97c5a03338355de/
data/localstack/openrouter/bindings-final.json
data/localstack/openrouter/registration-final.json
data/localstack/openrouter/registration-final-repeat.json
data/localstack/openrouter/final-check-2/report.json
data/localstack/openrouter/source-http-recovery-93d1e10c/report.json
```

### Real AWS S3 on a Windows host (October 26, 2026)

Windows 11 + WSL2, Docker Desktop 4.91.0 (8 CPUs, 15.6 GiB), Python 3.13.14, local Zetaris (`verify.sh` 9/9). Full record: [aws-registration-check.json](aws-registration-check.json). Zero model completions.

| Command/check | Environment | Expected | Actual | Status |
|---|---|---|---|---|
| `scripts\preflight_windows.ps1` with Zetaris and Nightshift | PowerShell 7, venv Python | Machine/connectivity checks pass | PREFLIGHT CHECKS PASS, 0 FAIL/WARN/SKIP/UNKNOWN | PASS |
| `register_sources.py --storage data\source_examples\aws.oah.json --apply` | Bucket `cost-optimizer-oah-k7m2q`; read-only key in the publishing terminal | Publish, register, exact row checks | 9 objects published with S3 versions; 3 tables created (1 brief, 460 catalog, 3 models); no current pointer change | PASS |
| Same command repeated | Same | Everything reused | 9/9 objects and 3/3 tables reused | PASS |
| `check_zetaris_sources.py` typed reads | Zetaris API key only | SELECT 1, typed reads, catalog arithmetic | 4/4 pass; `nvidia/nemotron-3.5-lightning` 0.07 / 0.20 per 1M, `execution_tariff: false` | PASS |
| Same with `--round-trip --storage aws.oah.json` | Read-only key in terminal | Write/readback, append, restart, duplicate | 5/5 pass; 1 S3 evidence object, 2 fixture rows in Zetaris; first attempt without the key failed before any write | PASS |
| Per-bucket `fs.s3a` credentials in Zetaris `spark-defaults.conf` | Driver restarted | Table creation without a key | Ignored; driver fell through to the EC2 metadata endpoint. Reverted | FAIL, by design not used |

The Zetaris reader is a dedicated IAM user with an inline policy only: `GetBucketLocation`, `ListBucket` on prefix `cost-optimizer/v4/` and `GetObject` on `cost-optimizer/v4/*`; the IAM policy simulator denied everything else checked. Zetaris reads S3 file stores only with a key in the table `OPTIONS`, so the publisher adds it from `ZETARIS_S3_*` in its own process; Zetaris's metadata API returns that secret masked. The bundle used the catalog-only route map; the team's route selection and execution tariffs are still pending.

**Remaining acceptance:** active frontier/mid routes, applicable provider/variant tariffs and complete cache/batch/context/index source coverage, source usage-rights review and runtime token/reasoning billing bounds. M06 has demonstrated reference-price arithmetic, not a verified execution-tariff calculation. Actual measured-model evidence is repeated at M08. Real AWS S3 registration, evidence round trip and Windows execution now pass for the scope above; server-side sealed-source permissions remain unverified. These outstanding proofs prevent marking all of M05/M06 complete.

Final checks on base `3132207` plus the working tree (Python 3.12.12): 72 focused source/adapter/ingestion tests passed; full suite 449 passed, 9 known skips; three guarded sample examples passed and were regenerated. The exact commands, source hashes and actual local reports are in [the portable source record](../m05-m06-source-checks.json). Sample manifest: `/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-ctr_0bk2/manifest.json`. Retained test/example artifacts: `/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-m05-m06-final-idb5tw9c/regeneration-manifest.json`.

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

The `tsx` CLI conformance run required sandbox escalation for its local IPC pipe; it passed after escalation. `npm ci` completed using the pinned lockfile and reported security advisories in development dependencies. No provider call was made. This is local reference evidence, not proof that accepted memory changes a later decision (M11), that JSON-file storage is safe for concurrent production use, or that the live sponsor workflow is ready. Manual instructions: [M07 verification](14-M07-Manual-Testing.md).

## M08 — Nightshift response gate and read-only live preflight

**Status: PARTIAL.** Checked October 25, 2026. `parse_completion_response` now requires a single text choice, a nonblank resolved model and response request ID, valid non-negative prompt/completion counts, and reasoning no greater than completion. It preserves raw usage, Nightshift winning-route model/provider/kind and receipt ID in the adapter, feature sample and durable dispatch record. The durable dispatcher still refuses a mismatched alias without a correlated priced identity and refuses all paid calls without verified route tariffs and bounds.

The earlier `feature/plan-07-impl-meena` commit `1f27731` records two **actual** standalone Nightshift/NVIDIA cloud completions on October 25: Lightning receipt `rcpt_req_6vjuc0nt` (208 input/18 output tokens) and Ultra receipt `rcpt_req_51o80g0a` (206 input/16 output tokens). Both were attributed to exact requested winning models. It also records Super as previously failing before the configured candidate was changed. Those are documented prior probes, not this M08 pack; the branch contains receipt IDs and observations, not saved raw receipt JSON.

The prior registered-binding no-spend diagnostic at `/private/tmp/cost-optimizer-m08-branch-verification/` reported Zetaris `SELECT 1` PASS, four pinned model rows PASS, Nightshift `GET /v1/models` PASS with 75 routes, H-MEM PASS, and three required completion SKIPs. The selected map now uses Ultra (frontier), Lightning (mid-tier) and Gemma 4 31B Dense free (required open model). Fresh discovery advertised 112 routes, including `openrouter/google/gemma-4-31b-it:free`. New immutable bundle `d85a2e103d87ba5069bf26e3` was registered with three rows at `data/localstack/openrouter/bindings-lightning-mid-gemma-open.json`; its typed Zetaris read and zero-completion OpenRouter projection passed (24 separate market-reference rows). The read-only gate at `/private/tmp/m08-lightning-mid-gemma-open-gate-retry.json` found all three advertised/registered and matched the current selection. Each still has `model_source_status: unknown`, no dispatch policy and a blocked billing gate. The configured Ultra Critic shares the frontier candidate, and the controller discloses that shared identity. The synthetic two-feature, one-sample-per-pair $0.50 request was prepared at `/private/tmp/cost-optimizer-m08-tiny-001.json` but **not executed** in this M08 check. No new paid request or model-output claim was made.

The branch reconciliation focused tests passed (134 adapter/trace/dispatch/controller cases); the full offline suite passed **476 tests with 8 shelved retrospective skips** after the Gemma route change. The current zero-spend smoke at `/private/tmp/m08-smoke-gemma-no-spend-retry/` passed Zetaris, Nightshift discovery and H-MEM, with three expected completion skips. The remaining acceptance is a verified serving/billing source and request bound for each role, a current Gemma response, three attributable candidate responses, a Nemotron-backed working feature, and a bounded CLI pack with Zetaris evidence readback. A distinct Critic route is optional when its serving/lab identity is proven; shared Ultra is disclosed. See [M08 manual verification](15-M08-Manual-Testing.md). Do not infer a Nightshift bill from the separate OpenRouter scenario.

The Ultra + Lightning validation subset passed the zero-spend controller preview (16 OpenRouter reference rows). A live-mode CLI run using only those two tiers returned a `partial` pack at `/private/tmp/m08-ultra-lightning-two-model-pack.json`: four unexecuted feature/model pairs, 0 dispatches, $0 spend and an explicit pending open-model comparison. Its request and gate report are `/private/tmp/m08-ultra-lightning-two-model.json` and `/private/tmp/m08-ultra-lightning-two-model-gate.json`. The gate requires Ultra and Lightning for this scoped run and reports Gemma as optional; both required billing gates remain blocked. See the [two-model manual guide](16-M08-Two-Model-Validation.md).

The repeatable $0 request also produced a `partial` pack at `/private/tmp/m08-ultra-lightning-two-model-zero-pack.json` with four planned pairs, 16 reference projection rows, 0 dispatches and $0 spend. The full offline suite after the two-model changes passed **483 tests with 8 shelved retrospective skips**.

## Milestone status

| Milestone | Status | Evidence or next acceptance action |
|---|---|---|
| M00 | PASS, scoped as above | Baseline checks, retained sample manifest, reusable-code inventory |
| M01 | PASS, scoped as above | 84 contract cases; 185 passing suite tests; sample examples regenerated |
| M02 | PASS, scoped as above | 75 focused economics checks; 217 passing suite tests; calculator/sample artifacts |
| M03 | PASS, scoped as above | 89 focused checks; 303 passing suite tests; required-skip and portable HTTP evidence; Windows preflight executed on Oct 26 (PASS, see M05–M06) |
| M04 | PASS, scoped as above | 67 dispatch tests; 183 focused / 377 full passing tests; synthetic receipts and restart/concurrency evidence |
| M05 | PARTIAL; component PASS | Actual catalog retained/published/registered on LocalStack and real AWS S3; execution tariff/route, source coverage and usage review pending |
| M06 | PARTIAL; component PASS | Typed reads, reference calculation, real fixture round trip (LocalStack and AWS) and HTTP outbox recovery pass; execution-tariff/measured-model proof pending |
| M07 | PASS, local reference scope | Real engine restart/isolation/audit and offline delegation pass without skipping; M11 decision influence remains pending |
| M08 | PARTIAL; prior Ultra/Lightning live receipts, current read-only gate and fixtures pass | Applicable tariffs, third candidate proof and bounded live pack pending; shared Critic disclosed |
| M09 | pending | Validated planner tasks/rubrics and grounded flags-only critique |
| M10 | pending | Output-bound review and effective repair evidence |
| M11 | pending | Accepted context affects a later run with a sourced comparison |
| M12 | pending | Aggregate totals, revenue, margin and founder controls |
| M13 | pending | Shared-core sample/live UI with no duplicate generation |
| M14 | pending | Final suite, real sponsor proof, second-machine rehearsal and release artifacts |

For subsequent checks, append the exact command, environment, expected/actual result, revision and artifact path. Keep failed assertions and negative outcomes. Do not convert planned tests or required integration skips into PASS results.
