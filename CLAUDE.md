# CLAUDE.md — project rules for Claude Code

AI SaaS Cost Advisor · Open Agent Hackathon 2026 · Track: The Agent That Can Explain Why
Team: Narin (integration/deployment owner, primary contact), Pradeep, Meena, Isioma, Shrie.
Submission closes 27 Oct 2026, 23:45 UTC (6:45 p.m. Chicago). This repository becomes public before then: write nothing here you would not publish.

## What this project is

An agent that turns a founder's AI SaaS idea into a costed model stack by feature and growth stage. The operating ledger is primary: compare candidate models (frontier, mid-tier and open-source tiers, from any lab, chosen per feature and modality) using measured API usage and deterministic checks plus human review. The build-approach ledger is secondary; the two ledgers are never summed. Unknown evidence stays explicit, and the Critic flags issues rather than grading candidates.

`Planning/07-Realignment-v4.md` (v4.3) is authoritative. Earlier PRD/architecture/plan requirements apply only where not contradicted by `07`. The retrospective, sealed-actuals evaluation and dev-spec tasks T1–T6 are historical/shelved; retain their existing access protections. Active work follows `docs/08-v4-Implementation-Plan.md` (steps and findings) as revised by `docs/17-v4-Revised-Implementation-Steps.md` (17 wins on candidate selection and the NVIDIA requirement), with incremental results in `docs/v4-release-checklist.md`. A plan or green offline suite is not proof of live sponsor readiness.

## Hackathon requirement versus app requirement (decision of 2026-10-26: read this)

Two different things were mixed together, and the code and docs still partly reflect the old mix.

| | Hackathon requirement | App requirement |
|---|---|---|
| NVIDIA | **Planner and Critic** run on Nemotron through Nightshift, with the resolved model identity logged per request. | None. |
| Candidate models | None. | Chosen per feature from what Nightshift offers, filtered by the feature's modality (text, audio, image), from **any lab**. Not hard-coded. |
| Spend safety | None. | Every executed route needs a verified rate source and dispatch policy; unproven candidates are projected only, never run. |

**Original position (kept for the record):** the PRD (`Planning/01-Product-Requirements.md:59`) said "Nemotron acts as the evidence critic through Nightshift", so the NVIDIA objective sat on the Critic.

**How the confusion started:** `Planning/07-Realignment-v4.md` v4.0 (commit `0c2f19b`, 25 Oct) moved Nemotron from the Critic into a candidate slot ("The critic is not Nemotron. Nemotron is now a candidate… NVIDIA award eligibility comes from Nemotron handling a working feature"). Commit `29e97cc` then hard-pinned a Nemotron candidate (`METERLESS_OPEN_MODEL`, the `required` flag in the route map). v4.1 and v4.2 swapped the open slot to Gemma but left the NVIDIA proof on the Ultra and Lightning candidates. `docs/09` Step 5.1 and M08, `.env.example` and the M05 docs inherited this, so a product choice (which models a founder compares) became a sponsor gate, and M05 and M08 kept stalling on billing evidence for candidates that never needed it.

**Decision (2026-10-26, user; `07` v4.3):** candidates are an app concern and are not tied to any lab. The NVIDIA proof is carried by the Planner and Critic. The Critic is independent unless a candidate is also Nemotron; then the trace discloses the shared lab. The official NVIDIA rule wording is still to be quoted from the organizer's Submission Requirements §4; if it requires a Nemotron *candidate*, allow one (do not pin one). Narin has not yet signed off on the `07` edit.

**Status of the code (2026-10-26):** R1 (role routes), R2 (modality fields) and R3a (per-feature, modality-filtered candidates; no pin; `METERLESS_OPEN_MODEL` is an optional override) are implemented. R4 (execute only candidates with a verified rate source and dispatch policy; project the rest without stopping the run; Planner and Critic routes still stop an unproven run) are implemented. R3b (Planner proposes candidates) is not implemented, and no live run has yet executed a derived candidate (R5). Do not add lab-specific candidate logic.

## Map of the code

- `run.py` → the only entry point. JSON in, JSON out. Calls `Controller.run`.
- `app/controller.py` → the brain. Allowlist by run state, call caps, spend reservation, sealed-source rule, Planner/Analyst/Critic sequence.
- `app/contracts.py` → every data structure. Change a field here and every user of it must update; tests catch breakage.
- `app/economics.py` → Decimal arithmetic only. Unknown stays unknown; never coerce to zero.
- `app/adapters/` → the only path to the outside world. `sample.py` (offline, zero network), `live_zetaris.py` (Zetaris), `live_nightshift.py` (Nightshift).
- `app/engines/hmem/` → Meterless H-MEM bridge. A Python dict is never an acceptable substitute.
- `app/trace.py` → JSONL trace in the organizer's format. Never invent `confidence` or events.
- `tests/` → run before every commit.
- `scripts/check_sample_examples.py` → repeatable offline CLI check of all three examples, with fresh databases and retained packs/traces. It disables dotenv loading and blocks Python sockets; real engine offline behavior is verified separately in M07.

## Non-negotiable rules

1. Run `python -m pytest -q` before every commit. Do not commit on red.
2. Never edit, create or print `.env`. Secrets live only there. `.env.example` holds placeholders only.
3. Never use `--force`, `-f` on push, `reset --hard`, `rm -rf`, or rewrite pushed history. Ask the user instead.
4. Never commit the founder's real case-study figures. `data/sample/retrospective_actuals_SYNTHETIC.json` is a synthetic analogue and must stay synthetic. Real actuals live outside this repository.
5. Sealed-source rule: `retrospective_actuals` and holdout task cases are unreadable before run state `frozen`. Never weaken the allowlist in `controller.py` to make a test pass.
6. **No outcome-targeted rules.** The builders know how the case study turned out. Do not add Planner, Critic or policy logic that targets a specific known outcome of the case study. Agent behaviour must come from general rules or live model reasoning, and any general checklist must be justified independently of the case.
7. Never write a sentence claiming the tool "saved" or "would have saved" a dollar amount. Report agreement with history only.
8. All inference goes through Nightshift. No direct provider calls, no fallback to a provider SDK.
9. Sample mode must make zero network calls and must label every output `SAMPLE/OFFLINE`. Sample outputs must never be read back as answers (`output_examples/` is write-only for the runtime).
10. Keep commits small, with a message saying what changed and why.

## Environment

Use the configured `.venv`. Windows/PowerShell activation: `.\.venv\Scripts\Activate.ps1`; macOS/Linux: `source .venv/bin/activate`. Record the actual Python/runtime versions in test evidence. Repeatable offline check: `python scripts/check_sample_examples.py`; it prints the retained artifact directory. A normal sample run is `$env:SAMPLE_MODE="true"; python run.py --input input_examples\example_1.json --output output.json` in PowerShell. Use isolated databases and fresh run IDs when comparing changes; never erase a real run database to make a rerun pass. Regenerate example outputs after product behavior changes.
