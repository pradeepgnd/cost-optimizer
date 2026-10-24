# H-MEM engine integration (W03, Pradeep)

The Meterless Engine requirement is satisfied only by the sponsor's reference running for real. This folder holds the Python wrapper (`bridge.py`, done) and the Node side (`bridge.mjs`, **to do**).

## To do, in order

1. Clone the Meterless repository, check out the `templates/agentathon-starter` path, and record the commit hash in `PINNED_REVISION`.
2. Vendor or `npm install` the reference under `reference/` so a fresh clone needs only `npm ci` in this folder. Do not copy the starter's optional direct-model provider example; our inference goes through Nightshift.
3. Write `bridge.mjs`: read one JSON object from stdin `{operation, project_scope, payload, storage}`, call the reference's memory acquisition/retrieval/audit functions, write one JSON object to stdout `{status, engine_revision, memory_ids, context, audit_refs}`. Per-project storage under `storage/<project_scope>/`. Support `--selftest` (remember → recall → audit round trip on a temp scope, exit 0, print `{"status":"ok"}`); it must work offline.
4. `tests/test_hmem_engine.py` (already stubbed) must pass: save a confirmed constraint, start a new process, recall it with its memory ID, confirm a different project cannot see it. This is the test the README points judges to.
5. Keep human logs on stderr; stdout is JSON only.

Dreaming/sleep operations are out of scope. Disclose exactly which services are used in the sponsor explanation.
