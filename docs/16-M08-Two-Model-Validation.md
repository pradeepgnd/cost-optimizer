# M08 Ultra + Lightning validation

This temporary validation profile uses only NVIDIA Nemotron Ultra (`frontier`) and Lightning (`mid_tier`) from the registered three-model source bundle. Gemma remains pinned for the later full comparison. The public request accepts `candidate_tiers` only with `sampling_profile: validation`; the pack records the selected tiers and an evidence gap for the omitted open-model comparison.

## Test now without model spend

Run from the repository root. Use fresh output paths and a fresh request every time:

```bash
.venv/bin/python scripts/prepare_m08_tiny_request.py --output /private/tmp/m08-two-model-dry-request.json --candidate-tiers frontier mid_tier --max-spend-usd 0
.venv/bin/python scripts/check_m08_gate.py --bindings data/localstack/openrouter/bindings-lightning-mid-gemma-open.json --request /private/tmp/m08-two-model-dry-request.json --output /private/tmp/m08-two-model-dry-gate.json
.venv/bin/python scripts/check_openrouter_projection.py --input /private/tmp/m08-two-model-dry-request.json --bindings data/localstack/openrouter/bindings-lightning-mid-gemma-open.json --output-dir /private/tmp/m08-two-model-dry-projection
ZETARIS_BINDINGS_FILE=data/localstack/openrouter/bindings-lightning-mid-gemma-open.json RUNS_DB=/private/tmp/m08-two-model-dry-runs.db HMEM_STORAGE_DIR=/private/tmp/m08-two-model-dry-memory LOG_DIR=/private/tmp/m08-two-model-dry-logs .venv/bin/python run.py --input /private/tmp/m08-two-model-dry-request.json --output /private/tmp/m08-two-model-dry-pack.json
```

The gate currently exits 1 with `status: incomplete`: Ultra and Lightning are `required_for_run: true`, Gemma is `false`, and the two required routes lack verified execution tariffs and dispatch policies. The projection should report 16 separate OpenRouter market-reference rows (two models × two features × four stages), zero completions and zero known actual-route monthly costs. The CLI pack should be `partial`, with only Ultra and Lightning selected, four unexecuted feature/model pairs, zero dispatches and zero spend. It reads Zetaris, discovers Nightshift routes and recalls H-MEM; it stops before inference. The $0 ceiling keeps this command no-spend even if billing profiles are added later.

A recorded run with a $0.50 ceiling also stopped before dispatch because the current billing gate is blocked: `/private/tmp/m08-ultra-lightning-two-model-pack.json`; its gate report is `/private/tmp/m08-ultra-lightning-two-model-gate.json`. The no-completion controller projection passed with 16 rows at `data/localstack/openrouter/openrouter-projection-ultra-lightning-two-model/report.json`.

The $0 profile was also exercised: `/private/tmp/m08-ultra-lightning-two-model-zero-pack.json` is `partial`, selects only Ultra and Lightning, has four planned feature/model pairs and 16 separate reference projection rows, and records 0 dispatches and $0 spend.

## Bounded live run after route evidence is verified

For Ultra and Lightning, pin the actual Nightshift serving endpoint/provider, official execution tariff or documented prototype entitlement, response identity, input/output treatment and a cited prompt/output bound including hidden reasoning. Register a new immutable bundle with verified `billing_profile` and `dispatch_policy` records. Generate a **new** request without `--max-spend-usd 0` (the helper defaults to $0.50), then run the gate with `--request`. Continue only when it says `ready_for_bounded_validation`, both required routes pass, and the full application prompts and up to nine reserved dispatch slots fit the ceiling.

Run that fresh request once with new output, run database and memory paths. Expect two features × two candidates × one measured sample, plus bounded Planner, Critic, at most one repair and at most two safe retries. Confirm both resolved model IDs, request/receipt IDs, usage and reasoning counts, spend, trace, and Zetaris evidence write/readback. The result is a scoped two-model validation; Gemma's serving proof and the three-model comparison remain M08 acceptance work. Never replay the same run ID after an unknown charged outcome.
