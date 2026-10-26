# v4 code and integration gap review

Reviewed October 25, 2026, against checkout `9936c66` and the working tree. Review only; application code was not changed.

**Verdict: the offline v4 economics foundation is implemented, but this checkout is not ready for a live integration rehearsal or sponsor-compliance sign-off.** Required sponsor functionality is incomplete, and several controller/economics defects can affect the recommendation after integration is restored.

## Scope and evidence

- Authoritative product requirements: [07-Realignment-v4.md](../Planning/07-Realignment-v4.md), version 4.1, with non-conflicting inherited requirements.
- Integration reference: supplied `7e1b7ca3995b4673b30a73555c87e71f.pdf`, **Participant Setup Guide**, last updated October 21, 2026, all 30 pages reviewed. PDF page numbers below refer to this file. It is a setup guide; this review does not independently certify the current Official Rules or submission form.
- Reviewed application, adapters, H-MEM wrapper, tests, scripts, sample data, examples, README and existing local traces. Private `.env` contents were not inspected.
- `.venv/bin/python -m pytest -q`: **100 passed, 9 skipped**. Eight skipped tests concern the shelved retrospective; one is the real H-MEM feature test.
- Ran all three bundled inputs through the sample controller with temporary databases/logs: all completed, producing respectively **4, 3 and 2 feature cost tables**, with zero executed model runs.
- Ran focused, temporary probes of lever composition, validation, repaired quality, timeout dispatch, offline memory and trace masking. Results appear below. No new live model calls or external writes were made.

## Required integration status

| Requirement | Current evidence | Assessment |
|---|---|---|
| Zetaris supplies application evidence, PDF pp. 5–11, 22 | REST transport exists; all application read/write methods are stubs | Blocked in current code |
| At least one working Meterless Engine, PDF pp. 12–15 | H-MEM Python wrapper only; engine assets absent; feature test skipped | Blocked |
| Nightshift as primary inference provider, PDF pp. 16–20 | Correct provider boundary, headers, discovery and completion transport implemented | Implementation present; current end-to-end proof missing |
| Nemotron powers a working feature through Nightshift, PDF pp. 17–20 | Mandatory open-source candidate selection exists; bundled routes are placeholders; no model-bearing request in reviewed local traces | Award proof unverified |
| Reachable, registered data storage, PDF pp. 22, 26 | No source-registration script or live source manifest in this checkout | Clean-clone setup incomplete |
| Credential handling, PDF pp. 4, 11, 18–19 | Placeholder environment template, ignored private environment files, no direct NVIDIA client | Structure aligned; no credential/history audit performed |

**Existing integration progress is acknowledged:** the local `trace-localstack-register-*.jsonl` and `trace-live-integration-*.jsonl` files record successful Zetaris queries and earlier writeback events. The latter runs stopped at `evaluation not approved` and contain no model-bearing inference events. They demonstrate earlier data-layer work, but the current adapter has no corresponding implementations. Reconcile or restore that work and regenerate evidence from the realigned revision. These logs are ignored by Git and are not clean-clone evidence.

## Findings and acceptance checks

### F01 — Blocker: current live Zetaris path cannot produce a pack

**Evidence:** [live_zetaris.py:50](../app/adapters/live_zetaris.py#L50), [controller.py:252](../app/controller.py#L252), [run.py:44](../run.py#L44). `read_approaches`, `read_models`, `read_brief` and `write_evidence` raise `NotImplementedError`. Once H-MEM construction succeeds, the controller will fail on the first pricing read. `_read` only catches `KeyError`, so the CLI turns this into an operational error rather than a useful evidence-gap pack. There is no evaluation-evidence readback method. The first approaches query is also called twice, while the models read bypasses `_read`.

**Requirement:** v4 §§3, 8, 11; PDF pp. 11, 22. Every price must come through Zetaris; measured runs must be written back.

**Acceptance / owner:** Meena: implement typed reads and supported writeback/readback, restore source-registration tooling, and demonstrate a real price row feeding a stage calculation plus a measured run read back through Zetaris. Preserve source IDs, versions and provenance. Confirm the installed response shape and the guide's `source: "SqlEditor"` request field; current requests omit it. Its absence is a contract discrepancy to verify, not a proven server rejection.

### F02 — Blocker: required H-MEM engine is absent; offline wiring also has a latent failure

**Evidence:** [bridge.py:38](../app/engines/hmem/bridge.py#L38), [test_hmem_engine.py:5](../tests/test_hmem_engine.py#L5), [sample.py:85](../app/adapters/sample.py#L85), [run.py:33](../run.py#L33). `bridge.mjs`, `PINNED_REVISION` and the reference engine are absent. Live controller construction therefore raises `SetupIncomplete`. Separately, `SampleMemory(bridge_available=True).recall(...)` returns `None`; the controller calls `.get()` on that value. Installing the bridge without fixing this adapter would break the sample path once its availability check succeeds.

**Requirement:** v4 §§3, 8, 11; PDF pp. 14–15 explicitly require a working engine feature and passing evidence. A provider connection does not satisfy this requirement.

**Acceptance / owner:** Pradeep: install and pin the real reference, delegate offline operations to it, document Node/reference installation, and pass save → restart → recall → cross-project isolation → audit tests in live and offline configurations.

### F03 — High: candidate identity and Nightshift proof remain incomplete

**Evidence:** [live_nightshift.py:28](../app/adapters/live_nightshift.py#L28), [controller.py:635](../app/controller.py#L635), [test_controller_live_fake.py:34](../tests/test_controller_live_fake.py#L34). Discovery and usage capture are implemented, but controller coverage uses a scripted fake. Reviewed local traces contain no `nightshift_request` or `run_feature` proof with a model identity. `_execute` logs the resolved model but does not check that it matches the model priced by the selected snapshot; a missing or differently resolved identity can still produce a recommendation at the requested route's rates.

**Requirement:** v4 §§4, 7, 11; PDF pp. 19–20. Explicit underlying Nemotron identity matters for the NVIDIA award.

**Acceptance / owner:** Pradeep: preserve one real response per candidate with requested/resolved IDs, usage including reasoning semantics, latency and correlated Nightshift receipt where aliases need resolution. Bind that identity to the priced variant; disclose or stop on unresolved identity. Run the complete founder workflow, not just discovery or health checks.

### F04 — High: production pricing evidence and reproducible registration are missing

**Evidence:** [data/README.md:9](../data/README.md#L9), [pricing_snapshots.json](../data/sample/pricing_snapshots.json), repository `scripts/`. Prices, intelligence scores and market references are explicitly placeholders. No committed S3 registration script, real source inventory with object versions/hashes/licences, or installed API response fixture is present. Earlier registration traces cannot recreate the setup from this checkout.

**Requirement:** v4 §§3, 8, 11; PDF pp. 22, 26 require storage Zetaris can reach.

**Acceptance / owner:** Isioma + Meena: supply dated, cited snapshots for actual pinned routes, provider lever terms and source metadata; register them using a documented repeatable process. Keep bucket credentials on the Zetaris side. The sample placeholders are honestly labeled and may remain as offline fixtures, but cannot substantiate live costs.

### F05 — High: the founder form and results UI are absent

**Evidence:** [run.py](../run.py) is the only entry point; `streamlit` is a dependency but there is no Streamlit application. JSON contracts do not provide the required form, editable assumed defaults, chart, switch-point view, evidence timeline or review/acceptance interaction.

**Requirement:** v4 §§2, 6, 11. This is a product/demo gap; the supplied setup guide does not require Streamlit specifically.

**Acceptance / owner:** Shrie: form → shared controller → pack → table/chart/switch points/trace/export in both modes, with persistent offline labels and duplicate-submit protection.

### F06 — High: Planner does not implement the v4 task/rubric planning step

**Evidence:** [controller.py:571](../app/controller.py#L571), [contracts.py:237](../app/contracts.py#L237), [economics.py:434](../app/economics.py#L434). The Planner generates domain risks only. Tasks, expected output length and rubric checks must already be supplied in the input JSON. Rubrics default to an empty list, so a founder who supplies only the specified form fields cannot obtain a quality-qualified recommendation. Cost-critical missing volume inputs add questions but do not prevent paid sampling. `quality_needs` is not used to generate or validate task checks.

**Requirement:** v4 §3 step 2 and §7: representative tasks, 3–5 deterministic checks plus human review, and clarification of cost-critical inputs.

**Acceptance / owner:** Narin: create a validated task/rubric plan from founder features and quality needs, obtain necessary clarifications before paid execution, then freeze the shared checks for candidate comparison. If planning is deliberately manual, amend the authoritative requirements and expose that work in the UI.

### F07 — High: memory currently cannot change a later decision

**Evidence:** [controller.py:233](../app/controller.py#L233), [controller.py:335](../app/controller.py#L335). Recall consumes only `memory_ids`; recalled `context` is discarded. There is no comparison of earlier stage decisions to the current run, no confirmed-assumption save path, and no reconciliation with current founder inputs. The final save writes `kind=accepted_finding`, whereas recall asks for `kind=confirmed_constraint`. Completion automatically treats the model stack as accepted; evaluation authorization is not a separate acceptance of those decisions.

**Requirement:** v4 §3 steps 1 and 8, §8; PDF p. 14's H-MEM example requires earlier information to be used on a later task.

**Acceptance / owner:** Narin + Pradeep: explicitly confirm assumptions/decisions, store and recall compatible record kinds, incorporate valid scoped context, prioritize current confirmed inputs, and display what changed after restart. Installing the engine alone will not close this gap.

### F08 — High: overlapping cost levers can produce negative costs

**Evidence:** [economics.py:262](../app/economics.py#L262), [economics.py:275](../app/economics.py#L275), [economics.py:366](../app/economics.py#L366). Batch discounts the original cost, then the output-cap delta independently removes output cost at the full rate. A background task with 1 input token, 1,000 output tokens, a measured cap rerun of 100 output tokens, prices $10/$20 per million, 1,000 calls/month, 10% retries and 50% batch gives **$22.01 gross, −$11.01 batch, −$19.80 output cap, and −$8.79 net**. This is accepted by the contracts and can distort model ranking and switch points. Long-context adjustments similarly use the original tokens/base rates rather than a consistently recomputed effective request.

**Requirement:** v4 §5.1: eligible levers, full precision and valid monthly projections.

**Acceptance / owner:** Narin: compute an effective request after the cap, apply the appropriate provider tariff, then eligible caching/batch combinations. Derive separate explanatory deltas from that calculation. Add interaction fixtures, including batch + cap and long-context + cap. Do not merely clamp negative totals to zero.

### F09 — High: repaired quality does not feed the recommendation

**Evidence:** [controller.py:776](../app/controller.py#L776), [controller.py:800](../app/controller.py#L800). A repaired run is appended to the output and may supply an output-cap lever, but `_project` still reads rubric results from the original `runs` map. A focused fake run changed a frontier critical check from fail before repair to pass after repair; projection continued using the failed original. Repair validation checks regressions from previously passing critical checks, rather than requiring all critical checks to pass before accepting the cap.

**Requirement:** v4 §3 steps 5–8: check the corrective action and recommend from the resulting evidence.

**Acceptance / owner:** Narin: retain both versions for audit, but select one validated effective configuration whose measured tokens and rubric results jointly feed costs, model stack and switch points. Explicitly reject or qualify repairs with any failed/pending critical checks.

### F10 — High: retries and spend reservations do not enforce the stated spend ceiling

**Evidence:** [controller.py:85](../app/controller.py#L85), [controller.py:198](../app/controller.py#L198), [controller.py:629](../app/controller.py#L629), [contracts.py:571](../app/contracts.py#L571). `max_spend_usd=1000` is schema-valid despite the $25 cap. Normal generations have no output-token bound; reservation is an estimate times three, and reconciliation may push spent above the ceiling after the request. Planner/Critic each reserve $0.05 without reconciling their measured cost. `_call` retries every exception, including ambiguous post-dispatch timeouts, without a new cost reservation or request checkpoint. A focused timeout probe dispatched the same operation **three times**. The SQLite events table is created but not used for per-request dispatch/reconciliation records.

**Requirement:** inherited controller limits and v4 §7: bounded, affordable execution; ambiguous outcomes must not be blindly replayed.

**Acceptance / owner:** Narin + Pradeep: enforce the supported spend ceiling in contracts, bound normal output sizes, reserve conservatively for every dispatch including roles/retries, and reconcile all measured charges. Retry only classified safe failures; persist pending/unknown outcomes and stop when execution may already have happened. Clarify whether the 30 limit counts candidate generations or all dispatches, and enforce the documented choice.

### F11 — High: input validation and founder-editable operating controls are incomplete

**Evidence:** [contracts.py:61](../app/contracts.py#L61), [contracts.py:237](../app/contracts.py#L237), [contracts.py:266](../app/contracts.py#L266), [controller.py:806](../app/controller.py#L806). Negative active users and uses/month are accepted. Feature count is not constrained to 2–5, and feature/check/stage identifiers are not checked for uniqueness even though dictionaries key on them. Build constraints and `features_v1` remain required objects although v4 makes the build panel optional. There is no monthly AI budget field or request-level switch threshold. Focused validation confirmed supplied `monthly_ai_budget_usd` and `switch_threshold_usd` fields are silently discarded; projection always uses the default $100 threshold. Most default feature values have no automatic per-field assumed provenance.

**Requirement:** v4 §§2, 5.1: one usable form, optional build inputs, editable threshold/defaults and explicit assumption labels.

**Acceptance / owner:** Narin + Shrie: validate ranges and unique IDs, support an idea-only operating workflow with optional build data, expose/persist budget and threshold, propagate them into economics, and label every injected default. Reject unexpected controls rather than silently accepting and ignoring them.

### F12 — Medium: stage revenue, contribution and margin are not implemented

**Evidence:** [contracts.py:52](../app/contracts.py#L52), [contracts.py:488](../app/contracts.py#L488), [controller.py:800](../app/controller.py#L800). Paying fraction and subscription price exist in the old usage contract, but the v4 projection does not read them. It exposes per-feature revenue-per-use shares instead. The older `operating_ledger` function has contribution/margin math, but the v4 controller leaves that ledger unset. There is also no aggregate recommended-stack monthly total across all features to compare with a founder's monthly AI ceiling.

**Requirement:** v4 §§2, 5.1: when revenue is present, show contribution and margin per stage.

**Acceptance / owner:** Narin: aggregate the recommended feature stack per stage and calculate revenue from active users × paying fraction × subscription price; show contribution/margin with absent/zero revenue handled explicitly. Keep the build ledger separate.

### F13 — Medium: Critic lacks grounding inputs and checks route independence only

**Evidence:** [controller.py:434](../app/controller.py#L434), [controller.py:701](../app/controller.py#L701). Critic sees a first-sample excerpt and rubric descriptions, but not the actual example input or approved facts needed to assess unsupported claims. Token-gap payloads compare output only, omitting measured/estimated input differences. Route independence explicitly does not detect two routes from the same lab, while v4 requires a non-candidate lab when available or disclosure of a shared lab.

**Acceptance / owner:** Narin + Pradeep: provide bounded example inputs, approved fact/source references and both token directions; identify sample coverage; attach reliable lab metadata and select/disclose accordingly. Preserve the existing flags-only authority.

### F14 — High: human review results are not bound to the outputs reviewed

**Evidence:** [contracts.py:227](../app/contracts.py#L227), [rubric.py:72](../app/rubric.py#L72), [controller.py:666](../app/controller.py#L666). Reviews match only feature/model/check. They carry no run ID, output reference/hash, sample ID or configuration version. The same input reviews override freshly generated outputs and a changed repair output. A prior approval can therefore qualify content the reviewer has never seen.

**Requirement:** v4 §§3, 7: human review is quality evidence for the measured comparison.

**Acceptance / owner:** Narin + Shrie: bind reviews to immutable output/configuration references, present the generated outputs for review, and invalidate approvals when a repair or rerun changes them. Support review/finalization without unnecessary regeneration of paid samples.

### F15 — Medium: diagnostics and traces can overstate readiness or lose evidence

**Evidence:** [trace.py:16](../app/trace.py#L16), [smoke_live.py:91](../scripts/smoke_live.py#L91), [smoke_live.py:255](../scripts/smoke_live.py#L255), [preflight_windows.ps1:153](../scripts/preflight_windows.ps1#L153). Secret-key matching redacts `prompt_tokens`, `completion_tokens` and the entire `completion_tokens_details` object from trace usage. The pack retains usage, but the per-request JSONL loses it. Zetaris health checks call HTTP success a PASS without verifying the `SELECT 1` result, unlike PDF p. 24. Smoke exits zero when all checks are SKIP because it considers only FAIL; Nemotron completion can PASS without requiring a resolved identity. Adapter request events are written after successful parsing, leaving failures less attributable.

**Acceptance / owner:** Meena + Pradeep: distinguish authentication secrets from numeric token usage; validate query contents and model identity; make required SKIPs result in an incomplete/non-ready outcome; log request attempts and failures with correlation IDs. Add focused diagnostic contract checks.

### F16 — Medium: release evidence and documentation need a v4 pass

**Evidence:** [README.md](../README.md), [CLAUDE.md](../CLAUDE.md), [data/README.md](../data/README.md). The README describes remaining adapters as in progress and uses `git clone <repo>`. There is no complete Node/reference setup, live registration recipe, current model mapping, second-machine rehearsal report, outside-founder feedback evidence, or deck/video artifact in the reviewed tree. `CLAUDE.md` still describes the earlier build-advisor/retrospective design and does not identify `07` as authoritative. These items may exist outside the repository; they were not verifiable here.

**Requirement:** v4 §§7, 9, 11–12 and inherited submission/reproducibility requirements.

**Acceptance / owner:** Narin + Meena, with outside-founder participants: update the working instructions and setup around v4, run a clean clone on a second machine with sample and live evidence, retain consented before/after observations including negative results, and link the tested submission artifacts. Record the exact revision used for evidence.

## Already aligned; retain these decisions

- Primary per-feature/per-stage operating tables and a separate secondary build panel exist.
- API usage is the source of measured tokens; completion tokens include reasoning, which is reported without double billing. Per-call precision and Decimal calculations are implemented.
- Critical deterministic rubric checks gate quality-qualified model choices and switch points. Critic verdict fields are ignored; it cannot directly grade candidates.
- The controller supports one validated corrective action, and selects a mandatory open-source route without allowing `meterless/auto` as a candidate.
- All application inference is routed through Nightshift; no direct-provider fallback was found.
- Sample outputs are input-dependent and honestly labeled; they do not replay saved model answers or invent quality scores.
- Omitting self-host break-even is consistent with the explicit stretch cut when cited throughput is unavailable. Hosted deployment and the shelved retrospective are not blockers under v4.
- The PDF has older summary diagrams/checklists that suggest Cursor is mandatory, but pp. 12–15 explicitly allow any coding tool. The project's coding-tool choice is aligned with that detailed instruction. The app's Nightshift-only policy also satisfies the stricter product design despite older direct-NVIDIA examples in the guide.

## Suggested order to close the gaps

1. **Restore the runnable sponsor path:** F01–F04, including real route/price identity and actual H-MEM persistence. Run the three sponsor checks on the same integration host.
2. **Fix decision correctness before recording:** F08–F11 and F14, then verify repaired quality, combined levers, spend/timeout behavior and fresh-input validation.
3. **Complete the v4 founder workflow:** F05–F07, F12–F13, with memory visibly affecting a rerun and human review tied to actual outputs.
4. **Collect release proof:** F15–F16, three live ideas, outside-founder observations and a second-machine clean-clone rehearsal. Regenerate outputs/traces from the reviewed final revision.

The passing test suite establishes useful offline coverage. It does not close the missing live-engine test, replace current sponsor proof, or cover the reproduced interaction defects above.
