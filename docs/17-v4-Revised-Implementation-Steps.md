# v4 revised implementation steps

Updated 2026-10-26 on branch `feature/realign-07-meena`. This document revises the candidate-selection, billing and NVIDIA parts of the [implementation plan](08-v4-Implementation-Plan.md) after a code review. The plan holds Steps 0–14, the findings table and the handoff checklist; the [evidence ledger](v4-release-checklist.md) holds every result. `Planning/07-Realignment-v4.md` (v4.3) is the product spec and wins where they differ; the candidate selection rules are in its §4.

**Decision recorded 2026-10-26:** the user chose to proceed with Reading A (§2) and updated `07` to v4.3. Narin has not signed off, and the official NVIDIA rule wording is still to be quoted from the organizer's Submission Requirements §4.

## 1. What was wrong, and what changed

Four problems were found in the review, and three more during live runs on 26 October (§3a). All are fixed in code except the R0 wording task.

1. **Hackathon requirements and app requirements were mixed.** The PRD put the NVIDIA proof on the Critic. `07` v4.0 moved it onto the candidate models (commit `0c2f19b`), and code commit `29e97cc` hard-pinned a Nemotron candidate. The record is in `CLAUDE.md`. Fixed by the split in §2.
2. **Candidates were hand-picked.** One model per tier from a hand-made route map, chosen once for all features. Fixed (R3a): per feature, from every priced Nightshift route.
3. **Modality was ignored.** An audio or image feature could get a text-only model. Fixed (R2, R3a).
4. **Billing evidence served three jobs.** Fixed (R1, R4):

| Job | Sufficient evidence |
|---|---|
| Founder-facing cost projection | A dated, cited catalog price read through Zetaris, labeled as a reference |
| The app's own spend while measuring | For every **dispatched** route: a verified rate source and a verified `dispatch_policy` (`completion_limit_includes_reasoning: true`). A verified $0 free-tier rate is valid |
| Sponsor proof | A Nemotron model doing real work through Nightshift with resolved identity logged per request |

## 2. Requirement split (in force)

| Area | Hackathon requirement | App requirement |
|---|---|---|
| Inference path | All inference through Nightshift (`CLAUDE.md` rule 8) | Same |
| NVIDIA proof | **Planner and Critic** run on Nemotron through Nightshift, identity logged | None on candidates |
| Candidate models | None | Chosen per feature from what Nightshift offers, filtered by modality, any lab |
| Candidate prices | None | Dated, cited, read through Zetaris, scope labeled, unknown kept unknown |
| Data layer and memory | Zetaris as data layer; one working Meterless engine with a test | Unchanged |
| Spend safety | None | Every executed route needs verified rates and bounds; others are projected only |

If the official rule instead requires a Nemotron model **among the compared candidates**, allow one (do not pin one); nothing else changes.

## 3. Revised steps R0–R5 (done)

| Step | What was done | Result |
|---|---|---|
| **R0** Decisions and doc alignment | Requirement split decided; `07` set to v4.3; `CLAUDE.md` records the original position, how the confusion started and the decision | Done. Narin sign-off and the official rule quote still open |
| **R1** Planner and Critic on Nemotron | Planner = Lightning, Critic = Ultra, both on a free NVIDIA Developer Program key; verified 0/0 profiles with a cited dispatch policy; role calls recorded by the Dispatcher; thinking off for the Planner (it returned empty responses with it on) | PASS |
| **R2** Modality-aware catalog and contracts | Catalog modalities and open-weights signal kept; `image_in` and `image_out` added; image cost unknown, not zero; schema stays 1.1 (additive) | PASS |
| **R3a** Use-case-driven candidates | Candidates chosen per feature from priced Nightshift routes that cover its modality; tiers derived by rule; no pin; `METERLESS_OPEN_MODEL` is an optional override; `prepare_source_bundle.py --include-discovered` registers every priced route. `tier` stays an optional curated hint for Ultra and Lightning | PASS |
| **R4** Execute versus project | Only candidates with a verified profile are dispatched; the rest are projected only, with a gap, and never recommended; Planner and Critic routes still stop an unproven run | PASS |
| **R5** First bounded live pack | Run `r5-live-20261026-113150-e`: 6 dispatches, $0, all identities resolved, four candidate pairs measured, zero unpublished evidence, one memory save. Three earlier attempts failed and are kept as negative results. Its token and cost numbers predate the memory fix (§3a) | PASS for dispatch, spend, identity and evidence |
| **R9** Stage totals, revenue, budget fit | One monthly AI total per stage (recommended stack, cheapest per feature, one model for every feature), separately for actual-route and OpenRouter-price tables; revenue, AI contribution, margin and budget fit; unknown feature costs never counted as zero | PASS; the recommended-stack total stays unknown until R7 |
| **R10** Streamlit workflow (trimmed) | Form with modality, revenue inputs and up to 3 founder-picked candidates; live progress panel; five views (cost by stage with totals, measured versus estimated, quality checks, risks and gaps, trace and export); stop reasons and setup hints | Live runs from the UI PASS; no human-review controls (R7) |
| **R11a** Live smoke check | `scripts/smoke_live.py` now checks the Planner and Critic routes; 6 of 6 required checks passed | PASS, diagnostic scope |

## 3a. Found during live runs (26 October)

| Finding | Fix | Status |
|---|---|---|
| Nightshift's built-in memory injected an earlier answer into similar prompts under the shared `meterless-scope: user`; Ultra and Lightning returned identical text and input tokens were inflated (1,542 against 751) | The adapter gives every request its own scope (`eval-<random>`) | Fixed and re-measured (Examples 1 and 3). **Token, cost and quality numbers from R5 and earlier UI runs should not be quoted** |
| Ultra (thinking on) put its reasoning inside the answer text, failing JSON checks | The adapter keeps only the text after the last `</think>` | Fixed; confirmed live |
| Thinking on used the whole 1,024-token output cap (Critic, Lightning and Ultra as candidates) | Thinking off for Planner, Critic, Lightning and Ultra through settings (§6) | Workaround; no clean thinking-on measurement exists |
| Estimates left out the instructions sent with each example | The 4/3-rule estimate adds them | Fixed. Estimates still include the brief's assumed production system prompt, which test calls do not send (open modelling decision) |
| Nightshift dropped its OpenRouter routes (111 → 74) | OpenRouter key re-added in Nightshift; verified on the next routed request | Fixed operationally; cross-lab candidates depend on connected providers |
| Projected-only candidates showed no tier | The controller records each candidate's tier per feature | Fixed |

## 4. Remaining steps (not started)

Step detail, requirements and acceptance tests are in the [implementation plan](08-v4-Implementation-Plan.md). These are the additions from this revision:

| Step | Plan step | Findings | Additions from this revision |
|---|---|---|---|
| **R6** Task planning, grounded critique | Step 9 | F06, F13 | The Planner may propose up to three candidates per feature from the filtered pool (formerly R3b); the controller validates each. Critic independence is reported from the real candidate and Critic labs |
| **R7** Review binding, effective repair | Step 10 | F14, F09 | Repair applies to a feature's own candidate |
| **R8** Memory changes a later run | Step 11 | F07 | Accepted decisions store each feature's candidate set and why |
| **R11** Release rehearsal | Step 14 | F15, F16 | Re-run `scripts/smoke_live.py` on the final setup; second-machine clean clone; the sponsor explanation states the §2 split and links the R1, R11a and post-fix receipts |
| *New* Price evidence for the market projection | Step 5 | — | Verify OpenRouter's fee and tariff terms so measured market-price rows need not be lower bounds; add audio conversion rates for audio candidates |

## 5. Order and cut line

Submission closes **Tue 27 Oct 2026, 23:45 UTC (6:45 p.m. Chicago)**; today is Mon 26 Oct. R0 (except sign-off), R1–R5, R9, R11a and a trimmed R10 are done. Remaining, in order:

| Order | Step | Suggested owner | Before submission? |
|---|---|---|---|
| 0 | Close R0: quote the official NVIDIA rule and get Narin's sign-off on `07` v4.3 | Narin | Yes, first; it is a text task |
| 1 | R11 essentials: smoke check on the final setup, clean clone, video, deck, sponsor explanation | Narin, Meena | Yes |
| 2 | R10 polish (layout review in a browser) | Shrie | As far as possible |
| 3 | R6, R7, R8; market price evidence | Team | Only if time remains; otherwise list as next steps in the deck |

Describe anything past the cut line truthfully as not implemented. Do not mark it done because the suite is green.

## 6. Live run settings

Passed on the command line or in `.env` (never committed); documented in `.env.example` and the README settings table:

| Setting | Why |
|---|---|
| `METERLESS_NO_THINKING_ROLES` (`Planner,Critic`) | A role whose thinking exhausts the 1,024-token cap needs it. An empty value means no roles |
| `METERLESS_NO_THINKING_MODELS` (Lightning and Ultra) | Routes that return `empty_response` or hit the 1,024-token cap with thinking on, including as candidates (Lightning did on Example 3, Ultra on Example 1) |
| `METERLESS_REQUEST_TIMEOUT_S` (default 60) | Ultra occasionally exceeds 60 s |
| `SOURCE_INGEST_URL` / `SOURCE_INGEST_TOKEN` | Evidence publisher; without it a run ends `partial` with evidence in the outbox |
| `METERLESS_OPEN_MODEL` | Optional founder override of the open-source candidate; the UI's candidate picks replace automatic selection for a run |
| `ZETARIS_BINDINGS_FILE` | Which registered price tables to read; the UI shows the snapshot it will use |

`meterless-scope` is no longer a setting: the adapter sets a unique scope per request (§3a).

## 7. Decisions kept from the original review

- Per-feature, per-stage operating tables with a separate secondary build panel; measured tokens come from API usage, with reasoning counted inside completion tokens and not billed twice; Decimal arithmetic.
- Deterministic critical checks plus human review decide quality. The Critic only flags; verdict fields are ignored.
- All inference goes through Nightshift with no direct-provider fallback; `meterless/auto` is never a candidate.
- Sample outputs are input-dependent, labeled `SAMPLE/OFFLINE`, and never replay saved model answers or invent quality scores.
- Self-host break-even, a hosted deployment and the shelved retrospective are not blockers.
- The organizer material allows any coding tool; do not invent or exaggerate Cursor use.
