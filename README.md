# LLM Cost Intelligence — a decision agent for founders choosing an AI build approach

**Open Agent Hackathon 2026 · Track: The Agent That Can Explain Why**

An agent that helps a founder choose which AI-assisted development approach and model configuration to commit to *before* building, by joining the founder's constraints, cited pricing, and executed task evidence into one sourced, cost-modeled recommendation with explicit evidence gaps.

Evaluation sandbox: a retrospective case study of the founder's own venture (built on an AI app-builder platform, >$15k in credits). The agent sees only a reconstructed pre-build brief; actual spend and rework are sealed until the recommendation is frozen, then compared. No artifact states a saved amount as a result. Design: `docs/06-Retrospective-Case-Study-Design.md`.

> Status (24 Oct, morning): scaffold complete; sample mode runs end-to-end; live adapters are written against the setup guide and **unverified** until the sponsor runtimes are installed. See "Build status" below.

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

Sample mode runs the same controller, contracts, cost engine and report builder with rule-based Planner/Analyst/Critic policies and bundled data. It makes zero network calls, never replays saved model answers, and labels every output `SAMPLE/OFFLINE`. It is reproducibility for judges, not sponsor proof.

## Live mode

Requires Zetaris (Docker Desktop / WSL2) and Meterless Nightshift running locally; see the Participant Setup Guide. Fill `.env` from your Zetaris and Nightshift consoles (the NVIDIA key goes in Nightshift's Providers tab, never here), then:

```bash
python run.py --input input_examples/example_1.json --output result.json
```

Preflight for the Windows host: `scripts/preflight_windows.ps1` (checks RAM, CPUs, disk, WSL2, Docker allocation, ports; with `-ZetarisUrl`/`-NightshiftUrl` also proves `SELECT 1` and `GET /v1/models`).

## Interface

`run.py` is JSON in / JSON out. Input: `RunRequest` (see `app/contracts.py`): brief, `evaluation_approved`, `max_spend_usd`. Output: `DecisionPack` with `status ∈ {complete, partial, needs_input, failed}` or a structured `RunError`. Exit codes: 0 valid result · 2 invalid input · 3 setup incomplete · 4 operational/duplicate. Trace: `logs/trace-<run_id>.jsonl` (organizer format, `model` per request, no invented confidence) plus readable `[INFO]` lines on stderr and one `final_result` JSON line on stdout.

## Architecture

```
Founder brief ─► Controller (allowlist by state, call caps, spend reservation, SQLite checkpoints)
                   ├─ Planner  (Nightshift)  proposes 2 configs, picks next action
                   ├─ Analyst  (tools)       Zetaris reads · Decimal cost ledgers · candidate runs
                   ├─ Critic   (Nemotron via Nightshift) challenges evidence → one validated repair
                   ├─ H-MEM    (Meterless)   confirmed constraints survive restart
                   └─ freeze ─► holdout ─► DecisionPack (+ sealed-actuals comparison, separate script)
```

Hard limits per run: 1 planning call, 1 batched critique, ≤1 revision, ≤23 candidate generations, ≤2 transport retries. `retrospective_actuals` and holdout tasks are unreadable before `frozen`; an attempt is logged `denied_sealed`.

## Sponsor technology

| Sponsor | Role in this project | Proof |
|---|---|---|
| Zetaris | Sole data layer: brief, pricing snapshots, task cases, evidence, sealed actuals (S3-backed sources) | `app/adapters/live.py`; trace `zetaris_query` events with query IDs |
| Meterless H-MEM | Stores founder-confirmed constraints and accepted findings across restarts; recalled into the next plan | `app/engines/hmem/`; `tests/test_hmem_engine.py` |
| Meterless Nightshift | Every inference call; requested and resolved model logged | `app/adapters/live.py`; trace `nightshift_request` events |
| NVIDIA Nemotron | Evidence critic; its structured finding drives the one repair; model ID attributable per request | trace `critique` events with `model`; `feature=nemotron_evidence_critic` |
| Cursor | (to be stated truthfully by the team) | — |

## Build status

| Component | State |
|---|---|
| Contracts, Decimal economics (two ledgers), controller, trace, CLI, sample adapters, tests | done, 10 passing |
| Zetaris live adapter | HTTP shape from guide; row mapping pending first real `SELECT 1` (`docs/zetaris_select1_response.json`) |
| Nightshift live adapter | written; untested until runtime token exists |
| H-MEM Node bridge | interface + README; `bridge.mjs` and `PINNED_REVISION` pending (W03) |
| Streamlit UI | pending (W07) |
| Pricing snapshots | placeholders marked unverified; replace with dated citations (W04) |
| Retrospective comparison script | pending; runs only on a frozen pack |

## Limitations

Economics are modeled estimates from entered assumptions and cited rates, not financial advice. Approach-level alternatives are compared on rates, not executed. The case study is N=1 and retrospective; metrics are agreement with history, never savings. Small samples throughout. The risk cause-class taxonomy was written by the team after the case-study incidents were known; matches are reviewed by a human for relevance.

## Pre-existing components

None. All code and data were created on or after 23 October 2026. The case-study subject is the founder's existing venture, used as input data, not as product code.
