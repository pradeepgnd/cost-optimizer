# Data

The M05–M06 entry in the [evidence ledger](../docs/v4-release-checklist.md) documents the implemented collector, immutable source bundle, publication/registration, typed reads, reference calculation and evidence round trip. [source_examples/](source_examples/) contains public LocalStack/AWS configuration examples and explicitly synthetic/catalog-only route maps. Generated raw data, bundles and reports are under the ignored `data/localstack/` tree. Portable verification summaries for the real AWS bucket are retained outside it in [aws-registration-check.json](../docs/aws-registration-check.json) and [windows-clean-clone-rehearsal.json](../docs/windows-clean-clone-rehearsal.json).

Source manifest schema 1.0 retains raw response files, normalized catalog, quarantined entries, acquisition mode, retrieval time, counts and hashes. Application bundle/bindings schema 1.1 pins dataset/version names, exact IDs/counts and per-row envelope SHA-256. Raw source files are published with the bundle; a release marker is created only after registered data matches. Versioned tables are immutable and no current pointer is automatically promoted. Existing matching sources are reused; conflicts are reported without replacement. Application reads preserve original source URLs/dates/statuses and add separate Zetaris transport/query/hash references.

The source publisher is a separate process. It uses create-only S3 publication and conditional append-only evidence writes with exact readback; the application has no S3 credential requirement. On publication failure, generated output/configuration/rubric/critique/repair evidence remains in a durable SQLite outbox. `scripts/retry_evidence.py` retries publication only, with zero model generations. Its test-fixture mode requires a new test DB and never erases real runs. LocalStack execution has been tested. On AWS, a probe object was read through Zetaris from the team bucket (below); full bundle registration on AWS is the next check.

All runtime data is read through **Zetaris** (live) or from `data/sample/` (SAMPLE_MODE). Registered files live in the team's Amazon S3 bucket; Zetaris reads them from there. Bucket credentials never appear in this repository.

## AWS bucket and Zetaris access

| Item | Value |
|---|---|
| Bucket | `cost-optimizer-oah-k7m2q`, `us-east-1`; Block Public Access on, SSE-S3, versioning, ACLs disabled |
| Prefix | `cost-optimizer/v4/` (bundles, releases, evidence); probe object `cost-optimizer/v4/probe/connectivity_check.json` |
| Storage config | [aws.oah.json](source_examples/aws.oah.json) (no credentials) |
| Zetaris reader | IAM user `zetaris-s3-reader`, inline policy only: `s3:GetBucketLocation` on the bucket, `s3:ListBucket` for prefix `cost-optimizer/v4/`, `s3:GetObject` on `cost-optimizer/v4/*`. No write, delete or other buckets. |
| Writer | The publisher process, using the operator's own AWS sign-in (`aws login`), never the Zetaris key |

Zetaris reads S3 file stores only with a key in the table `OPTIONS`; per-bucket `fs.s3a` settings in the platform's `spark-defaults.conf` are ignored (checked 26 Oct 2026). Zetaris stores datasource credentials encrypted. The publisher therefore adds the reader key to each `CREATE LIGHTNING FILESTORE TABLE` statement on AWS. It reads the key only from `ZETARIS_S3_ACCESS_KEY_ID` and `ZETARIS_S3_SECRET_ACCESS_KEY` in the publishing terminal, never from `.env`, and dry-run plans, reports and traces show `<key id>` / `<secret>` or `...redacted` instead. Set them for one command and clear them afterwards:

```powershell
$env:ZETARIS_S3_ACCESS_KEY_ID = Read-Host "zetaris-s3-reader access key ID"
$env:ZETARIS_S3_SECRET_ACCESS_KEY = Read-Host "secret access key" -MaskInput
python scripts/register_sources.py --bundle <BUNDLE_DIR> --storage data/source_examples/aws.oah.json --apply --bindings-output <BINDINGS> --report <REPORT>
Remove-Item Env:ZETARIS_S3_ACCESS_KEY_ID, Env:ZETARIS_S3_SECRET_ACCESS_KEY
```

To re-register on another Zetaris install, use the same command there; existing matching tables are reused, and a new machine needs its own reader key in the same two variables.

| Source set | Live source name | Sample file | Status | Notes |
|---|---|---|---|---|
| founder_briefs | `oah.founder_briefs` | `founder_briefs.json` | synthetic | Two synthetic briefs. The AVL pre-build brief was removed in v4 (the retrospective is shelved, 07 §10). Founder ideas used as run inputs are in `input_examples/` and `docs/founder_ideas_examples.md`, every number labeled assumed. |
| pricing_snapshots | `oah.pricing_snapshots_*` | `pricing_snapshots.json` | **PLACEHOLDER / unverified** | To be replaced by dated, URL-cited actual-route pricing (W04). Unknown rates stay unknown. Each model row may also carry an `intelligence` score (`score`, `score_source`, `score_date`) and a `market` reference from an OpenRouter catalog snapshot (catalog ID, list prices, usage rank, snapshot date). Catalog rates can feed a separately labeled hypothetical OpenRouter serving table after a pinned Zetaris read; they never authorize Nightshift calls or determine its actual-route costs, switch points or recommendations. Record the index name, catalog URL, date and licence here when registered. The open-source row marked `required` is the Nemotron route. |
| dev_task_cases | `oah.dev_task_cases` | `dev_task_cases.json` | derived | 6 spec-level tasks (T1–T6); 3 development, 3 holdout. Holdout rows are sealed until freeze. |
| evaluation_evidence | `oah.evaluation_evidence` | written at run time | generated | Case results and critiques; live writeback via the supported registration path. |
| retrospective_actuals | `oah_sealed.retrospective_actuals` | `retrospective_actuals_SYNTHETIC.json` | **synthetic in repo** | The founder's real aggregate exists only in the live sealed source and the deck, with the founder's consent. The repository never contains it. |

Validate sample outputs with `python scripts/check_sample_examples.py`. Regenerate committed outputs using fresh isolated databases and the original example IDs. Source URL, licence, subset and hash are recorded with each live registration. No data predates the build window (22 Oct 2026, 00:00 UTC).

## Provider discount compatibility

`ModelPricingTerms.lever_combinations` contains exact combinations of `prompt_caching`, `batch_api` and `long_context_cliff`. Each entry has `levers`, `supported` and a `SourceRef`. Applying a combination requires `supported=true`, source status `verified`, a valid ISO verification date and an HTTP(S) source URL. Unsupported, absent, unverified or undated rules do not allow stacked discounts; the calculator selects the cheapest supported standalone scenario instead. Three-way compatibility must be cited explicitly, even if all pairs are supported. Record each combination's source/version through the same Zetaris price snapshot path.

For a long-context request, cache rates must use the explicit `long_context_cached_input_tokens` and `long_context_cache_write_tokens` categories. The calculator does not substitute ordinary cache rates for missing tier rates. Unknown required long-context input/output prices keep the decision cost unknown. Optional unavailable cache pricing leaves caching unapplied.

Live dispatch also requires an optional `ModelProfile.dispatch_policy` to be populated with actual route evidence. It contains `max_prompt_bytes`, `prompt_tokens_per_byte`, `prompt_overhead_tokens`, `max_output_tokens`, `completion_limit_includes_reasoning: true`, `billing_mode: input_output_only`, and a dated, verified HTTP(S) `SourceRef`. The byte-to-token bound and overhead must cover the serialized messages and any runtime-added framing/tokens; the output limit must include hidden reasoning. `input_output_only` attests that the cited full input/output rates bound all request billing, including routing/other fees, without additional unmodeled billing categories. Routes with separate/unbounded charges require another supported billing policy and currently cannot dispatch. Do not treat these fields as founder estimates or mark them verified without evidence.

The model/terms source and each required rate source must be dated, verified and cited. Required rates have unit `1M tokens`, finite non-negative USD values and unique categories. Reservations cover both ordinary and required long-context tariffs and never assume projected cache/batch discounts. Measured charges select the actual whole-request tariff. Planner and Critic routes must be present as priced profiles too; an automatic router alias is insufficient. Actual resolved identity must match the priced route or the outcome remains reserved/unknown pending verification. Sample data intentionally has no dispatch policies; the attestations under `tests/dispatch_fixtures.py` are synthetic test fixtures, not usable provider evidence.

