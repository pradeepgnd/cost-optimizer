# M07 manual verification — real H-MEM

Run these checks from the repository root. They use the vendored, pinned Meterless H-MEM reference. No Zetaris, Nightshift, Nemotron, credentials or paid calls are needed. Node 20+ and the project Python virtual environment are required.

## 1. Install and identify the reference

```bash
cd app/engines/hmem/reference
npm ci
npm test
./node_modules/.bin/tsx ../conformance/runner.ts
cd ../../../..
cat app/engines/hmem/PINNED_REVISION
```

Expected: `npm test` reports 10 passing tests; conformance reports 13/13 PASS; the revision is `1742dec56a66e58eef9dda2d2b865823758ca8cd`. The source, lockfile, conformance vectors and Apache 2.0 licence are local. `npm ci` may report advisories for the pinned development dependencies; do not run an automatic dependency upgrade without rechecking the pinned reference.

## 2. Prove the bridge offline

```bash
NODE_OPTIONS="--require=$(pwd)/scripts/hmem_network_guard.cjs" node app/engines/hmem/bridge.mjs --selftest
.venv/bin/python -m pytest -q -rs tests/test_hmem_engine.py tests/test_sample_memory.py
```

Expected: one JSON line with `status: ok` and the pinned `engine_revision`; 5 tests pass with no skips. The Node guard throws if the engine attempts a network call. The real-engine test saves a confirmed constraint, starts a second Python process, recalls its ID and text, proves another project cannot retrieve it, checks the audit, and rejects a path-escaping project ID.

## 3. Inspect your own save, recall and audit

Use a fresh local store so this manual record does not mix with application data:

```bash
M07_STORAGE=$(mktemp -d)
HMEM_STORAGE_DIR="$M07_STORAGE" .venv/bin/python -c 'from app.engines.hmem.bridge import HmemBridge; print(HmemBridge().remember_confirmed("manual-M07-A", {"kind":"confirmed_constraint","text":"monthly budget 300 USD"}))'
HMEM_STORAGE_DIR="$M07_STORAGE" .venv/bin/python -c 'from app.engines.hmem.bridge import HmemBridge; print(HmemBridge().recall("manual-M07-A", {"kind":"confirmed_constraint"}))'
HMEM_STORAGE_DIR="$M07_STORAGE" .venv/bin/python -c 'from app.engines.hmem.bridge import HmemBridge; print(HmemBridge().recall("manual-M07-B", {"kind":"confirmed_constraint"}))'
HMEM_STORAGE_DIR="$M07_STORAGE" .venv/bin/python -c 'from app.engines.hmem.bridge import HmemBridge; print(HmemBridge().audit("manual-M07-A"))'
```

Expected: the first and second commands share a memory ID and text; project B returns empty `memory_ids` and `context`; A's audit contains `create` and `read`. Each Python command creates a separate Node process. The store contains a separate hashed directory per project. Keep or remove the temporary directory yourself after inspection.

## 4. Check the complete sample workflow

```bash
.venv/bin/python scripts/check_sample_examples.py
.venv/bin/python -m pytest -q -rs tests/test_controller_sample.py tests/test_check_sample_examples.py
```

Expected: examples 1, 2 and 3 all report PASS; sample memory delegates to the actual bridge; Python and Node network operations are blocked; output stays labeled `SAMPLE/OFFLINE` with zero model dispatches and `sponsor_integration: not_verified`. Inspect the printed manifest path to find the retained sample packs and traces. A missing or broken bridge is reported as unavailable rather than silently replaced by a dictionary.

M07 confirms the local reference integration. The upstream JSON store is a deterministic reference with file persistence, not a concurrent production database. M11 will test whether explicitly accepted memory changes a later application decision. M08 will test the live sponsor path.
