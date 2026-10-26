# v4 revised implementation steps

Updated 2026-10-26 on branch `feature/realign-07-meena`. This document revises the candidate-selection, billing and NVIDIA parts of the [implementation plan](08-v4-Implementation-Plan.md) after a code review. The plan holds Steps 0–14, the findings table and the handoff checklist; the [evidence ledger](v4-release-checklist.md) holds every result. `Planning/07-Realignment-v4.md` (v4.3) is the product spec and wins where they differ; the candidate selection rules are in its §4.

**Decision recorded 2026-10-26:** the user chose to proceed with Reading A (§2) and updated `07` to v4.3. Narin has not signed off, and the official NVIDIA rule wording is still to be quoted from the organizer's Submission Requirements §4.

## 1. What was wrong, and what changed

Four problems were found. Three are fixed in code; the fourth is a wording task.

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
| **R5** First bounded live pack | Run `r5-live-20261026-113150-e`: 6 dispatches, $0, all identities resolved, four candidate pairs measured, zero unpublished evidence, one memory save. Three earlier attempts failed and are kept as negative results | PASS |

## 4. Remaining steps (not started)

Step detail, requirements and acceptance tests are in the [implementation plan](08-v4-Implementation-Plan.md). These are the additions from this revision:

| Step | Plan step | Findings | Additions from this revision |
|---|---|---|---|
| **R6** Task planning, grounded critique | Step 9 | F06, F13 | The Planner may propose up to three candidates per feature from the filtered pool (formerly R3b); the controller validates each. Critic independence is reported from the real candidate and Critic labs |
| **R7** Review binding, effective repair | Step 10 | F14, F09 | Repair applies to a feature's own candidate |
| **R8** Memory changes a later run | Step 11 | F07 | Accepted decisions store each feature's candidate set and why |
| **R9** Stage totals, revenue, budget fit | Step 12 | F12, F11 | Totals that include projected-only rows are labeled incomplete or lower-bound |
| **R10** Streamlit workflow | Step 13 | F05 | The form adds modality per feature, including image; results show per-feature candidates labeled executed or projected only |
| **R11** Release rehearsal | Step 14 | F15, F16 | Run `scripts/smoke_live.py` on the final setup; the sponsor explanation states the §2 split and links the R1 and R5 receipts |

## 5. Order and cut line

Submission closes **Tue 27 Oct 2026, 23:45 UTC (6:45 p.m. Chicago)**; today is Mon 26 Oct. R0–R5 are done. Remaining, in order:

| Order | Step | Suggested owner | Before submission? |
|---|---|---|---|
| 0 | Close R0: quote the official NVIDIA rule and get Narin's sign-off on `07` v4.3 | Narin | Yes, first; it is a text task |
| 1 | R11 essentials: sponsor smoke check (`scripts/smoke_live.py`, not run on the current setup), clean clone, video, deck, sponsor explanation | Narin, Meena | Yes |
| 2 | R10 UI | Shrie | As far as possible |
| 3 | R9 totals and revenue | Narin | If time allows |
| 4 | R6, R7, R8 | Team | Only if time remains; otherwise list as next steps in the deck |

Describe anything past the cut line truthfully as not implemented. Do not mark it done because the suite is green.

## 6. Live run settings

Optional, passed on the command line or in `.env` (never committed); documented in `.env.example`:

| Setting | Why |
|---|---|
| `METERLESS_NO_THINKING_ROLES` (default `Planner`) | A role whose thinking exhausts the 1,024-token cap needs it; the R5 run used `Planner,Critic` |
| `METERLESS_NO_THINKING_MODELS` | A route that returns `empty_response` with thinking on (Lightning did) |
| `METERLESS_REQUEST_TIMEOUT_S` (default 60) | Ultra occasionally exceeds 60 s |
| `SOURCE_INGEST_URL` / `SOURCE_INGEST_TOKEN` | Evidence publisher; without it a run ends `partial` with evidence in the outbox |
| `METERLESS_OPEN_MODEL` | Optional founder override of the open-source candidate |

## 7. Decisions kept from the original review

- Per-feature, per-stage operating tables with a separate secondary build panel; measured tokens come from API usage, with reasoning counted inside completion tokens and not billed twice; Decimal arithmetic.
- Deterministic critical checks plus human review decide quality. The Critic only flags; verdict fields are ignored.
- All inference goes through Nightshift with no direct-provider fallback; `meterless/auto` is never a candidate.
- Sample outputs are input-dependent, labeled `SAMPLE/OFFLINE`, and never replay saved model answers or invent quality scores.
- Self-host break-even, a hosted deployment and the shelved retrospective are not blockers.
- The organizer material allows any coding tool; do not invent or exaggerate Cursor use.
