# Setup and implementation execution plan

**Updated:** 25 October 2026 UTC, based on repository commit `3e90d15` plus the current local setup work. This is the execution checklist for the project. It complements the [PRD](01-Product-Requirements.md), [architecture](02-Technical-Architecture.md), [implementation plan](03-Implementation-Plan.md), and [case-study design](06-Retrospective-Case-Study-Design.md). Setup instructions below refer to the *Open Agent Hackathon 2026 Participant Setup Guide*, last updated 21 October 2026; page numbers refer to the PDF pages.

**Current baseline:** Stages 1–4 pass their recorded setup/engine checks. Stage 5 application code is implemented: bounded Zetaris mappings and guarded reads, real H-MEM, deterministic ranking labeled `rule_policy`, structured Nightshift candidate/critic requests, one validated repair, usage-based spend accounting, evidence ingestion/readback, and freeze-before-holdout. The local integration verifier passes all nine checks with fixtures and zero inference calls. A fully evaluated live decision is still pending approved case-study data, cited configured-model rates, sealed-source permissions and an observed paid candidate/critic run. See Stage 5 below for proof and remaining blockers.

**Current topology:** The verified integration host is the local Apple Silicon Mac. Zetaris and LocalStack run in Docker; Python runs in the project's `.venv`; Nightshift Runtime runs on the host at `http://127.0.0.1:8088/v1`; H-MEM runs as a fresh local Node process per operation with persistent project-scoped storage. LocalStack S3 emulation is the verified fixture-storage route. Real actuals stay private and separate, and all live inference must use Nightshift. The existing plan proposes Narin for setup/integration, Pradeep for H-MEM and adapters, Isioma for data, Meena for evaluation, and Shrie for UI/reporting; these assignments remain proposals unless confirmed by the team.

| Stage | Observed status | Next exit check |
|---|---|---|
| 1 — Zetaris | Complete | Preserve repeatable 9/9 and app-credential SQL results |
| 2A — Data storage | Complete with setup fixtures | Preserve counts, manifests, and no-holdout-query evidence |
| 2B — Case-study data | Pending | Founder/rubric approval, verified rates, private actuals, and access controls |
| 3 — Nightshift/Nemotron | Complete: configured routes and standalone checks pass | Preserve model identities, Runtime receipts, and repeatable checks |
| 4 — H-MEM | Complete | Preserve restart/isolation, audit, supersession, and ranking checks |
| 5 — Live agent | Code implemented; nine local integration checks pass; full live-evaluation exit pending | Approve/register data and exact model rates, verify sealed permissions, then record a bounded paid investigation |
| 6 — Judge rehearsal | Pending | Fresh-checkout offline/live runs and submission evidence pass |

## Ground rules for every stage

- Keep credentials in private local configuration. Never put the Zetaris admin password, Zetaris API key, Nightshift Runtime token, NVIDIA key, or S3 credentials in Git, logs, screenshots, or this plan. The NVIDIA key belongs in Nightshift's Providers tab; S3 credentials belong in Zetaris-side configuration. Do not print or inspect `.env` during review.
- Preserve `retrospective_actuals` outside the public repository. The repository's similarly named sample file is **synthetic**. Never use actual outcomes to choose or repair a configuration before freeze, and never report a dollar amount as “saved.”
- Treat sample mode as a credential-free demonstration of the control flow. Sponsor acceptance needs separate **live** evidence. A service health check alone does not prove a useful project query or model response.
- Use the installed Zetaris API reference and the live Meterless Power Prompt as the final request contracts. The PDF contains examples; record actual versions, routes, model IDs, response shapes, and any deviations.
- At the end of each stage, record **pass/fail, date, owner, and redacted artifact path** in a private team evidence log. Check boxes below only when the exit check is observed.

## Stage 0 — Select and prepare the integration machine

**Dependency:** none. **Guide:** pp. 4, 7–8, 17. **Exit:** a named host can run all three services and the app.

- [ ] Select the host. The existing architecture chooses Windows with Docker Desktop/WSL2; the guide also describes macOS and Linux. If the host changes, update the README's commands and network addresses.
- [ ] Confirm at least 16 GB host RAM in practice, 8 GB and 4 CPUs available to Docker, and at least 15 GB free disk. Confirm Docker Engine/Compose, Git, Python, Node, and npm. On Windows, enable WSL2 and Docker's WSL integration.
- [ ] On the Windows candidate, run `scripts/preflight_windows.ps1` before installing sponsor services. Save its report without credentials. Then run the platform bundle's own `./preflight.sh` from its extracted directory (in WSL on Windows).
- [ ] Establish one private project `.env` from `.env.example` and verify `.gitignore` excludes it. Keep the Zetaris platform bundle's separate `.env` separate from the app's `.env`.

**Stop here if:** Docker lacks the resources the guide requires or the chosen host cannot run the local services. Use a different host or the sponsor-supported managed option before debugging app code.

## Stage 1 — Install and prove Zetaris by itself

**Dependency:** Stage 0. **Guide:** pp. 6–11, 23–24. **Exit:** UI, query engine, and authenticated REST SQL all work.

**Stage 1 complete, 25 October 2026 at 00:28 UTC:** The user confirmed completing the private API-key setup. The configured app connection returned `1` from `SELECT 1 AS one`, and the installed bundle passed **9/9 checks** again. See [the verification report](../docs/07-Zetaris-Setup-Verification.md), [app connection result](../docs/zetaris_connection_check.json), [bundle output](../docs/zetaris_platform_verify.txt), and [observed SQL response](../docs/zetaris_select1_response.json). This proves the local Zetaris connection; Stage 2 will register and verify the project's sources.

- [x] The user obtained and installed the platform bundle and configured the administrator account. Working administrator sign-in is verified. Initial download and first-start steps were completed by the user and were not replayed during verification.
- [x] The installed Docker Compose stack has healthy `postgres`, `driver`, `api`, and `ui` services; `init` and `bootstrap` exited successfully. Installation commands and resource checks remain documented in Stages 0–1 for a fresh machine.
- [x] Run the bundle's `./verify.sh` and obtain **9/9 passes**, including its UI → API → driver → Spark SQL check. Separately confirm `SELECT 1 AS one` through the authenticated UI query route and the direct REST endpoint. The guide's PokéAPI starter query remains an additional source-registration exercise.
- [x] The user confirmed creating and privately configuring a Zetaris API key. The app's own adapter called `POST /sql-editor/sqls/run` using that configured bearer credential, `X-Org-ID`, and a fresh UUID `X-Request-ID`. `SELECT 1 AS one` returned one row containing `1`; the sanitized report and query trace were saved. The verified request includes `queryId`, `sql`, `source`, and `limit`.
- [x] Align `app/adapters/live.py` and `scripts/preflight_windows.ps1` with the verified request, including `source: SqlEditor`; verify the returned SQL value in the Windows preflight and the standalone `scripts/check_zetaris.py`. Automated contract and error tests pass; Windows execution remains a host-specific check.

To repeat the app's own connection check independently of Nightshift and H-MEM, run `python scripts/check_zetaris.py --output docs/zetaris_connection_check.json`. In the installed UI, API-key creation is under **Management → API Tokens → New token**.

The earlier session-authenticated check is retained as [separate evidence](../docs/zetaris_session_connection_check.json); the later configured app-credential check passed independently. The observed organization ID for this installation is `1`. The platform password setting was synchronized under explicit user authorization, and the user completed the project's private API-key setup. The verified host is the current local macOS installation; Windows preflight execution will need a Windows host if the team changes machines.

**Stop here if:** only the UI works, only `/health` responds, or the REST request has not returned a row. No project data mapping should be guessed from a sample response.

## Stage 2 — Register project data and approve the live case study

**Dependency:** Stage 1. **Guide:** pp. 6, 10, 22. **Exit:** Zetaris returns approved project records with stable IDs, versions, and suitable access restrictions. Stage 3 can proceed while the human data approvals below are completed.

**Storage update, 25 October UTC:** The six requested LocalStack steps are complete: activated service, shared Zetaris network, bucket creation/uploads, source registration, successful probe query, and ordinary project-fixture row checks. See [the runbook](../docs/08-LocalStack-Zetaris-Setup.md) and [successful query report](../docs/localstack_registration_check.json). JSON arrays were required to preserve all rows in the installed reader. The holdout table is registered separately and its contents were not queried. This completes the storage transport work with fixtures; the live case-study approval and pricing tasks below remain open.

### Completed storage work (Stage 2A)

- [x] Start activated LocalStack with a persistent volume on the existing `zetaris_default` network; verify healthy status and S3 operations.
- [x] Prepare a CSV probe, JSON-array founder/pricing/task exports, and a versioned SHA-256 manifest; preserve fixture and evidence-status labels.
- [x] Upload the seven current objects and register five ordinary tables under `oah_localstack` plus the separate `oah_localstack_sealed.dev_task_cases_holdout` table.
- [x] Query ordinary records through the app's Zetaris transport: probe 1, founder briefs 3, approaches 4, models 2, development tasks 3. Record SQL query IDs and the trace in the [successful report](../docs/localstack_registration_check.json).
- [x] Verify repeated registration and successful queries after LocalStack container recreation. Do not query holdout content for setup checks.
- [x] Record the current six-task fixture design in this execution plan: 3 development and 3 holdout tasks. Founder approval remains pending.

### Mandatory pending tasks and blockers (Stage 2B)

| ID | Mandatory task | Blocks |
|---|---|---|
| S2-01 | Approve the founder brief from pre-build evidence or labeled recollections; verify it contains no actual outcomes | Live founder recommendation |
| S2-02 | Approve the six tasks (3 development, 3 holdout), pass criteria, and critical failures; freeze rubrics before benchmarking | Valid benchmark results |
| S2-03 | Supply dated, cited prices for the four approaches and actual Stage 3 model routes; keep unavailable rates explicitly unknown | Supported cost estimates and rankings |
| S2-04 | Upload/register approved data and verify Zetaris returns its record IDs and versions | Live data integration; current records are setup fixtures |
| S2-05 | Enforce sealed-source access restrictions and deny holdout/actuals reads before freeze; verify controller guards with Stage 5 | Safe benchmark execution and sealed-data use |
| S2-06 | Prepare private, consented founder actuals and the restricted retrieval path | Real retrospective comparison only; not Stage 3 setup |

**Stage 3 can start now:** none of these tasks blocks Nightshift installation or its standalone inference check. Evaluation-evidence writeback/readback remains part of Stage 5. Updating older planning documents is not required.

**Stop here if:** the app is reading the bundled JSON files in a supposedly live run, or a recommendation cannot cite a Zetaris project record.

## Stage 3 — Install and prove Nightshift and Nemotron by themselves

**Dependency:** Stage 0; can run while Stage 1–2 proceeds. **Guide:** pp. 16–20, 23–24. **Exit:** a real Nemotron-backed response is attributable.

**Stage 3 complete, verification started 25 October 2026 at 03:23:14 UTC:** The saved primary/candidate settings now use Lightning and Ultra; the critic uses Ultra. `GET /healthz` returned 200, model discovery through `NightshiftInference.list_models()` returned 75 IDs including every configured route, and a deliberately invalid token returned 401. Both distinct configured models returned fresh, noncached JSON through `NightshiftInference.complete()`. Runtime receipts identify provider `nvidia`, kind `cloud`, and the exact requested model as the winning model. The earlier missing-provider and failing-Super blockers are resolved. The current [Meterless provider contract](https://meterless.ai/engines.html) is the implementation reference.

| Verification | Observed result | Evidence |
|---|---|---|
| Runtime health, app authentication and model discovery | Pass: HTTP 200; all configured IDs discovered | Authenticated app adapter; 75 IDs returned |
| Configured primary / second candidate: `nvidia/nemotron-3.5-lightning-30b-a3b` | Pass through app completion adapter: HTTP 200, expected JSON, uncached | Receipt `rcpt_req_6vjuc0nt`; request `chatcmpl-8549db0a-9f32-4cf1-aa45-71f19adf9825`; 208 input / 18 output tokens |
| Configured critic / first candidate: `nvidia/nemotron-3-ultra-550b-a55b` | Pass through app completion adapter: HTTP 200, expected JSON, uncached | Receipt `rcpt_req_51o80g0a`; request `chatcmpl-c57055b0-81db-4a9d-8f76-7de7a8abdf79`; 206 input / 16 output tokens |
| Invalid Runtime token | Pass: HTTP 401 | Deliberately invalid token rejected |
| Explicit unavailable NVIDIA model | Pass: HTTP 404, `model_not_found` | No substitute model was returned for the provider-prefixed ID |
| Adapter timeout propagation | Pass with a simulated `httpx.ReadTimeout` | No live provider timeout was induced |

Successful inference probes used unique prompts, a 256-output-token cap, and disabled thinking. The adapter probes applied those controls only to outgoing test requests; no application code or private configuration was changed during verification. These checks prove standalone connectivity and attribution, not the end-to-end critic feature or benchmark quality. Unknown bare model aliases can fall through to Runtime routing; validate app model IDs against discovery before dispatch in Stage 5.

**Verified current settings:** the user replaced the failing Super route. All settings below were loaded from existing private configuration and verified; the working Runtime URL/token remain private. There are no remaining standalone Stage 3 blockers.

```dotenv
METERLESS_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
METERLESS_CANDIDATE_MODELS=nvidia/nemotron-3-ultra-550b-a55b,nvidia/nemotron-3.5-lightning-30b-a3b
METERLESS_CRITIC_MODEL=nvidia/nemotron-3-ultra-550b-a55b
```

- [x] Run Nightshift Runtime locally; the process is listening on port 8088 and `/healthz` returns 200.
- [x] Prove Nightshift's NVIDIA provider can serve real Nemotron requests. Runtime receipts identify NVIDIA cloud and the exact Ultra/Lightning models. No provider credentials were inspected or changed.
- [x] Verify the privately configured Runtime URL/token through the app's authenticated `GET /v1/models`, with `meterless-app: llm-cost-intelligence` and `meterless-scope: user`. Route discovery passes; an invalid token returns 401. No credentials were printed or changed.
- [x] Verify the saved primary/candidate/critic settings. The failing Super route has been replaced; both candidates pass through the completion adapter and resolve to distinct Lightning/Ultra IDs. The critic's Ultra route is included in that successful check.
- [x] Obtain a real Nemotron response from the app host and through the completion adapter; correlate winning model/provider with Runtime receipts. The configured Ultra critic route passes this standalone check; implementing its useful application feature remains Stage 5.
- [x] Verify connection, invalid authentication, discovery, JSON/text response, and explicit unavailable-model rejection. The adapter propagates a simulated timeout; handling a real provider outage throughout the controller remains a Stage 5–6 check.

**Routing note:** these tests explicitly addressed `nvidia/<model>` IDs. The installed Nightshift Runtime supports model pinning independently of manual lane assignment, subject to app policies. A `meterless/auto` request instead uses Runtime routing; its actual winning model must still be checked.

**Following stage:** Stage 4's H-MEM proof is now complete below. The meaningful critic feature and complete founder investigation remain Stage 5 work.

## Stage 4 — Finish the H-MEM Engine feature

**Dependency:** Stage 0; can run alongside Stages 1–3. **Guide:** pp. 14–15. **Exit:** a confirmed constraint survives restart and changes or preserves a decision for an explained reason.

**Stage 4 complete, 25 October 2026 UTC:** Vendored the unchanged official Meterless H-MEM reference and conformance suite at revision `1742dec56a66e58eef9dda2d2b865823758ca8cd`, with license, source hashes, and locked Node dependencies. See the [engine setup and contract](../app/engines/hmem/README.md) and [standalone verification report](../docs/hmem_engine_check.json). No model credentials or inference are needed for this engine.

- [x] Pin the real sponsor reference, implement `bridge.mjs`, install from the lockfile, and pass the offline self-test. Source hashes are checked before loading the reference. A clean `npm ci --offline --ignore-scripts` succeeded using the already populated package cache.
- [x] Implement real `remember_confirmed`, `recall`, and `audit` operations through persistent reference services. Each call launches a new Node process; scope-specific IDs/stores, source provenance, audit references, and independent-writer locking pass integration checks. The H-MEM test now passes without skipping.
- [x] Apply recalled structured confirmed constraints before eligibility/ranking. Integration tests prove a remembered DevOps constraint preserves the next plan, current confirmed input changes eligibility, and the superseded old value does not return on another restart. Reconstructed/assumed inputs are not promoted to confirmations; generated recommendations are not automatically treated as founder-accepted findings.
- [x] Connect sample mode to the same real offline reference with storage separate from live mode. Missing/failed memory produces a clear partial result before evaluation. Memory traces include real engine revision, scoped IDs and audit references.

| Check | Observed result |
|---|---|
| Offline Node self-test | Passed: save, fresh-process recall, isolation and audit |
| Standalone Python verifier | All 6 checks passed; synthetic temporary scopes, zero inference calls |
| Official reference tests | 10 passed |
| Official conformance suite | 13/13 passed |
| Python application suite | 46 passed, no skips |

Repeat the standalone proof from the project root:

```bash
.venv/bin/python scripts/check_hmem.py --output docs/hmem_engine_check.json
.venv/bin/python -m pytest -q tests/test_hmem_engine.py tests/test_memory_constraints.py
```

**Scope:** the app uses confirmed capture, reference enrichment, retrieval/reinjection, supersession and audit. The reference's embedder is deterministic hashing and persistence is JSON/JSONL; this is not a production semantic-memory service. Dreaming, sleep and model-based mining are not invoked by this product. Completing Stage 4 does not complete the live data mappings, model critique or founder evaluation in Stage 5. Stage 2B approvals/data blockers still apply.

## Stage 5 — Complete the live application path

**Dependency:** Stages 1–4 and project data. **Exit:** one end-to-end run uses the intended technologies for its actual decision.

**Implementation update, 25 October 2026 UTC:** The code below is implemented and covered by automated tests. This does **not** close Stage 5's live-evaluation exit. Local service verification at **16:39:49 UTC** passed nine checks without inference or sealed-content reads; [the report](../docs/stage5_integration_check.json) contains the actual source IDs and exact evidence writeback references. Setup, data contracts and limitations are in the [live application integration guide](../docs/09-Live-Application-Integration.md).

**Automated verification:** all **81 Python tests pass, with no skips**, including real H-MEM and deterministic live-adapter HTTP/S3 tests. These tests make no model calls. The earlier Stage 4 count of 46 records that stage's historical run.

- [x] Implement the six Zetaris methods against the observed JSON-envelope schema with validated IDs/splits, fixed bounded queries, versions/statuses and source references. Ordinary reads and synthetic evidence ingestion/append/readback pass against the real local services. Private actuals retrieval is implemented and tested with doubles; a consented live source remains pending.
- [x] Route investigation reads through the controller guard before adapter dispatch. Live briefs come from Zetaris rather than inline descriptions. Tests deny holdout/actuals dispatch in every pre-freeze state; the local verifier also observes denied calls without reaching the sealed adapters.
- [x] Keep ranking deterministic and explicitly label it `rule_policy` in live and sample modes. Validate critic actions, references, targets and founder-constraint protection. Deliberate missing-context injection is restricted to the labeled sample fixture.
- [x] Implement structured, source-linked Nightshift/Nemotron critique with one validated target revision, optionally one bounded pricing re-query. HTTP/S3 integration tests cover all-pass/no-repair, an observed missing element, re-query, invalid JSON, invented references and rejected sealed requests. **The complete real paid critique has not yet been run.**
- [x] Reserve conservative per-call input/output bounds and settle real response usage against dated/cited exact-model rates. Unknown rates block paid dispatch; ambiguous delivered calls keep an outstanding reservation and `spend_usd: null`. Retry only pre-delivery connection failures, at most twice globally. Preserve generation limits, duplicate-run refusal and separate founder ledgers.
- [x] Persist frozen configuration snapshots/digest before querying holdout; evaluate both configurations on the same tasks and never repair after freeze. HTTP/S3 tests prove holdout failure causes abstention. Live holdout content remains unqueried during setup checks.
- [x] Add separate post-freeze `--zetaris` retrospective retrieval and retain controlled private exports. Reject cross-project comparisons, require consent metadata for live actuals, and retain human cause-class relevance review. Synthetic actuals now share the example pack's project identity and remain explicitly synthetic.

Repeat local integration verification (two synthetic evidence writes, no paid calls):

```bash
.venv/bin/python scripts/check_live_application_integration.py --write-evidence --output docs/stage5_integration_check.json
.venv/bin/python -m pytest -q
```

**Mandatory blockers before the Stage 5 live-evaluation exit:**

1. Complete S2-01/S2-02/S2-04: approved pre-build founder brief and six frozen task rubrics registered with matching IDs/versions, project identity, `setup_fixture: false` and truthful `approved_for_evaluation: true` metadata.
2. Complete S2-03: dated/cited approach prices and input/output rates for the configured Lightning/Ultra routes, including the critic. The registered `sample/model-a`/`sample/model-b` fixtures do not price those routes. Unknown rates stay unknown.
3. Complete S2-05's server-side sealed permissions. Controller denials pass; namespace separation and the current app credential do not prove server enforcement.
4. Run an explicitly approved, spend-capped live evaluation and preserve candidate/critic Runtime receipts, Zetaris source IDs, H-MEM trace and final decision evidence. No fixture/test-double run substitutes for this proof.

S2-06 private actuals are required only for the real retrospective comparison, not for the initial recommendation. Only this execution plan has been updated among the planning documents.

## Stage 6 — Verify from a judge's point of view

**Dependency:** Stage 5. **Guide:** pp. 20, 23–24. **Exit:** a clean teammate can reproduce both the offline and live paths.

- [ ] From a fresh checkout, install documented Python and Node dependencies, run `python -m pytest -q`, and run all three sample examples with Zetaris and Nightshift **stopped**. Edit one supported input and run a new in-domain input; outputs must change appropriately and remain labeled `SAMPLE/OFFLINE`.
- [ ] On the integration host, run a small live input through `run.py`. Verify its trace contains a successful project Zetaris query with source IDs, an H-MEM recall/remember operation, a Nightshift candidate request, and a Nemotron critic request with resolved model evidence. Verify the final pack cites the same records.
- [ ] Run a live all-pass/no-repair case, one evidence-triggered correction, an unapproved-evaluation case, a missing-source case, a timeout/outage case, a duplicate `run_id`, and a pre-freeze sealed-source denial. Check that no holdout observation enters a repair prompt.
- [ ] Run `scripts/compare_retrospective.py` only after a frozen/complete pack; first test with the synthetic sample and then with the private live actuals. Preserve the N=1 and no-savings-claim limits.
- [ ] Update README commands and status to match reality. It currently says “10 passing” and says the comparison script is pending. Confirm the benchmark and demo use the same six-task manifest. Explain sample versus live behavior and the exact setup prerequisites.
- [ ] Prepare the public repository, concise demo video, slide deck, sponsor-technology explanation, and pre-existing-components declaration. Check links in a signed-out browser and review all recorded screens and tracked files for secrets. Re-check the live event rules and submission form before the **27 October 2026, 23:45 UTC** deadline.

## Minimum evidence to call the project ready

1. `./verify.sh` reports 9/9 and authenticated Zetaris REST SQL returns a project row, not just `SELECT 1`.
2. A live decision cites records from Zetaris, including a pricing record, and shows no sealed read before freeze.
3. The H-MEM integration test passes; a later run visibly uses a recalled, project-scoped constraint.
4. The live trace and Nightshift receipt agree on a real candidate request and an actual Nemotron-backed critique that affects a validated next action or an honest no-change result.
5. A fresh checkout completes the documented offline example and the documented live run without hand edits to source or undisclosed setup steps.
6. README, report, demo, and submission describe only behavior the recorded runs support.

**Priority if time is short:** Stages 1–5 and their proof come before Streamlit polish, extra charts, or additional founder cases. A working CLI with truthful evidence is sufficient for the core demonstration; the UI can follow after the sponsor-backed vertical slice.
