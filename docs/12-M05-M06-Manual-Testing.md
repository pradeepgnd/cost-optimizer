# Steps 5–6: incremental implementation and manual tests

Implemented October 25, 2026. No owners are assigned. This guide separates catalog collection, planned route mapping, source registration, typed reads, reference arithmetic and evidence publication. Each stage can be tested without model completions or H-MEM.

The recommended source path is **OpenRouter → collector → immutable S3 objects → Zetaris → application**. Source bundles retain the raw response, normalized catalog, quarantined records, manifest, exact hashes and application records. The publisher emits a release only after checking the registered rows. It never changes a current-version pointer automatically.

Catalog prices remain reference data. OpenRouter documents model-level pricing as the top provider's prices and exposes serving-provider endpoints separately. An applicable Nightshift tariff requires a reviewed route/provider/variant mapping; simply collecting a catalog cannot supply that proof. See [Models API](https://openrouter.ai/docs/guides/overview/models) and [model endpoints](https://openrouter.ai/docs/api/api-reference/endpoints/list-all-endpoints-for-a-model).

## Current-machine quick check

The following bindings were actually registered on this machine:

```text
data/localstack/openrouter/bindings-final.json
```

With the project environment activated and the existing Zetaris/LocalStack containers running:

```text
python scripts/check_zetaris_sources.py --bindings data/localstack/openrouter/bindings-final.json --catalog-id nvidia/nemotron-3.5-lightning --round-trip --storage data/source_examples/localstack.json --run-id manual-source-check-001 --output-dir data/localstack/manual-check-001
```

Expected: `status: pass`, five successful checks, `model_completions: 0`, `execution_billing_verified: false`. The final check covers fixture write/readback, a second append, publisher recreation and a repeated identical write. `report.json`, `reference-scenario.json`, `models.json`, `select-one.json` and a JSONL trace are retained in the output directory.

For a repeat, keep the same `--run-id` and choose a new `--output-dir`, such as `data/localstack/manual-check-002`. The first evidence record's version/hash should remain identical; query IDs and check timestamps may change. Existing output directories are refused.

The bindings and data above are local artifacts, not files available automatically on another machine. Use the full sequence below to rebuild them.

## Preparation

Run commands from the repository root using the configured virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies if needed:

```text
python -m pip install -r requirements.txt
```

Stages 5A and 5B and the registration dry run need no private configuration. Live Zetaris steps use the existing private `ZETARIS_REST_URL`, `ZETARIS_ORG_ID` and `ZETARIS_API_KEY`. Scripts load private dotenv configuration normally; `--no-dotenv` uses exported process settings instead. Do not put credentials in route maps, storage JSON, reports or Git.

The supplied [LocalStack configuration](../data/source_examples/localstack.json) targets bucket `cost-optimizer-data`, prefix `cost-optimizer/v4`, and namespace `cost_optimizer_v4`. Its host endpoint is `127.0.0.1:4566`; its Zetaris-side endpoint is the Docker name `cost-optimizer-localstack:4566`. On another machine, copy this public configuration and adjust the Docker-reachable endpoint. The bucket must exist, and the Zetaris driver must be able to reach it. Existing unrelated sources are never dropped, patched or replaced.

## 5A — Collect and validate locally

First exercise the offline path:

```text
python scripts/collect_sources.py --from-file data/source_examples/openrouter.fixture.json --output-dir data/localstack/manual/catalog
```

Expected: `status: pass`, 3 accepted records, `acquisition: file_import`, and `purpose: catalog_reference_only`. These are synthetic fixture records. Copy the returned `snapshot_dir` into `<CATALOG_DIR>` below; angle-bracket names are placeholders to replace with command output.

```text
python scripts/collect_sources.py --validate <CATALOG_DIR>
```

Expected: validation passes without network access. Inspect `manifest.json`, `catalog.json`, `rejected.json` and `raw/page-001.json` under that directory. Repeating collection with identical input reuses the existing snapshot.

Then collect the actual public catalog:

```text
python scripts/collect_sources.py --output-dir data/localstack/openrouter/catalog
```

Expected: `acquisition: https_api`. Counts can change upstream. The executed check on October 25 retained **467 upstream records, 460 accepted records and 7 quarantined records**. Invalid/unbounded price entries are retained in raw data and listed in `rejected.json`; they are excluded from eligible normalized records, never converted to zero. Pagination errors, duplicates, invalid response shapes and incomplete imports prevent acceptance.

Inspect a selected catalog entry using the returned directory:

```text
python scripts/collect_sources.py --validate <CATALOG_DIR> --search nemotron-3.5-lightning
```

This reports reference prices, supported parameters and retained raw pricing conditions. Prices are normalized from USD/token to USD/million tokens with Decimal arithmetic. Missing prices stay null; explicit zero stays zero. Unknown conditional/auxiliary terms are retained rather than silently treated as supported tariffs.

Negative test: make a copy of a snapshot directory, change a price in its `catalog.json`, and validate the copy. Expect exit 1 and a hash mismatch. The original snapshot must remain valid. Do not modify the accepted snapshot itself.

## 5B — Prepare mapped application records

For the offline fixture snapshot:

```text
python scripts/prepare_source_bundle.py --catalog <CATALOG_DIR> --route-map data/source_examples/routes.fixture.json --brief input_examples/example_3.json --output-dir data/localstack/manual/bundles
```

For the actual catalog snapshot:

```text
python scripts/prepare_source_bundle.py --catalog <CATALOG_DIR> --route-map data/source_examples/routes.catalog-only.json --brief input_examples/example_3.json --output-dir data/localstack/openrouter/bundles
```

Expected: 3 model records, 1 synthetic founder brief, the accepted catalog count, a returned `bundle_dir`, and `execution_tariffs_verified: false`. Use that directory as `<BUNDLE_DIR>`. Inspect `models.json`: catalog reference prices appear under `market`; execution rates remain null and dispatch policies remain absent unless a separate curated `billing_profile` was supplied. No intelligence score is invented. Optional build prices can be supplied with `--approaches <JSON-list>`; omission does not block model reads.

The catalog-only route map is an example for data-path testing, not a quality recommendation or a claim that the routes are configured. Its frontier/mid routes were **not offered by the current runtime**; the Lightning route was advertised. It must remain `mapping_status: planned` until validated against retained discovery. An observed alternative with Ultra, Super, Lightning and a separate Qwen Critic is recorded in the [M05 serving/billing selection](13-M05-Serving-and-Billing-Selection.md) and [routes.nvidia-selected.json](../data/source_examples/routes.nvidia-selected.json). Its four routes were advertised and registered locally, but no execution tariff or actual serving result was verified.

Optional free route verification:

```text
python scripts/discover_source_routes.py --output data/localstack/manual/discovery.json
python scripts/prepare_source_bundle.py --catalog <CATALOG_DIR> --route-map <YOUR_ROUTE_MAP_JSON> --discovery data/localstack/manual/discovery.json --brief input_examples/example_3.json --output-dir data/localstack/manual/observed-bundles
```

Expected: the second command fails if any mapped route was not offered. A successful discovery match proves availability only, not execution identity, applicable billing or quality. The current check retained 75 advertised routes and made zero completions.

Before paid execution, curate real `billing_profile` records with official serving-provider tariffs, cache/batch/context terms, citations/dates and the Step 4 `dispatch_policy`. Include separately used Planner/Critic routes. See [data contracts](../data/README.md). Provider-endpoint enrichment, intelligence-index ingestion, usage-rights review and actual runtime billing-bound verification remain separate work; this implementation does not fabricate them.

## 5C — Publish, register and repeat safely

Preview without contacting storage or Zetaris:

```text
python scripts/register_sources.py --bundle <BUNDLE_DIR> --storage data/source_examples/localstack.json --report data/localstack/manual/registration-plan.json
```

Expected: `mode: dry_run`, `mutations_performed: false`, dedicated table names and expected counts. Review the namespace, bucket, object keys and SQL statements.

Apply that concrete plan:

```text
python scripts/register_sources.py --bundle <BUNDLE_DIR> --storage data/source_examples/localstack.json --apply --bindings-output data/localstack/manual/bindings.json --report data/localstack/manual/registration-result.json
```

Expected: `status: pass`, registration counts matching the bundle, content checks for all rows, `registered: true` in the bindings, and `current_pointer_updated: false`. Raw source files and manifests are published too. Bindings schema **1.1** pins each complete row's SHA-256; a later self-consistent but altered payload or fixture flag is rejected by application reads.

Repeat the same apply command with a new `--report` path. Expected: objects and matching tables are `reused`, with the same snapshot and hashes. A conflicting object, source path or reader configuration fails; the script does not overwrite/drop it. Different source versions get new pinned table names, with one table per dataset/version rather than one per model. No latest-version pointer is silently switched.

AWS option: copy [aws.template.json](../data/source_examples/aws.template.json), set your bucket/region and retain null custom endpoints. The publishing process uses the AWS SDK credential chain; Zetaris must already have suitable source access on its side. **AWS registration/IAM is not verified by the LocalStack result.** Do not put real AWS keys in the public JSON or application runtime. Conditional writes provide create-only publication; content hashes remain the identity contract even when storage returns no VersionId. [S3 PutObject reference](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html)

## 6A and 6B — Typed reads and reference calculation

```text
python scripts/check_zetaris_sources.py --bindings data/localstack/manual/bindings.json --catalog-id <EXACT_CATALOG_ID> --output-dir data/localstack/manual/read-check-001
```

Use `fixture/nemotron` for the offline fixture bundle or `nvidia/nemotron-3.5-lightning` for the recorded real catalog bundle.

Expected: `SELECT 1`, typed model read, founder read and reference arithmetic checks pass. Inspect each source's query ID, snapshot ID, original source URL where supplied, transport reference and payload hash. Original provider citations/statuses are preserved; reading through Zetaris cannot promote an assumed founder input to verified. The model query uses the exact pinned source/version and expected IDs, fetching an extra row to detect overflow; it does not silently truncate the catalog at 50 rows.

`reference-scenario.json` uses explicit synthetic volumes/tokens to verify that a queried real catalog price reaches the deterministic calculator. It states `execution_tariff: false`, `model_execution_performed: false` and `complete_billing_estimate: false`. This is a token-only reference scenario, not a verified Nightshift bill. Actual serving-provider tariff acceptance remains pending.

Optional SQL-editor inspection: obtain the namespace/table from `bindings.json`, then run:

```sql
SELECT record_id, snapshot_id, payload_sha256
FROM <NAMESPACE>.<MODELS_TABLE>
LIMIT 4
```

Expect the 3 selected model IDs and the pinned snapshot. Keep the sealed retrospective sources untouched.

## 6C — Evidence write/readback, append, duplicate and restart

```text
python scripts/check_zetaris_sources.py --bindings data/localstack/manual/bindings.json --catalog-id <EXACT_CATALOG_ID> --round-trip --storage data/source_examples/localstack.json --run-id manual-roundtrip-001 --output-dir data/localstack/manual/roundtrip-001
```

Expected: the additional fixture write/readback check passes. The publisher writes two distinct fixture IDs, repeats the first write, recreates publisher state and confirms that the first record/version remains unchanged. Test evidence is labeled `integration_test_fixture`; its `SourceRef.status` stays `unverified` because it is not a real measured model sample.

Repeat with the same run ID/bindings and a new output directory. Expect the same first-record content hash/version and no duplicate evidence ID. Reusing an ID with different content fails. Choose a new run ID when changing source snapshots. Readback mismatch or storage outage cannot become a verified publication.

## Optional runtime ingestion and outbox recovery

The application never needs S3 credentials. For automatic result publication, run the separate loopback publisher with the registered bindings and a privately configured `SOURCE_INGEST_TOKEN`:

```text
python scripts/serve_source_ingest.py --storage data/source_examples/localstack.json --bindings data/localstack/manual/bindings.json --port 8766
```

Configure the application process with `SOURCE_INGEST_URL=http://127.0.0.1:8766`, the same private token and `ZETARIS_BINDINGS_FILE` pointing at these bindings. Publisher credentials stay in the publisher process. The application persists its output first, sends it to ingestion, and independently reads it through Zetaris. Samples, configurations, rubric results, critiques and repair outcomes are retained. An outage leaves pending IDs in the local SQLite outbox and makes a completed-but-unpublished live result partial.

You can test recovery without any model execution. Stage a labeled fixture in a **new test-only database**:

```text
python scripts/retry_evidence.py --runs-db data/localstack/manual/outbox-test.db --run-id manual-outbox-001 --stage-test-fixture
```

Expected: `status: pending`, one fixture ID, `model_completions: 0`. Existing DB paths are refused in this staging mode.

With the ingestion process unavailable, retry:

```text
python scripts/retry_evidence.py --runs-db data/localstack/manual/outbox-test.db --run-id manual-outbox-001 --bindings data/localstack/manual/bindings.json
```

Expected: exit 1 with that ID still pending. Start/configure ingestion and repeat: expect the ID under `published`, an empty pending list, and zero model completions. A third retry has nothing to publish. Original packs are not silently refinalized; publication receipts remain in the DB. Never erase an actual run DB to repeat a test.

## Automated checks and acceptance boundary

```text
python -m pytest -q tests/test_source_manifest.py tests/test_source_registry.py tests/test_source_ingest.py tests/test_zetaris_adapter.py
python -m pytest -q -rs
python scripts/check_sample_examples.py
```

Actual local collection, S3 emulation registration, typed reads, reference arithmetic and labeled evidence round trips are separate from fixture tests. Recorded results and source hashes are in [m05-m06-source-checks.json](m05-m06-source-checks.json). M05 remains partial for actual serving-provider/variant tariffs, index/terms coverage and usage-rights review; M06 component plumbing passes, while an applicable execution-tariff calculation and a measured model-sample round trip remain pending. Real measured evidence is repeated at M08. AWS, Windows and real H-MEM proof are not established by these checks.

Final validation on the implementation working tree: **72 focused source/integration tests passed; 449 total tests passed, 9 known tests skipped; all three guarded sample examples passed and were regenerated.** The nine skips remain eight shelved retrospective checks and the unavailable real H-MEM feature test. Retained full test output and regenerated CLI packs are under `/private/var/folders/8m/69np3l210snb8twb3tb0d7mh0000gn/T/cost-optimizer-m05-m06-final-idb5tw9c/`; these temporary paths are machine-specific and should be regenerated elsewhere.
