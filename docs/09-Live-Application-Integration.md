# Live application integration

The live controller now reads the registered founder brief, approach/model pricing,
and development tasks from Zetaris. H-MEM supplies project-scoped confirmed memory.
Deterministic ranking is labeled `rule_policy`; candidate specifications and the
structured Nemotron critique use Nightshift. No provider fallback exists.

The implementation and deterministic HTTP/S3 integration tests are in place.
The local service check passes with setup fixtures. **Stage 5's full live-evaluation
exit is still pending approved data, cited model rates, sealed-source permissions,
and a recorded paid candidate/critic run.** Test doubles do not prove model quality
or sponsor-backed decision behavior.

## Prerequisites

- Project Python dependencies, including `boto3`, and the Stage 4 Node dependencies.
- The verified local Zetaris/LocalStack Docker stack, bucket and registered tables.
- Nightshift running with the privately configured Runtime token and discovered
  candidate/critic routes. NVIDIA credentials remain inside Nightshift.
- Private configuration for `ZETARIS_REST_URL`, `ZETARIS_ORG_ID`, `ZETARIS_API_KEY`,
  `METERLESS_BASE_URL`, `METERLESS_RUNTIME_TOKEN`, `METERLESS_CANDIDATE_MODELS`,
  and `METERLESS_CRITIC_MODEL`.

Defaults match the current installation: ordinary namespace `oah_localstack`,
sealed namespace `oah_localstack_sealed`. Override these using `ZETARIS_SOURCE`
and `ZETARIS_SEALED_SOURCE`. Evidence ingestion currently supports the verified
LocalStack topology only; another namespace requires a separately verified writer.
The two namespaces must differ. Namespace separation does not enforce server permissions.

## Repeat the local integration check

From the project root:

```bash
.venv/bin/python scripts/check_live_application_integration.py --output docs/stage5_integration_check.json
```

This reads ordinary registered records, discovers Nightshift routes, uses temporary
real H-MEM storage, proves sealed reads are denied before adapter dispatch, and
proves an unapproved evaluation stops. It makes **zero inference calls** and never
queries holdout or retrospective contents.

To also verify evidence ingestion and append/readback:

```bash
.venv/bin/python scripts/check_live_application_integration.py --write-evidence --output docs/stage5_integration_check.json
```

This writes two explicitly synthetic setup records into one new S3 JSON array and
registers one dedicated Zetaris evidence table. It preserves existing evidence.
Expected: `status: passed`, all nine checks true, `inference_calls: 0`, and
`sealed_content_queried: false`. Without `--write-evidence`, seven checks run.
The [observed report](stage5_integration_check.json) records the live service check;
its trace path is local and excluded from Git.

## Run the application

```bash
.venv/bin/python run.py --input input_examples/live_application.json --output /tmp/live-application-preview.json
```

This input explicitly selects live mode and leaves evaluation unapproved. Expected:
`needs_input`, zero inference spend, and Zetaris source references in the pack.
Give each subsequent run a new `run_id`; duplicate IDs are refused before dispatch.

In live mode, `brief_id` selects the authoritative Zetaris brief and `brief_version`
must match it. Inline descriptive fields satisfy the shared input contract but do
not replace registered data. Update/register approved founder changes in Zetaris
before the next live run. Sample mode continues to use the inline brief.

After the data requirements below are satisfied, make a private copy of the input,
set a new `run_id`, set `evaluation_approved: true`, and set `max_spend_usd` to the
founder's authorized evaluation cap. The current fixtures deliberately return
`needs_input` before inference, even when that flag is true.

## Approved data contract

Ordinary tables are `founder_briefs`, `pricing_snapshots_approaches`,
`pricing_snapshots_models`, and `dev_task_cases`. The sealed task table is
`dev_task_cases_holdout`. Their registered S3 objects contain JSON arrays, with
one envelope per validated record:

```json
{
  "record_id": "the-contract-identity",
  "record_type": "founder_brief, approach, model, or task",
  "source_version": "a-stable-version",
  "evidence_status": "verified",
  "setup_fixture": false,
  "approved_for_evaluation": true,
  "brief_id": "the-contract-identity",
  "payload_json": "a JSON-encoded FounderBrief"
}
```

Use `approach_id`, `model_id`, or `task_id` instead of `brief_id` for the respective
contract. Task envelopes also contain `split`. Envelope IDs must match payload IDs;
payload splits must match the requested split. Missing/duplicate identities,
versions, malformed rows and oversized result sets are rejected.

`approved_for_evaluation` records an actual human approval; changing the flag on
placeholder data is not approval. An approved brief must include the matching
`project_id`. Keep reconstructed/assumed evidence statuses accurate. Approve three
development and three disjoint holdout tasks and freeze their rubrics before evaluation.

Model profiles must use the exact configured Nightshift IDs. Each requires one
input-token and one output-token rate, with unit `1M tokens` or `1000000 tokens`,
a known nonnegative USD amount, verified rate/source statuses, an HTTPS citation,
and `verified_at`. This applies to the critic too. The existing `sample/model-a`
and `sample/model-b` rates do not price the configured NVIDIA routes.
Unknown or unverified prices block inference; no zero-price assumption is made.

## Bounded execution and evidence

1. Guard and retrieve the brief/pricing; recall confirmed memory; calculate separate
   founder build/operating ledgers and rank eligible approaches with a rule policy.
2. Check evaluation approval, dataset approval, exact model discovery and rates.
3. Generate development specifications for two configurations on the same three tasks.
4. Request one structured Nemotron critique containing actual development outputs,
   task/source references and a permitted action. Invalid JSON, invented references,
   founder-constraint edits and sealed-source requests are rejected.
5. Accept no change, or make at most one evidence-linked revision of one configuration.
   A permitted pricing re-query updates the revision's actual pricing context.
   Rerun development cases for that configuration only. Live failures are observed;
   the deliberately missing-context stress case exists only in sample mode.
6. Persist configuration snapshots and a digest before reading holdout. Evaluate both
   frozen configurations on the same three holdout tasks. No holdout feedback goes
   to the critic or a repair. Failed quality gates cause abstention.

Gates check nonempty required sections, critical-failure markers and citations to
the selected approach/model records. They are specification proxies; semantic
correctness, working software and human review are not proved by these gates.

Each candidate output, critique and freeze artifact is ingested through S3 and read
back through Zetaris. One JSON array/table is created per run; optimistic conditional
S3 writes prevent accidental overwrites. This uses the supported file-store route
instead of assuming that a registered S3 source supports SQL inserts. S3 ingestion
uses [Boto3 PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html).

Evaluation inference accounting is separate from both founder ledgers. Every call
reserves a conservative input/output bound, then settles reported token usage at
verified rates. A read timeout or missing usage leaves `spend_usd: null` and an
outstanding reservation; it never silently reports zero. Only connection failures
before delivery retry, with at most two retries globally. Candidate generations are
capped at 23. SQLite records reservations; duplicate run IDs cannot restart paid work.
Calls use a 1,024-output-token cap and disabled thinking. Unknown/mismatched routes,
truncated responses and Runtime review requirements stop the run.

## Retrospective comparison: separate, after freeze

The investigation never fetches actuals. Use either a controlled private export:

```bash
.venv/bin/python scripts/compare_retrospective.py --pack result.json --actuals /private/path/actuals.json
```

Or restricted Zetaris retrieval:

```bash
.venv/bin/python scripts/compare_retrospective.py --pack result.json --zetaris
```

The pack must be `frozen` or `complete` before a live adapter is constructed. Actuals
must have the same `project_id`. The private `retrospective_actuals` table requires
`project_id`, `record_id`, `source_version`, `evidence_status`, `payload_json`, and
`consented_for_retrospective: true`. Use an appropriately restricted credential in
the post-freeze process. The private live source has not been supplied/tested.
Controlled exports need the same project identity and consent outside the public repo.

The synthetic retrospective fixture now shares the example pack's project identifier;
its contents remain explicitly synthetic. Human relevance judgments still use
`--reviewed`. This is N=1 agreement with history and never a savings claim.

## Automated verification

```bash
.venv/bin/python -m pytest -q
```

`tests/test_live_workflow.py` runs the actual live HTTP adapters and controller
against deterministic HTTP/S3 doubles and real temporary H-MEM. It covers no repair,
observed-failure repair, pricing re-query, malformed critique, sealed denial,
usage/cost accounting, retry limits, missing rates/sources, duplicate runs, failed
evidence readback, freeze/holdout and abstention. These tests make no model calls.
