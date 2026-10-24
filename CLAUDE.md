# CLAUDE.md — project rules for Claude Code

LLM Cost Intelligence · Open Agent Hackathon 2026 · Track: The Agent That Can Explain Why
Team: Narin (integration/deployment owner, primary contact), Pradeep, Meena, Isioma, Shrie.
Submission closes 27 Oct 2026, 23:45 UTC (6:45 p.m. Chicago). This repository becomes public before then: write nothing here you would not publish.

## What this project is

A decision agent that helps a founder choose an AI-assisted development approach and model configuration before building. It joins the founder's brief, cited pricing and executed task evidence into a sourced recommendation with two cost ledgers (build-phase and operating, never summed) and an explicit evidence-gaps list. Design documents: `Planning/` (PRD, architecture, implementation plan, `06-Retrospective-Case-Study-Design.md`).

## Map of the code

- `run.py` → the only entry point. JSON in, JSON out. Calls `Controller.run`.
- `app/controller.py` → the brain. Allowlist by run state, call caps, spend reservation, sealed-source rule, Planner/Analyst/Critic sequence.
- `app/contracts.py` → every data structure. Change a field here and every user of it must update; tests catch breakage.
- `app/economics.py` → Decimal arithmetic only. Unknown stays unknown; never coerce to zero.
- `app/adapters/` → the only path to the outside world. `sample.py` (offline, zero network), `live.py` (Zetaris, Nightshift).
- `app/engines/hmem/` → Meterless H-MEM bridge. A Python dict is never an acceptable substitute.
- `app/trace.py` → JSONL trace in the organizer's format. Never invent `confidence` or events.
- `tests/` → run before every commit.

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

Windows host, PowerShell, Python 3.13 venv at `.venv`. Activate with `.\.venv\Scripts\Activate.ps1`. Sample run: `$env:SAMPLE_MODE="true"; python run.py --input input_examples\example_1.json --output output.json`. Regenerate example outputs after any behaviour change.
