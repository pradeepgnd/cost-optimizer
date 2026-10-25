# LocalStack S3 and Zetaris

This setup implements the requested local storage route:

```text
Python app → Zetaris → LocalStack S3 → project setup fixtures
```

The current package uses the existing `zetaris_default` Docker network and a pinned LocalStack image. It adds a separate Compose project; it does not replace the Zetaris stack. Files under `data/localstack/` are generated from the bundled sample data and are **setup fixtures**. Prices remain unverified and founder/rubric approval is still pending. No real retrospective actuals or fabricated evaluation results are uploaded.

## Current execution status

**All six requested storage-integration steps completed on 25 October 2026 UTC.** LocalStack 2026.10.2 is activated using the user's privately configured token, S3 operations work, and the project files are uploaded. Zetaris has six registered file-source tables. Queries through the app's Zetaris adapter returned the exact probe row and the expected ordinary dataset counts. A repeat registration run reused the same tables successfully.

The [successful registration report](localstack_registration_check.json) records source paths, verified counts, SQL query IDs, and the local trace path. Automated checks pass: **37 passed, 1 H-MEM test skipped**. These results establish the real storage/query integration with sample fixtures; founder approval, dated pricing, and the full agent workflow remain separate work.

The LocalStack container reports healthy using its installed Python runtime for the health probe; this image does not contain `curl`. It was recreated with its named volume, and the full SQL registration/count check passed again afterward. The bucket contains the seven current objects listed below, including the manifest; the obsolete JSON Lines setup copies were removed.

## Activate and run the six steps

1. Obtain a LocalStack account token using the [official auth-token instructions](https://docs.localstack.cloud/aws/getting-started/auth-token/). Privately add `LOCALSTACK_AUTH_TOKEN` to the existing project `.env` yourself, or export it in the shell used to run Docker Compose. The LocalStack account token is separate from Zetaris's API key and from the dummy S3 credentials used for local emulation. No paid subscription is authorized by this setup.
2. From the project root, prepare the upload objects, check Compose configuration without printing resolved secrets, and start the service:

   ```bash
   python scripts/prepare_localstack_data.py
   docker compose -f compose.localstack.yaml config --quiet
   docker compose -f compose.localstack.yaml up -d
   docker compose -f compose.localstack.yaml ps
   ```

   The container joins `zetaris_default` with the DNS name `cost-optimizer-localstack`; the driver reaches S3 at `http://cost-optimizer-localstack:4566`. The host reaches its published gateway at `http://localhost:4566`. Only the gateway port is published, on the loopback interface. A named volume stores LocalStack state.
3. The ready hook creates bucket `cost-optimizer-data` if needed and uploads the prepared objects under `cost-optimizer/v1/`. Confirm that actual S3 operations work, rather than relying only on the gateway health response:

   ```bash
   docker exec cost-optimizer-localstack awslocal s3 ls s3://cost-optimizer-data/cost-optimizer/v1/ --recursive
   docker exec cost-optimizer-localstack awslocal s3 cp s3://cost-optimizer-data/cost-optimizer/v1/connectivity_check.csv -
   ```

   The probe CSV contains `id,message` and one row: `1,localstack_connection_ok`. These are public synthetic setup values. The bootstrap uses LocalStack-only `test` S3 credentials and never receives the app's Zetaris credentials.
4. Review the fixed Zetaris registration plan, then register the dedicated sources and verify ordinary records:

   ```bash
   python scripts/register_localstack_sources.py
   python scripts/register_localstack_sources.py --apply
   ```

   Each DDL statement is sent separately through the app's Zetaris transport. The file-store options specify the custom S3 endpoint, path-style access, and dummy local S3 credentials, following [Zetaris's S3-compatible registration documentation](https://kbase.zetaris.com/knowledge/how-to-connect-to-minio-s3). Existing dedicated tables are reused. Listing a file-source namespace requires `SHOW LIGHTNING TABLES <name>` in this installation.
5. The registration script checks the probe row through Zetaris and counts the ordinary project records. On success, `docs/localstack_registration_check.json` contains `status: passed` and the verified counts. This proves the path from the Python host through Zetaris to LocalStack; successful `awslocal` output alone does not prove that path.
6. The same script registers the prepared founder, pricing, and development-task tables, plus the separately named holdout table. The holdout contents are not queried by the script. These fixtures are staging data; approved live datasets and the remaining app row mapping are later work.

## Prepared objects and tables

| S3 key under `cost-optimizer/v1/` | Rows | Zetaris table |
|---|---:|---|
| `connectivity_check.csv` | 1 | `oah_localstack.connectivity_check` |
| `inputs/founder_briefs.json` | 3, SQL verified | `oah_localstack.founder_briefs` |
| `inputs/pricing_snapshots_approaches.json` | 4, SQL verified | `oah_localstack.pricing_snapshots_approaches` |
| `inputs/pricing_snapshots_models.json` | 2, SQL verified | `oah_localstack.pricing_snapshots_models` |
| `inputs/dev_task_cases_development.json` | 3, SQL verified | `oah_localstack.dev_task_cases` |
| `sealed/dev_task_cases_holdout.json` | 3 exported; contents not queried | `oah_localstack_sealed.dev_task_cases_holdout` |
| `manifest.json` | Metadata | File counts, SHA-256 hashes, and fixture limitations |

JSON arrays expose simple identifier/status fields and preserve each validated app contract as a string in `payload_json`. The installed reader returned only the first object from JSON Lines; complete JSON arrays with `multiLine: true` returned all expected ordinary rows. The app's future read methods must decode and validate `payload_json`; those methods remain unimplemented at this stage.

If updating exported fixture data after the container is already running, upload it again with:

```bash
python scripts/prepare_localstack_data.py
docker exec cost-optimizer-localstack sh /etc/localstack/init/ready.d/10-cost-optimizer-s3.sh
python scripts/register_localstack_sources.py --apply
```

For an earlier setup that registered the old JSON Lines paths, use `--apply --refresh-json` after uploading the current exports. This uses Zetaris's supported GET/PATCH file-source metadata API to update the dedicated JSON paths and reader parameters, preserving the source settings and objects. Normal runs reuse existing definitions without that update.

The separate `sealed/` prefix and source name support the planned freeze boundary, but do not by themselves enforce it. LocalStack's emulated storage is not evidence of AWS IAM isolation. Controller authorization and the required Zetaris permissions must be completed before a live evaluation. Raw actuals and evaluation results are not part of this initial upload package.

## Completion criteria

- LocalStack is activated and S3 accepts bucket/object operations.
- The Zetaris driver resolves and reaches `cost-optimizer-localstack:4566` on the shared network.
- The probe query returns the exact uploaded row through Zetaris.
- Registered ordinary tables have the expected counts and retain their fixture/status labels.
- No holdout rows or real retrospective actuals were queried for setup verification.

The runtime criteria above were observed and the successful report is saved. The holdout claim is deliberately limited to registration; this script performs no SELECT against its contents. The Stage 1 Zetaris verification remains a separate completed check.
