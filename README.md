# LLM Cost Intelligence — a decision agent for founders choosing an AI build approach

**Open Agent Hackathon 2026 · Track: The Agent That Can Explain Why**

An agent that helps a founder choose which AI-assisted development approach and model configuration to commit to *before* building, by joining the founder's constraints, cited pricing, and executed task evidence into one sourced, cost-modeled recommendation with explicit evidence gaps.

Evaluation sandbox: a retrospective case study of the founder's own venture (built on an AI app-builder platform, >$15k in credits). The agent sees only a reconstructed pre-build brief; actual spend and rework are sealed until the recommendation is frozen, then compared. No artifact states a saved amount as a result. Design: `docs/06-Retrospective-Case-Study-Design.md`.

> Status (25 Oct UTC): the live application path is implemented and local integration checks pass, including project-record reads and S3 evidence ingestion/readback through Zetaris. Sample mode runs end-to-end with real H-MEM. The full paid live evaluation remains pending approved founder/tasks, cited prices for the configured NVIDIA routes, and sealed-source permissions. Current checklist: [Plan 7](Planning/07-Setup-and-Implementation-Execution-Plan.md).

## Quick start (offline runtime, no credentials)

Requires Python and Node 20.11+. Dependency installation needs network access;
sample execution uses the real H-MEM reference locally and makes no network calls.

```bash
git clone <repo> && cd <repo>
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm ci --ignore-scripts --prefix app/engines/hmem
SAMPLE_MODE=true python run.py --input input_examples/example_1.json --output result.json
cat logs/trace-example-1.jsonl
python -m pytest -q
```

Sample mode runs the same controller, contracts, cost engine and report builder with rule-based Planner/Analyst/Critic policies and bundled data. It makes zero network calls, never replays saved model answers, and labels every output `SAMPLE/OFFLINE`. It is reproducibility for judges, not sponsor proof.

H-MEM setup and scope: [engine README](app/engines/hmem/README.md). Repeat its standalone check with `python scripts/check_hmem.py --output docs/hmem_engine_check.json`. Sample and live memory have separate Git-ignored stores. Only explicit verified constraints become confirmed memories; a newer confirmed value supersedes the old one without deleting its audit history.

## Live mode

Requires the local Zetaris/LocalStack Docker services, Meterless Nightshift, Python dependencies and the Stage 4 Node setup. Privately configure the app credentials from the Zetaris/Nightshift consoles; the NVIDIA key stays in Nightshift's Providers tab. See the [live integration guide](docs/09-Live-Application-Integration.md) for the approved-data contract, spending controls and exact prerequisites.

First verify the services without paid inference or sealed reads:

```bash
python scripts/check_live_application_integration.py --write-evidence --output docs/stage5_integration_check.json
python run.py --input input_examples/live_application.json --output /tmp/live-application-preview.json
```

The integration check writes two synthetic evidence records and verifies their Zetaris readback. Omit `--write-evidence` for read-only service checks. The application example explicitly selects live mode with evaluation unapproved and returns `needs_input` with zero inference spend. Use a new `run_id` each time. Live mode retrieves the registered brief by ID/version; inline descriptive fields do not replace it. Approved data and verified model prices are required before enabling paid evaluation.

Preflight for the Windows host: `scripts/preflight_windows.ps1` (checks RAM, CPUs, disk, WSL2, Docker allocation, ports; with `-ZetarisUrl`/`-NightshiftUrl` also proves `SELECT 1` and `GET /v1/models`).

### Verify Zetaris before the full live run

In the local Zetaris UI, open **Management → API Tokens → New token** and create a key for the app. A human must copy it into private local configuration; the plaintext key is shown only once. Configure `ZETARIS_REST_URL`, `ZETARIS_ORG_ID`, and `ZETARIS_API_KEY` using the installation's actual organization ID. Keep credentials out of chat and Git.

With the project's Python dependencies installed, run:

```bash
python scripts/check_zetaris.py --output docs/zetaris_connection_check.json
```

This command loads existing private configuration and runs `SELECT 1 AS one` through the same Zetaris adapter as the app, without requiring Nightshift or H-MEM. It exits 0 only when the expected row is returned, 2 for missing configuration, and 3 for a connection/query failure. Reports and query traces exclude credentials. It does not create API keys or change `.env`.

Also run `./verify.sh` in the separate `zetaris-platform` installation and obtain 9/9 passes. If the administrator password changed after first start, manually reconcile that installation's saved verification password with the working account; changing the file does not reset an existing account. See [the setup verification report](docs/07-Zetaris-Setup-Verification.md) for observed local checks and remaining work.

### Local S3 with LocalStack

The [LocalStack setup runbook](docs/08-LocalStack-Zetaris-Setup.md) covers the separate Docker service, shared Zetaris network, S3 fixture uploads, source registration, and SQL checks. Run `python scripts/prepare_localstack_data.py` to export the sample records and `python scripts/register_localstack_sources.py` to review the registration SQL. LocalStack requires a user-supplied account activation token before startup. All six local storage setup steps pass; [the report](docs/localstack_registration_check.json) records verified fixture row counts and query IDs. Live record mapping and evidence ingestion are implemented; prices and case-study data remain unapproved fixtures.

## Interface

`run.py` is JSON in / JSON out. Input: `RunRequest` (see `app/contracts.py`): brief, `evaluation_approved`, `max_spend_usd`. Output: `DecisionPack` with `status ∈ {complete, partial, needs_input, failed}` or a structured `RunError`. Exit codes: 0 valid result · 2 invalid input · 3 setup incomplete · 4 operational/duplicate. Trace: `logs/trace-<run_id>.jsonl` (organizer format, `model` per request, no invented confidence) plus readable `[INFO]` lines on stderr and one `final_result` JSON line on stdout.

## Architecture

```
Founder brief ─► Controller (allowlist by state, call caps, spend reservation, SQLite checkpoints)
                   ├─ Planner  (rule policy) ranks 2 eligible configurations
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
| NVIDIA Nemotron | Structured evidence critic through Nightshift; validated no-change/repair/abstention paths | Controller/HTTP tests pass; standalone route passed Stage 3; full paid critique workflow pending approved data/rates |
| Cursor | (to be stated truthfully by the team) | — |

## Build status

| Component | State |
|---|---|
| Contracts, Decimal economics (two ledgers), controller, trace, CLI, sample adapters, tests | 81 Python tests pass, no skips; real H-MEM and live-adapter HTTP/S3 integration tests; no live model calls in tests |
| Zetaris live adapter | Fixed, bounded project mappings implemented; local ordinary reads and synthetic evidence ingest/append/readback pass |
| LocalStack S3 fixture sources | Six tables registered; ordinary row counts and exact probe row verified through Zetaris; holdout contents unqueried |
| Nightshift live adapter | Exact discovery guard, output cap, receipt/usage capture and structured requests implemented; paid agent workflow pending approved data/rates |
| H-MEM Node bridge | Pinned official reference, offline self-test, persistence/isolation/supersession and ranking integration pass; 10 reference tests and 13 conformance checks pass |
| Streamlit UI | pending (W07) |
| Pricing snapshots | placeholders marked unverified; replace with dated citations (W04) |
| Retrospective comparison script | Implemented: post-freeze project matching, controlled export or restricted Zetaris retrieval, human cause-class review; private live actuals pending |

## Limitations

Economics are modeled estimates from entered assumptions and cited rates, not financial advice. Approach-level alternatives are compared on rates, not executed. The case study is N=1 and retrospective; metrics are agreement with history, never savings. Small samples throughout. The risk cause-class taxonomy was written by the team after the case-study incidents were known; matches are reviewed by a human for relevance.

## Pre-existing components

Project-specific code and data were created on or after 23 October 2026. The H-MEM integration vendors the existing [Meterless reference](https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd/engines/hmem/reference) and conformance suite under Apache-2.0; source hashes and revision are in `app/engines/hmem/UPSTREAM.json`. It uses the reference's deterministic hash embedder and JSON persistence. The case-study subject is the founder's existing venture, used as input data, not as product code.
