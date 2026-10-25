# AI SaaS Cost Advisor

**Open Agent Hackathon 2026 · Track: The Agent That Can Explain Why**

An agent that helps solo founders turn an AI SaaS idea into a costed technology plan. It runs the idea's core AI tasks on frontier and open-source models, measures real token usage and quality, and projects how monthly costs evolve from prototype to scale, including when to switch models.

**The problem.** A founder spent over $15,000 building with an AI app-builder, and no tool estimated what the app would cost to build or to run.

## Quick start (no credentials, no network)

```bash
git clone <repo> && cd <repo>
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
SAMPLE_MODE=true python run.py --input input_examples/example_1.json --output result.json
cat logs/trace-example-1.jsonl
python -m pytest -q
```

Sample mode runs the same controller, contracts and cost engine on bundled data. It makes zero network calls and executes no model: tokens are estimated with the 4/3 rule and labeled estimated, no outputs are produced, and rubric checks don't run. It never replays saved model answers and labels every output `SAMPLE/OFFLINE`. It is reproducibility for judges, not sponsor proof.

## Live mode

Requires Zetaris (Docker Desktop / WSL2) and Meterless Nightshift running locally; see the Participant Setup Guide. Fill `.env` from your Zetaris and Nightshift consoles (the NVIDIA key goes in Nightshift's Providers tab, never here), then:

```bash
python run.py --input input_examples/example_1.json --output result.json
```

Preflight for the Windows host: `scripts/preflight_windows.ps1` (checks RAM, CPUs, disk, WSL2, Docker allocation, ports; with `-ZetarisUrl`/`-NightshiftUrl` also proves `SELECT 1` and `GET /v1/models`).

Live smoke test (diagnostic only, reads `.env`): `python scripts/smoke_live.py` checks Zetaris, Nightshift (including one tiny completion per candidate route) and the H-MEM bridge separately. It prints a PASS/FAIL/SKIP table with secrets redacted and saves it to `logs/smoke-<timestamp>.md`.

## Interface

`run.py` is JSON in / JSON out. Input: `RunRequest` (see `app/contracts.py`): brief (idea, target user, 2–5 `ai_features`, `growth_stages`, optional build constraints), `evaluation_approved`, `max_spend_usd`, optional `human_reviews`. Examples: `input_examples/` (two founder ideas, one synthetic; every number labeled assumed). Output: `DecisionPack` with `status ∈ {complete, partial, needs_input, failed}` or a structured `RunError`. Exit codes: 0 valid result · 2 invalid input · 3 setup incomplete · 4 operational/duplicate. Trace: `logs/trace-<run_id>.jsonl` (organizer format, `model` per request, no invented confidence) plus readable `[INFO]` lines on stderr and one `final_result` JSON line on stdout.

## Architecture

v4 (`Planning/07-Realignment-v4.md`). The founder describes an AI SaaS idea and its 2–5 AI features; the agent measures what can be measured and labels the rest.

```
Founder idea + AI features ─► Controller (allowlist by state, call caps, spend reservation, SQLite checkpoints)
  1  Recall     H-MEM (Meterless)         earlier runs and confirmed assumptions for this idea
  2  Retrieve   Analyst ◄─ Zetaris         dated prices (input, output, cache, batch, audio, long-context),
                                           intelligence scores, OpenRouter market reference
  3  Select     Controller ◄─ Nightshift   candidate shortlist: one Nightshift route per tier (GET /v1/models,
                                           before any paid call); open-source is always the Nemotron route;
                                           Critic route must not be a candidate's route
  4  Estimate   Analyst                    4/3 rule per feature × candidate, labeled estimated
     ── approval gate (evaluation_approved, max_spend_usd) ──
  5  Plan       Planner ◄─ Nightshift      domain risks only, labeled model-generated, not advice
  6  Execute    Analyst ◄─ Nightshift      each feature's example input on each candidate, 2 samples (1 if the cap needs it);
                                           measured tokens from API usage fields (output includes reasoning)
  7  Check      rubric checks              deterministic pass/fail (max_words, required_json_fields,
                                           forbidden_terms, regex) + human review; no model grades
  8  Critique   Critic ◄─ Nightshift       flags only: unsupported claims, token gaps, over-long output;
                                           proposes one action; controller validates it
  9  Repair     Analyst ◄─ Nightshift      at most one: re-run one feature × model with an output cap
 10  Project    economics (Decimal)        stage cost tables, levers, switch points, model stack
     └─ frozen ─► complete ─► DecisionPack ─► H-MEM (accepted decisions)
```

**Candidate shortlist.** One candidate per tier: frontier, mid-tier and open-source. In live mode only Nightshift routes are eligible; sample mode says the route check needs live mode.

- **Frontier and mid-tier:** the top-ranked eligible model by intelligence score, then OpenRouter usage rank, then snapshot order.
- **Open-source:** always the Nemotron route, from `METERLESS_OPEN_MODEL` or the snapshot row marked `required`, regardless of score. Other open models can appear in the shortlist but never replace it. If the pinned route has no price snapshot or Nightshift doesn't offer it, the run stops for input before any paid call.
- **In the pack:** `candidate_shortlist` lists every snapshot model, with:
  - whether it's a Nightshift route;
  - its intelligence score, with source and date;
  - its market reference, labeled *market reference (OpenRouter, date)*;
  - its price per intelligence point (list price blended 3:1 input:output ÷ score), labeled with source and date;
  - why it was or wasn't selected.
- **Reference data only ranks the shortlist.** Costs come from the price snapshots and pass/fail from rubric checks; scores and market prices never feed stage tables, switch points or the model stack.

**Decision pack.** Two ledgers, never summed:

- **Operating ledger by growth stage** (primary): monthly AI cost per feature, per candidate, at Prototype 50 · Launch 500 · Traction 5,000 · Scale 50,000 active users (editable, labeled assumed). Levers appear as separate lines, applied only when eligible: prompt caching, batch API and output reuse are labeled *projected (production setup)*; the output cap uses a measured re-run; the long-context cliff is a warning. AI cost per use is shown against revenue per use when given; above 100% raises a high-severity risk.
- **Build panel** (secondary): build approaches, expected build cost with an assumed rework multiplier, and checkpoints. A missing build input adds a question; it never stops the run.
- **Model stack** per feature and stage: the cheapest candidate that passes every critical rubric check; a higher-quality one only if it costs less than the switch threshold ($100/month default) more; never one that loses money per use while a qualified alternative doesn't. **Switch points**: the first stage where a cheaper candidate is projected to cost at least the threshold less and passes every critical check.
- Measured versus estimated tokens per feature, evidence gaps, risks, limitations, and the trace.

**Sample mode** runs steps 1–4 and 10 on bundled data with zero network calls: nothing is executed, no outputs exist, rubric checks don't run, switch points stay pending, the model stack says *requires live run*, and domain-risk review is reported as requiring live mode. Audio features are never sent to Nightshift in either mode; audio is priced from per-second conversions, labeled estimated.

Hard limits per run: 1 Planner call, 1 Critic call, ≤1 repair, ≤30 candidate generations, ≤2 transport retries, `max_spend_usd` reserved before each call and reconciled to measured cost. `retrospective_actuals` and holdout tasks remain unreadable before `frozen` (an attempt is logged `denied_sealed`); the v3.4 retrospective that used them is shelved (`scripts/compare_retrospective.py`).

## Sponsor technology

| Sponsor | Role in this project | Proof |
|---|---|---|
| Zetaris | Data layer: price snapshots for every candidate (S3-backed sources) and writeback of measured runs | `app/adapters/live_zetaris.py`; trace `zetaris_query` events with query IDs |
| Meterless H-MEM | The idea's memory: confirmed assumptions recalled at the start of a run; accepted model-stack decisions saved at the end | `app/engines/hmem/`; `tests/test_hmem_engine.py` |
| Meterless Nightshift | The router for every model call: Planner, all three candidates and the Critic; requested and resolved model logged per request | `app/adapters/live_nightshift.py`; trace `nightshift_request` and `run_feature` events |
| NVIDIA Nemotron | The open-source candidate in every comparison, pinned so no higher-scored open model replaces it; its measured cost and deterministic quality checks drive the switch points | `METERLESS_OPEN_MODEL`; trace `select_candidates` (chosen routes) and `run_feature` events (`model` per request) |
| Cursor | Used by Shrie for UI and Zetaris work | — |

No model grades the comparison. The Critic only flags issues and proposes one action, which the controller validates. It never uses a candidate's route when Nightshift offers another; when none is available, the trace and the pack's limitations say so.

## Build status

The offline core is complete, with 100 passing tests: contracts, Decimal economics, the controller loop, rubric checks, trace, CLI and sample adapters. The live Zetaris, Nightshift and H-MEM adapters are in progress as of 25 October.

| Component | State |
|---|---|
| Contracts, economics, controller, rubric checks, trace, CLI, sample adapters | complete; 100 tests pass (9 skipped: the shelved comparison and the H-MEM bridge test) |
| Zetaris live adapter | in progress: HTTP shape from the setup guide; row mapping for prices and evidence writeback pending the first real query |
| Nightshift live adapter | in progress: written; candidate routes not yet pinned; tested only against a scripted fake |
| H-MEM bridge | in progress: Python interface written; Node bridge and pinned engine revision pending |
| Streamlit UI | in progress |
| Pricing snapshots | unverified placeholders; to be replaced with dated, cited snapshots |
| Retrospective comparison script | shelved in v4 |

## Limitations

- Economics are modeled estimates from entered assumptions and the rates in the price snapshots, not financial advice. Small samples throughout; no claim about a model's quality beyond the measured tasks.
- All prices are unverified placeholders until replaced with dated, cited snapshots; so are the intelligence scores and OpenRouter market references in the sample data.
- Audio is priced from per-second conversions, not measured; audio is never sent to a model.
- Prompt caching, batch API and output reuse are projections for a production setup, not measured in our runs.
- The self-host break-even is not shown: it needs a cited throughput figure for the pinned Nemotron variant.
- Founder-impact evidence so far comes only from the founder's own ideas (self-evaluation).
- Build-approach costs are compared on rates; no build was executed on any platform.

## Pre-existing components

None. All code and data were created on or after 23 October 2026.
