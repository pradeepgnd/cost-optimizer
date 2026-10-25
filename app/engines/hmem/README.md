# H-MEM integration

The bridge runs the unchanged official Meterless H-MEM reference at revision
`1742dec56a66e58eef9dda2d2b865823758ca8cd`. `PINNED_REVISION` and `UPSTREAM.json`
record the revision and SHA-256 of every vendored reference/conformance file.
The bridge verifies those hashes before loading the engine. The Apache-2.0
license and upstream implementation instructions are included here.

## Install and verify

Requires Node 20.11+ and the project's Python dependencies. From the project root:

```bash
npm ci --ignore-scripts --prefix app/engines/hmem
node app/engines/hmem/bridge.mjs --selftest
npm test --prefix app/engines/hmem
npm run conformance --prefix app/engines/hmem
.venv/bin/python -m pytest -q tests/test_hmem_engine.py tests/test_memory_constraints.py
.venv/bin/python scripts/check_hmem.py --output docs/hmem_engine_check.json
```

Use `python` instead of `.venv/bin/python` with an activated environment. `npm ci`
downloads locked dependencies during setup. All subsequent memory operations and
checks work offline. No NVIDIA key, Nightshift, Zetaris, or local model is needed.

## What runs

`bridge.py` sends one JSON object to `node bridge.mjs` over stdin. Each operation
starts a fresh process. The Node bridge calls the sponsor's `HMEM.add()`,
`query()`, reinjection formatter, persistent store and append-only trust ledger.
No model provider is imported. Human-readable errors use stderr; stdout is JSON.

```json
{
  "operation": "remember_confirmed",
  "project_scope": "project-A",
  "payload": {
    "kind": "confirmed_constraint",
    "field": "devops_capacity",
    "value": "none",
    "source": "founder confirmation"
  },
  "storage": "/absolute/private/memory-directory"
}
```

Operations are `remember_confirmed`, `recall`, and `audit`. Responses contain
`status`, `engine_revision`, project-scoped `memory_ids`, structured `records`,
reinjected `context`, and `audit_refs`. Audit also returns the last 100 ledger
references/actions. Scope names allow letters, numbers, `.`, `_`, and `-`, with
an alphanumeric first character and a 128-character maximum. Traversal and
symlinked project stores are rejected. A per-project filesystem lock serializes
independent writers; the Python wrapper also serializes its own threads.

Live storage defaults to `storage/live`; sample storage defaults to
`storage/sample`. Both are ignored by Git. Override with private
`HMEM_STORAGE_DIR` or `HMEM_SAMPLE_STORAGE_DIR`, respectively. Keep memory outside
ephemeral containers or mount a persistent volume. If an interrupted process
leaves `.writer-lock`, confirm no writer is running before manually removing that
project's lock directory.

## How memory affects the app

The controller recalls structured confirmed constraints before calculating
eligibility and ranking. Missing fields can use remembered values; explicitly
supplied current values win. Only explicitly supplied fields marked `verified`
are captured as new founder confirmations. Reconstructed/assumed values and
generated recommendations are not silently promoted to confirmed memory.

Updating a confirmed field adds a new reference record and audit entries, marks
the older record `supersededBy`, and retains the history. Superseded records do
not enter the active constraint context. An accepted finding requires explicit
`confirmed: true` plus a source. The current app does not automatically accept its
own findings. Missing or failed memory returns a clear partial result before
evaluation.

Exact-kind constraint recall calls the reference ranker with threshold zero so
lexical similarity cannot hide a hard constraint. It returns all matching active
records, up to 100. Ordinary text recall uses the reference's default threshold.

## Scope and limitations

This is the sponsor's deterministic reference, not a production semantic-memory
service. Its embedder hashes text and its persistence uses JSON/JSONL. The product
uses direct confirmed capture, enrichment, retrieval/reinjection, supersession,
and audit. Dreaming, sleep and model-based mining are not invoked by the app.
The included upstream conformance suite also tests those reference capabilities;
passing it does not claim the product uses them.

Source: [Meterless H-MEM reference](https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd/engines/hmem/reference).
The [agentathon starter](https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd/templates/agentathon-starter)
demonstrates the same memory spine; its optional direct-provider example was not copied.
