# H-MEM reference integration

The unmodified Meterless H-MEM TypeScript reference and conformance suite are vendored from [revision 1742dec](https://github.com/Meterless/Meterless/tree/1742dec56a66e58eef9dda2d2b865823758ca8cd/engines/hmem), recorded in `PINNED_REVISION`. Its Apache 2.0 licence is copied to `LICENSE`. The reference is deterministic, model-free and JSON-file backed; upstream labels it a reference, not a production library.

## Clean-clone setup

Use Node 20 or newer and run from the project root:

```bash
cd app/engines/hmem/reference
npm ci
npm test
./node_modules/.bin/tsx ../conformance/runner.ts
cd ../../../..
.venv/bin/python -m pytest -q -rs tests/test_hmem_engine.py tests/test_sample_memory.py
```

`npm ci` installs the exact development tooling locked in `reference/package-lock.json`; the reference has no runtime provider dependency. The bridge uses local `tsx` only to load the vendored TypeScript and never calls a model. Runtime files live under `HMEM_STORAGE_DIR` or ignored `storage/`. Project IDs are validated and hashed into separate directories. Keep that storage private and backed up if using it beyond a demonstration; the upstream JSON store is not a concurrent production database.

`bridge.mjs` accepts one JSON request on stdin and emits exactly one JSON response on stdout. It calls H-MEM `add`, `query` and `ledger.all` and returns `status`, `engine_revision`, `memory_ids`, structured `context`, and `audit_refs`. `node bridge.mjs --selftest` creates a disposable scope and checks save, new-instance recall, isolation and audit. Errors go to stderr. The Python wrapper enforces a 20-second timeout and verifies revision/response shape. Sample mode delegates to the same bridge. Dreaming and sleep operations are outside M07.

See the M07 entry in the [evidence ledger](../../../docs/v4-release-checklist.md). Step R8 in [docs/17](../../../docs/17-v4-Revised-Implementation-Steps.md) still needs proof that explicitly accepted memory changes a later application decision; current controller behavior does not establish that.
