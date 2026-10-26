# Submission review against the strong and weak examples

Reviewed October 25, 2026. Base revision: `9936c6683b205a1a69b57ce063c11c32a0bb0c64`, **including the current uncommitted working tree**. This review records findings; it does not implement fixes or close milestones.

## Verdict

**The repository meets several engineering practices in the examples, but it does not yet demonstrate the working, integrated agent submission they describe.** The offline calculator and programmatic interface are credible foundations. The remaining work is primarily real sponsor execution, demonstrable feedback that changes a decision, output-bound review, usable founder results, and release evidence.

The distinction matters: a complete sample pack proves an input-dependent estimate. It does not prove live agent collaboration, identified Nemotron execution, Zetaris price/evidence round trips or H-MEM persistence. The repository now reports that distinction explicitly through its readiness contract; retain that honesty.

Do not assign an expected judging score from passing tests. Several of the highest-impact criteria require artifacts and actual executions that are not available in the reviewed tree.

## Review sources and precedence

Both supplied files were treated as reference material and preserved:

- [Strong Submission Examples](/Users/muthumeena/Downloads/strong-submission-examples.md): particularly §§1–5, 7–8 and 13–16.
- [Weak Submission Examples](/Users/muthumeena/Downloads/weak-submission-examples.md): particularly the sponsor, collaboration, hardcoding, reproducibility and submission-artifact examples, and §§20–22.
- [Current product specification](../Planning/07-Realignment-v4.md), [gap implementation guide](09-v4-Gap-Implementation-Guide.md), [gap review](08-v4-Integration-Gap-Review.md), current code, tests and local sample outputs.

The examples say that Official Rules take precedence. This review did not obtain or verify the current official event-page rules or the submission form. Consequently, this is an evidence/quality review against the supplied examples, not a declaration of official eligibility or disqualification. In particular, their Cursor wording must be reconciled with the optional-tool interpretation recorded in the older [guideline alignment review](../Planning/05-Guideline-Alignment-Review.md). Do not invent or exaggerate Cursor use to satisfy an example.

The ChurnWhy architecture, six-agent layout, FastAPI endpoint, Dockerfile, numeric confidence and automatic sample fallback are illustrative choices. The project can meet the underlying quality bar with its documented JSON CLI, bounded controller and deterministic evaluation. Copying those examples is unnecessary.

## Verification performed

Portable results and reviewed-source hashes are in [submission-guideline-review-checks.json](submission-guideline-review-checks.json). This artifact is outside the currently ignored `docs/evidence` directory so it can be included with the review in Git.

| Check | Observed result | What it establishes |
|---|---|---|
| `.venv/bin/python -m pytest -q -rs` | **376 passed, 9 skipped**, 5.15 seconds | Offline regressions, including scripted inference and HTTP fixtures; not live sponsor readiness |
| `.venv/bin/python scripts/check_sample_examples.py` | **Three PASS results**, with 4 / 3 / 2 feature tables | All three example CLI workflows produce honest offline estimates under blocked Python networking and disabled dotenv loading |
| Copied request with a fresh run ID and doubled prototype volume | 50 → 100 users; calls 500,000 → 1,000,000; displayed monthly estimate $580.25 → $1,160.50 | The selected sample calculation responds to new input; no saved-answer replay was needed |
| Mutation-run execution/readiness | Zero dispatches; estimated tokens; sponsor readiness `not_verified` | The sample does not disguise estimates as measured model work |
| H-MEM test | One required feature test skipped because the bridge/reference is not installed | Engine proof remains open; the other eight skips are shelved retrospective tests |
| Limited current tracked-file credential-pattern check | No tracked private `.env` file and no matches for the checked credential/private-key shapes | Limited hygiene evidence only; not a full history or credential audit |
| GitHub repository metadata via connected GitHub tool | `404 NOT_FOUND` for the configured origin | Public visibility remains unverified; the result does not establish whether the repository is private or inaccessible to the connector |

The mutation amounts are synthetic sample estimates, not actual charges, savings, revenue or evidence of model quality. They apply to one selected feature/model/stage row, not the aggregate stack.

Temporary evidence locations, also recorded in the portable JSON:

```text
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-sample-check-2x2ml8_0/manifest.json
/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-submission-review-ds6lyr4o/manifest.json
```

These checks used the configured Python environment, not a clean installation on a second machine. No paid inference or production source registration was performed during this review. The working tree is changing; the hashes identify the inspected sources more precisely than the unchanged base commit alone.

## Assessment against the six judging areas

The weights below come from the supplied examples; they are not a prediction of awarded points.

| Area | Example weight | Assessment | Evidence and next improvement |
|---|---:|---|---|
| Impact | 30 | Partially evidenced | README names solo founders, the cost-planning problem and the Explain Why track. Outside-founder before/after decisions and measured usefulness remain absent from the reviewed evidence. Collect consented observations, including failures. |
| Technical | 20 | Strong offline base; live workflow incomplete | CLI, typed contracts, Decimal economics, structured errors and tests work. Zetaris typed reads/writeback and the real H-MEM engine remain missing; no current complete live run is demonstrated. |
| Innovation | 15 | Promising design, insufficient live proof | Measured model comparison, deterministic quality gates and a flags-only Critic are meaningful choices. Prove a feedback decision that changes the evaluated configuration and final recommendation. |
| Demo | 15 | Not evidenced in the reviewed tree | No final 1–4 minute video, eight-point deck or linked release recording was found. Planning notes are not those artifacts. |
| Product & UX | 10 | Partially implemented | Structured stage tables and editable assumptions exist. Founder form/results UI, generated-output review, aggregate budget fit and complete revenue/margin presentation remain open. |
| Sponsor technology | 10 | Roles designed; functional proof incomplete | Nightshift has a real adapter and Zetaris has a query transport, but source stubs, missing H-MEM and no corroborated feature execution prevent a strong end-to-end claim. Cursor attribution requires truthful evidence and rules reconciliation. |

## Findings that materially affect submission quality

### R01 — Blocker: sponsor names and connectivity do not yet establish a working integration

**Example concern:** Weak Examples 1–2; Strong §§2, 4–5.

`read_brief`, `read_models`, `read_approaches` and `write_evidence` still raise `NotImplementedError` in [live_zetaris.py](../app/adapters/live_zetaris.py). [H-MEM](../app/engines/hmem/bridge.py) validates a protocol but lacks the actual installed bridge/reference. The live CLI constructs it before controller execution, so missing setup blocks the integrated run. Source-query transport and `SELECT 1` are useful diagnostics, not proof that a sourced price affects a decision or that measured evidence can be recalled.

**Improve:** finish M05/M06 source acquisition and typed reads/writeback, M07 real engine delegation, and M08 a small identified candidate run. Reuse reviewed historical integration behavior where compatible rather than restoring obsolete contracts wholesale.

**Acceptance:** retain one revision-bound run with a cited price read through Zetaris, a real Nemotron-backed task through Nightshift, valid measured usage, and matching evidence IDs from writeback/readback. Separately prove real H-MEM save → new process → recall → project isolation → audit. Do not require the entire controller to work before independently testing each component.

### R02 — High: the Planner's current authority is narrower than its name and proposed workflow imply

**Example concern:** Weak Examples 3–5; Strong §§3 and 13.

The controller makes distinct Planner and Critic calls in scripted live tests, so this is not simply one prompt relabeled as multiple agents. However, [the Planner implementation](../app/controller.py) currently produces domain risks only. Tasks, expected output lengths and checks arrive in the input. Its reasoning does not create or revise the task plan used by the Analyst. Sample mode does not run either model role.

**Improve:** deliver M09's typed task/rubric plan, frozen before candidate execution, and trace its downstream use. Describe the current Analyst honestly as controller-driven task execution and calculation; do not inflate deterministic functions into additional reasoning agents.

**Acceptance:** a founder supplies the intended feature-level brief rather than implementation-ready rubrics; the Planner produces validated task/check definitions that change the actual execution inputs. A model-proposed action is accepted or rejected by controller rules with a recorded reason. A bounded useful feedback loop is sufficient; adding more agent names is not.

### R03 — High: the Critic cannot reliably ground unsupported-claim flags in its current context

**Example concern:** Strong trace example removes unsupported claims based on evidence; Weak Example 4 requires information exchange with consequences.

`_critique` currently passes rubric descriptions, estimated/measured output tokens and the first output excerpt. It omits the actual example input/approved facts and input-token comparison. A role asked to identify claims unsupported by the input needs that input or a bounded evidence representation.

**Improve:** M09 should provide approved inputs, source references, both token directions and disclosed sample coverage. Keep its existing flags-only authority; deterministic checks and human review decide quality.

**Acceptance:** the retained Critic request contains enough bounded evidence to evaluate the flagged claim, and the resulting controller action references the affected immutable sample. Unsupported model verdict/score fields remain ignored.

### R04 — High: repair and review must be bound to the configuration used for the recommendation

**Example concern:** Strong collaboration changes later behavior; a cosmetic loop is a weak pipeline with extra labels.

`_repair` creates a rerun and may add its measured cap to `output_caps`, but `_project` still reads quality results from the original `runs` map. The cap acceptance check detects regressions from previously passing checks rather than requiring every critical rerun check to pass. [HumanReview](../app/contracts.py) and [rubric overrides](../app/rubric.py) match feature/model/check without an immutable output/configuration reference. A prior approval can therefore apply to new content.

**Improve:** implement M10's effective-configuration selection and immutable review binding. Preserve original and repaired versions for audit, and use one accepted version's tokens and quality together in the final projection.

**Acceptance:** changed outputs invalidate prior reviews; pending/failed critical checks prevent quality qualification; an accepted repair visibly changes the corresponding projected configuration while rejected repairs do not. The final evidence points to exactly what was reviewed. Do not manufacture a failure or force a favorable correction just to make a demonstration.

### R05 — High: memory does not yet influence a later decision

**Example concern:** Strong reasoning architecture uses earlier decisions to change the current one; sponsor technology must have a real role.

The controller consumes recalled `memory_ids` but discards returned context. It recalls `confirmed_constraint` and automatically saves `accepted_finding` model-stack data on completion. Evaluation authorization is not separate acceptance of that decision. Merely installing the engine will not resolve those semantics.

**Improve:** M11 should persist explicitly accepted, scoped assumptions/decisions, reuse compatible record kinds, reconcile recalled context with current founder inputs and show a dated comparison.

**Acceptance:** after restart, an accepted prior assumption changes or constrains a later plan/projection, with source IDs and an explanation; a new confirmed founder input overrides older conflicting context. Do not require an invented model-quality score or hidden reasoning transcript as proof.

### R06 — High: real price collection fits the plan, but its evidence meaning must remain correct

**Example concern:** load-bearing data access, reproducibility and limitations.

The selected [OpenRouter snapshot approach](10-OpenRouter-Source-Options.md) fits M05/M06. The collector is still absent, sample rates are unverified, and the live model query is bounded to 50 rows. API reachability, a locally advertised model and a chosen Nemotron candidate do not establish an applicable serving-provider tariff. OpenRouter market references currently have a separate, shortlist-only contract.

**Improve:** collect and validate raw/normalized data, publish immutable S3 versions with manifests and hashes, query a pinned version through Zetaris and explicitly map catalog IDs to execution model/provider/variant. Filter eligible IDs or paginate without silent truncation. Preserve missing terms as unknown.

**Acceptance:** the final recommendation traces to a retained source version and applicable rates. Paid OpenRouter projections, NVIDIA trial-credit execution and local hardware costs remain clearly separate scenarios. M05's collection does not replace M06's measured-evidence writer or M08 identity verification.

### R07 — High: submission artifacts and clean-clone accessibility remain unverified

**Example concern:** Weak Examples 8–9 and 13; Strong §§7–8 and 15.

There is no verified public-access check, second-machine rehearsal, final video/deck or submission-form receipt in the reviewed repository. The README quick start still uses `git clone <repo>`. Live setup needs source registration and Node/reference instructions beyond private console values. A passing local virtual environment cannot establish that a judge can install and run the project.

**Improve:** complete M14 with an actual clone URL, exact tested setup/runtime versions, sample-first commands, supported live setup and artifact links. Test public repository/artifact access while logged out. Keep provider keys out of all screen recordings. Reconcile pre-existing-work and contributor declarations with actual provenance and official rules.

**Acceptance:** a teammate can run a fresh sample clone without keys or a local GPU; the integration host can run the separately documented sponsor path. Retain command transcripts and revision. Supply a 1–4 minute real-run video and a deck covering the eight supplied topics. Presence of a checklist alone is not completion.

### R08 — Medium: founder actionability needs more than valid JSON

**Example concern:** Impact and Product & UX; the output should support a real decision.

The CLI is a valid programmatic interface and should remain available. It is not a substitute for v4's intended founder form/results/review experience. The stack-wide monthly budget fit, stage revenue/margin and output-bound review flow are still incomplete. The README reports founder-impact evidence as self-evaluation only.

**Improve:** deliver M12/M13 after reliable live decisions, with editable assumptions, measured-versus-estimated labels, stage comparisons, source age, review of actual outputs and export. Use one or two consented outside-founder sessions to record the initial expectation, observed recommendation, decision afterward and confusing/negative findings.

**Acceptance:** a founder can enter a normal idea, understand cost/quality uncertainty, review the generated samples and decide what to do next without editing Python or supplying internal rubric JSON. No claim about a dollar amount saved is needed or justified by these sample projections.

### R09 — Medium: present implementation status and evidence distinctly

**Example concern:** sponsor padding, misleading diagrams and claims that cannot be verified from traces.

The README now reports 376 passing tests and identifies integration gaps, which is useful. Its architecture and sponsor-role descriptions still need careful reading as intended behavior rather than complete proof: H-MEM context is not applied and real sponsor execution has not been retained here. The older planning review's statements about document compliance are not proof that today's software is integrated. A newly implemented dispatcher also exists while M04 remains pending in the inspected ledger.

**Improve:** before release, distinguish implemented/fixture-tested/live-verified paths in the diagram and sponsor proof table, link actual artifacts, and reconcile milestone evidence with the reviewed code. Do not automatically mark M04 complete because the full suite passes; execute and record its own acceptance checks.

**Acceptance:** each sponsor claim names an artifact, run/revision and meaningful action. A judge can distinguish a synthetic fixture, a connectivity check and a measured feature run without guessing.

## Disposition of every weak-pattern example

| Weak example | Current assessment | Required next action or retained strength |
|---|---|---|
| 1: required sponsor technology missing | Not demonstrated end to end | R01; give Zetaris and Meterless actual functional proof |
| 2: sponsor names bolted on | Risk remains until runtime evidence exists | R01/R06/R09; a `SELECT 1` result alone does not close this |
| 3: linear pipeline | Conditional critique/repair exists in code and fakes; live consequence unproven | R02–R04; prove the branch changes accepted evidence/decisions |
| 4: prompt wrappers | Controller has state, deterministic authority and tool boundaries; Planner integration remains narrow | R02/R03; make role outputs influence later work |
| 5: one agent presented as many | Separate role calls exist in scripted tests | Keep truthful role/authority descriptions; prove real interactions |
| 6: hardcoded final outputs | No replay path found; volume mutation changed the sample result | Preserve input-dependent logic and clearly label sample estimates; fresh live-input behavior remains unproven |
| 7: missing/unusable logs | JSONL events, correlation, usage and readiness handling implemented | Retain real collaboration traces and a short readable explanation of the decisive branch |
| 8: repository not public | Unknown; connector lookup returned 404 | Logged-out public-access test; do not infer privacy from the connector alone |
| 9: broken setup/manual steps | Local offline checks pass; clean-clone/live setup unverified | R07; automate registration and test the documented path on a second machine |
| 10: UI only | Avoided: JSON CLI is implemented | Keep the CLI while completing the founder UI rather than substituting UI polish for execution |
| 11: no failure handling | Structured errors, validated reads/readiness, timeouts and a durable dispatcher exist | Retain the new offline protections; finish M04 evidence and test actual integration outages separately |
| 12: committed secrets | No matches in the limited current tracked-file check | Preserve `.env.example` hygiene; public-release assurance still needs a suitably scoped final audit |
| 13: missing deck/weak video | Final artifacts not found in the reviewed tree | R07; planning outlines are not the required artifacts |
| 14: undeclared pre-existing work | README declaration exists; creation provenance/submission form not verified | Verify and attribute upstream components; reconcile declarations with official rules |
| 15: unclear track fit | Largely addressed in README/product scope | Carry the same Explain Why framing into the demo, deck and evidence-backed result |
| 16: too much data/too slow | Small bundled data and quick offline checks are positive | Keep collector and evaluation bounds; measure first-run installation and actual live runtime separately |

## Trace and example adaptations that should remain deliberate

- **No fabricated confidence:** the source examples include numeric confidence, but the current trace intentionally omits invented scores. Keep evidence status, pending checks, readiness and measured coverage explicit; they are more useful than an unsupported probability.
- **Console stream:** readable event lines currently go to stderr, JSONL goes to files, and stdout carries one `final_result`. The supplied examples prefer key events on stdout. Document this machine-readable CLI contract and show combined output in the demo if needed; do not break it just to reproduce an illustrative transcript.
- **No silent sample fallback:** an outage should produce an explicit unavailable/partial result or a user-selected sample run. Do not mix placeholder prices with live measurements and call the result sponsor-verified. Bounded retries are appropriate only when dispatch/charge semantics make them safe.
- **Role authority:** deterministic checks and output-bound human review should retain quality authority. A flags-only Critic is compatible with real collaboration; granting it unilateral pass/fail power is unnecessary.
- **Scope control:** no additional agent count, microservice, hosted deployment, GPU download or Dockerfile is justified solely by the example architecture. Complete the shared-core workflow and evidence first.

## Recommended completion sequence

| Order | Work | Exit evidence |
|---|---|---|
| 1 | Finish and record M04 safeguards; implement M05/M06 source path and M07 engine independently | Bounded-dispatch fixtures; dated catalog/tariff manifest and real Zetaris read/writeback; real engine persistence/isolation test |
| 2 | M08 tiny live evaluation, within verified rates/bounds | Identified candidate responses, including Lightning if available, valid usage, correlated trace, exact evidence readback; no requirement to spend before prerequisites are satisfied |
| 3 | M09/M10 grounded planning, critique, effective repair and immutable reviews | A valid fresh brief, a traceable feedback decision and one accepted configuration used consistently for quality and cost |
| 4 | M11/M12/M13 memory comparison and founder workflow | Prior accepted context affects a rerun; aggregate cost/revenue output; usable form/results/review/export |
| 5 | M14 release rehearsal and artifacts | Logged-out links, clean-clone report, final video/deck, sponsor explanation and accurate declarations |

The existing M00–M03 evidence should be retained rather than redone as a substitute for these missing live and product checks. M04's implementation is present in the reviewed working tree, while its milestone was still pending in the inspected ledger; resolve that discrepancy with the milestone owner before release.

## Submission-ready evidence to retain

- [ ] A small current-revision live pack, trace, model/provider mapping and priced source manifest.
- [ ] Zetaris price query plus actual measured-evidence write/readback with matching IDs.
- [ ] Passing real H-MEM feature test without a required skip, plus an accepted-context rerun comparison.
- [ ] A real collaboration branch with its input evidence, controller decision and downstream consequence.
- [ ] Human reviews bound to the exact generated outputs used for the recommendation.
- [ ] Three fresh-input examples whose labels clearly distinguish sample estimates and live measurements.
- [ ] A clean-clone report and accessible public repository/artifact links.
- [ ] A 1–4 minute real-run video, eight-topic deck and specific sponsor explanation.
- [ ] Accurate provenance, data/licence and development-tool declarations checked against the applicable official rules.
- [ ] An explicit limitations statement covering pricing applicability, small samples, audio estimates and projected production levers.

These are requested evidence targets, not assertions that the repository already satisfies them.
