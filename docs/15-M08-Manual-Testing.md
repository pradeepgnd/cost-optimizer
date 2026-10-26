# M08 incremental Nightshift verification

M08 is **partial** as of October 25, 2026. The selected candidates are Ultra (frontier), Lightning (mid-tier) and Gemma 4 31B Dense free (required open model, replacing Super). Nightshift advertises the exact route `openrouter/google/gemma-4-31b-it:free`; the user's label is not a literal route ID. The earlier `feature/plan-07-impl-meena` Stage 3 record documents real NVIDIA cloud responses for Ultra and Lightning; Gemma still needs a verified completion. This sequence separates the checks that are safe now from the bounded live run. Do not launch a new completion until the read-only gate says `ready_for_bounded_dispatch` and the exact serving provider, tariff and token bounds have been verified for every route the run will use. OpenRouter catalog prices are a separate hypothetical serving scenario and cannot authorize Nightshift spend.

For the current **Ultra + Lightning only** validation, use the [two-model guide](16-M08-Two-Model-Validation.md). It keeps Gemma in the source bundle and marks the omitted open-model comparison as pending.

## A. Check the adapter and prepare the request (no network or spend)

From the repository root:

```bash
.venv/bin/python -m pytest -q tests/test_nightshift_adapter.py tests/test_dispatch_limits.py tests/test_trace.py tests/test_controller_live_fake.py
.venv/bin/python scripts/prepare_m08_tiny_request.py --output /private/tmp/m08-tiny-request.json
```

The request helper uses synthetic example 3, two text features with pre-supplied rubric checks, `sampling_profile=validation` (one sample per candidate/feature pair), `sample_mode=false`, and a $0.50 ceiling. It chooses a new run ID and refuses to overwrite an existing file. Preparing it makes no model or source request.

## B. Check live sources and dispatch eligibility (no completion)

Start the registered LocalStack/Zetaris source setup from [M05–M06](12-M05-M06-Manual-Testing.md), then run:

```bash
ZETARIS_BINDINGS_FILE=data/localstack/openrouter/bindings-lightning-mid-gemma-open.json .venv/bin/python scripts/smoke_live.py --output-dir /private/tmp/m08-smoke-no-spend
.venv/bin/python scripts/check_m08_gate.py --bindings data/localstack/openrouter/bindings-lightning-mid-gemma-open.json --output /private/tmp/m08-gate.json
```

Use fresh output paths if repeating. The smoke script's default allowance is zero, so three completions show `SKIP` and its exit code is 1 even when discovery succeeds. The current zero-spend smoke passed Zetaris `SELECT 1`, three model reads, Nightshift discovery of 112 routes and H-MEM, with three expected completion skips. The current registered bundle `d85a2e103d87ba5069bf26e3` passed a typed Zetaris read of all three candidate IDs. A read-only gate found all three advertised and registered, but every model row has an unknown execution source and no dispatch policy. The registered bundle mapping is `discovery_observed`; the reusable route template is `planned`. The gate also checks that bindings match the current selected candidate map. The configured Ultra Critic is accepted with an explicit shared-candidate/lab disclosure; Gemma is the required open candidate and still needs a verified response. The saved report lists these facts without printing secrets.

## C. Complete the missing evidence before paid work

For Ultra, Lightning, Gemma and the selected Planner/Critic route, establish the current Nightshift serving endpoint/provider and resolved model variant. The prior branch records Ultra and Lightning as NVIDIA cloud but does not contain raw receipt JSON or applicable tariffs. Obtain a dated official billing source and the exact input/output rates or documented free entitlement, rate limits and fallback rules, cache/context/batch/request fees if applicable, token-bound method, and evidence that `max_tokens` includes hidden reasoning. Pin the response/receipt alias mapping when a route ID differs from the returned model. A model advertised by `GET /v1/models` is not proof of that identity or tariff. Meterless states that cloud providers added with your own key bill directly ([Nightshift integration details](https://meterless.ai/)).

Publish verified route-specific profiles through the M05 bundle/registration process, then rerun B with the new bindings. Keep the configured Ultra Critic unless a distinct, validated Critic route is added. NVIDIA Nemotron proof must come from Ultra or Lightning on a working feature; Gemma does not satisfy that sponsor-specific evidence requirement.

Continue only if the report says `ready_for_bounded_dispatch`, every route marked `required_for_run` passes, and `selection_matches_current` is true. The current Ultra Critic shares a candidate; this is permitted with disclosure and needs only the three candidate/Planner route profiles. Confirm the full application prompts fit the verified bounds and the total reserved amount for up to 11 dispatch slots fits $0.50. The preflight's eight-token sample bound alone does not authorize the full CLI pack.

## D. Run bounded live checks after C passes

First run the existing smoke diagnostic with a fresh operation ledger and a small allowance no greater than $0.50; it sends at most one tiny request to each candidate through the durable dispatcher. Inspect its JSON/Markdown reports for resolved model, request ID, prompt/completion/reasoning counts and actual spend. If any response is missing identity/usage or is a different variant, stop and reconcile its correlated receipt before proceeding.

Then start the M06 evidence publisher for the same registered bindings, set `M08_BINDINGS` to that verified bindings file, and run the prepared request with fresh output/database paths:

```bash
ZETARIS_BINDINGS_FILE="$M08_BINDINGS" RUNS_DB=/private/tmp/m08-runs.db HMEM_STORAGE_DIR=/private/tmp/m08-memory .venv/bin/python run.py --input /private/tmp/m08-tiny-request.json --output /private/tmp/m08-pack.json
```

Inspect the pack, trace, operation ledger and Zetaris evidence readback. Expect two text features × three identified candidates × one measured sample, plus bounded Planner/Critic and at most one repair. Record actual dispatch count (at most 11 including two safe retries), request IDs, resolved variants, raw usage, separate reasoning breakdown, source refs, engine revision, spend and unpublished evidence IDs. Pending human review is acceptable at this checkpoint; it is not a final reviewed recommendation. Never replay the same run ID after an unknown charged outcome.
