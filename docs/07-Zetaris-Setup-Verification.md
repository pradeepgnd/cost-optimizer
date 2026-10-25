# Local Zetaris verification

Verified 25 October 2026 UTC (24 October evening in America/New_York), against repository commit `3e90d15`.

**Stage 1 complete:** the installed platform's `verify.sh` passes all 9 checks, and the user's configured application credential passes `SELECT 1 AS one` through the app's own adapter. Both checks passed on 25 October 2026 at 00:28 UTC.

| Check | Observed result |
|---|---|
| Installation | Docker Compose project `zetaris`, configuration at `/Users/muthumeena/Hackathon/zetaris-platform/docker-compose.yml` |
| Long-running services | `postgres`, `driver`, `api`, and `ui` running and healthy |
| Initialization jobs | `init` and `bootstrap` completed with exit code 0 |
| Bundle verification script | 9/9 passed again on 25 October 2026 at 00:28 UTC; [recorded output](zetaris_platform_verify.txt) |
| Docker | Engine 29.7.2, 15 CPUs, 8,318,844,928 bytes of reported memory, aarch64 |
| Web interface | `http://localhost:3000` resolves to HTTP 200 after its redirect |
| Administrator sign-in | HTTP 200; session token and organization ID returned; neither retained in evidence |
| UI SQL route | `POST /api/proxy/query/sql/start`, `SELECT 1 AS one`, returned `one = 1` |
| Direct REST SQL route from guide | `POST http://localhost:8888/api/v1.0/sql-editor/sqls/run`, returned HTTP 200 and one row containing 1 |
| Other direct SQL route | `POST /api/v1.0/query/sql/start`, returned HTTP 200 and `one = 1` |
| API documentation | `http://localhost:8888/redoc/index.html` accessible with administrator authentication; specification reference `./docs.yaml` |
| Current app adapter | `ZetarisDataLayer.select_one()` passed against the live server with a temporary administrator session; sanitized result in [zetaris_session_connection_check.json](zetaris_session_connection_check.json) |
| Configured application credential | User confirmed creating/configuring the API key; independent app check passed with one row containing `1`; [sanitized result](zetaris_connection_check.json) |
| Organization ID | Working sign-in returned `1`; use this value for this installation's app configuration |

The guide's REST route accepted this request shape (request identifiers generated freshly for each request):

```json
{
  "queryId": "<fresh UUID>",
  "sql": "SELECT 1 AS one",
  "source": "SqlEditor",
  "limit": 1
}
```

It returned column names in `headers` and rows as arrays in `data`. The sanitized observed response is saved in [zetaris_select1_response.json](zetaris_select1_response.json). It contains only the query result and timing, with no credentials or authentication tokens. This response establishes the SELECT 1 envelope; queries against registered project tables still need their own mapping verification.

## Stage 1 completion and scope

- **Completed:** the initial 7/9 verification failure was resolved by synchronizing only the platform's saved `ZETARIS_ADMIN_PASSWORD` with the working administrator sign-in, under the user's explicit authorization. The installed, unmodified `verify.sh` then passed **9/9**. No account password or other platform setting was changed.
- **Completed:** the original checks used an administrator session token. The user subsequently confirmed completing API-key creation and private app configuration. The standalone app check loaded the existing configuration and returned the expected row through the actual app adapter. No credentials were printed or included in the JSON report or query trace.
- The live adapter and Windows preflight now include `source: SqlEditor` and use `SELECT 1 AS one`. Windows preflight validates the returned value as well as the HTTP status. Its PowerShell execution still needs a Windows host; the request contract is covered by automated HTTP tests.
- Queries against the project's founder, pricing, task, and evidence sources are Stage 2 work and were not performed here. No sealed actuals or holdout data was queried.

No passwords, API keys, login tokens, or raw authentication responses were saved to the repository. The only private configuration change was the user-authorized synchronization of the platform's saved administrator password. Services and account credentials were not changed.

## Reproducible app connection check

With the private app configuration already present, repeat the check with:

```bash
python scripts/check_zetaris.py --output docs/zetaris_connection_check.json
```

The command uses the app's actual Zetaris adapter, requires no other sponsor runtime, and checks the returned SQL value. Its JSON report and trace exclude credentials and raw authentication responses. Exit codes are 0 for verified SQL, 2 for incomplete configuration, and 3 for a connection or query failure. The report labels the authentication as a configured bearer credential because a successful HTTP query alone cannot establish that the credential is a newly created API key rather than a session token; API-key provenance must come from the human token-creation step.

Stage 1 implementation checks: **33 tests passed, 1 H-MEM test skipped**. Contract tests cover authenticated request headers and body, rejection of empty/incorrect HTTP-200 results, and omission of credentials from reports and traces. The live app check now reports `SQL_VERIFIED` with exit code 0. Project source registration, H-MEM, and Nightshift remain later stages.

The earlier administrator-session result is retained separately from the later configured app-credential result. API-key creation is confirmed by the user's setup report; the successful SQL query independently establishes that the credential configured for the app authenticates and can execute SQL.
