# OpenRouter collection options

Reviewed October 25, 2026. OpenRouter remains the chosen public catalog source. This document retains the source-option comparison and earlier feasibility observations. **Implementation update:** automated snapshots, pinned bundles, LocalStack/Zetaris registration, typed reads and labeled evidence round trips now exist and have component evidence. Use the [Steps 5–6 manual guide](12-M05-M06-Manual-Testing.md) and [verification record](m05-m06-source-checks.json). M05/M06 overall acceptance remains partial for execution tariffs/source coverage and measured-model evidence.

## Recommendation

Implement automated snapshots first: **OpenRouter → collector → immutable S3 objects → Zetaris → application**. This preserves the existing S3 registration design and produces repeatable evaluations. Explore direct REST federation as a separate component experiment; add it to the application only after its query, pagination and cache behavior are demonstrated.

Every evaluation pins the records it actually used. Snapshotting is a requirement for reproducibility, whether collection uses a script or Zetaris REST tables. All inference continues through Nightshift.

## What was checked

| Check | Result | Limit of the evidence |
|---|---|---|
| Collector | Implemented in `app/source_snapshots.py` and `scripts/collect_sources.py`; raw/normalized/quarantined data and hashes retained | Catalog acquisition does not verify an execution tariff |
| Adapter | Typed pinned reads and external ingestion/readback implemented; local component round trip passes | Applicable tariff and measured-model acceptance remain separate |
| Historical S3 setup | Commit `1f27731` contains preparation, registration, typed reads and evidence round-trip code | LocalStack-specific fixtures and old contracts need adaptation; historical traces do not certify this checkout |
| Installed REST support | Zetaris SQL 2.4.3.1 jars contain `LightningRestTableRegister`, `RESTApiRelation` and REST query-strategy classes | Class presence does not prove configuration, licensing, response mapping or execution |
| Driver outbound access | On October 25 at 21:23:10 UTC, the running driver fetched the OpenRouter models URL: HTTP 200, 467 records, no next-page link | HTTPS reachability only; no REST table was registered or queried |
| Application query bound | Replaced by pinned table/version reads with exact expected IDs/counts, one extra row for overflow detection and per-row hashes | The old `LIMIT 50` transport template is not the bound application read path |

The driver response SHA-256 was `596c40ea52be8d4043e028e3c4ab409ab23a390a0e9922bce20dc9c93b21ce1d`. The response body was not retained, so this hash identifies the observation but is not a replayable snapshot artifact. No source registration or model execution was performed during these checks.

## Comparison

| Property | Automated snapshots | Direct REST tables | Hybrid |
|---|---|---|---|
| Acquisition | Collector fetches OpenRouter | Zetaris fetches OpenRouter during source evaluation, subject to connector caching | Zetaris fetches live data and persists the exact retrieved records for each run |
| Application reads | Versioned S3 source through Zetaris | REST source through Zetaris | Persisted version through Zetaris |
| Freshness | Proposed refresh before an evaluation; show retrieval age | Depends on upstream edge caching and Zetaris caching | Depends on refresh policy; evaluation remains pinned |
| Repeatability | Natural fit with immutable objects | Requires explicitly retaining the evaluated records | Built into the design |
| Outage behavior | Existing pinned snapshots remain queryable; stale use must be disclosed | Upstream failure can prevent a new retrieval | Prior pinned versions remain available |
| Main implementation risk | Validation, publication and registration | Connector configuration, nested JSON, pagination, caching and upstream errors | Adds persistence and publication to REST federation |
| Fit for M05/M06 | Best fit with the current plan and recoverable code | Useful isolated experiment | Later extension if direct federation proves useful |

## OpenRouter inputs and their meaning

1. Start with `GET https://openrouter.ai/api/v1/models`. Preserve the raw response and normalize its `data` records. The documented default is a full list; when pagination is requested, follow the returned next-page links with explicit request/row bounds and refuse incomplete publication. Restrict pagination destinations to the expected HTTPS host and API path.
2. Optionally enrich selected candidates with `GET https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints`. This distinguishes serving providers, endpoint prices and performance. Its documentation specifies bearer authentication; access has not been tested in this review. Failure must not silently substitute the model-level cheapest or default provider price.
3. Keep intelligence scores, popularity and benchmark results absent when not supplied. Context length and price are not intelligence scores. Any popularity ranking needs its actual query/order and measurement window recorded.

Model-level catalog pricing describes OpenRouter's top provider. It is not automatically the tariff of the provider Nightshift used. The implementation now uses pinned catalog rows for a separately labeled hypothetical OpenRouter serving projection, alongside shortlist ranking. Promoting a collected rate to an **actual Nightshift** economics input still requires an explicitly reviewed model/provider/variant/terms mapping and compatible provenance; acquisition through Zetaris does not itself verify billing equivalence. No such promotion is made by this review.

For a catalog-only comparison, label results as OpenRouter reference-price scenarios. Measured token counts may come from Nightshift, while actual billed charges remain distinct evidence.

## Option A: automated snapshots

### Initial NVIDIA candidate decision

Selected October 25, 2026: **Nemotron 3.5 Lightning 30B-A3B** is the initial NVIDIA/open-source candidate for the text workload comparison. NVIDIA describes it as a 30B-total/3B-active model for agentic workloads and instruction following. This is a candidate selection, not measured proof that it meets the founder's quality requirements; deterministic checks and required human review remain the decision gate.

| Mapping | Value | Status |
|---|---|---|
| OpenRouter catalog model | `nvidia/nemotron-3.5-lightning` | Observed in the public catalog |
| NVIDIA-backed Nightshift route | `nvidia/nemotron-3.5-lightning-30b-a3b` | Advertised in the earlier local discovery check; actual execution/variant identity remains M08 |
| Possible OpenRouter-backed Nightshift route | `openrouter/nvidia/nemotron-3.5-lightning` | Present in the bundled registry; provider configuration and runtime availability remain unverified |

At **2026-10-25 21:43:17 UTC**, a read-only request from the Zetaris driver to the public models API returned the following model-level reference rates. These are API-observed catalog rates, not pinned serving-provider tariffs, actual billed charges, or an implemented S3 snapshot. They differ from some website starting-price displays; preserve the API payload and exact serving endpoint during M05 rather than mixing sources.

| Model | OpenRouter ID | Input USD / 1M tokens | Output USD / 1M tokens | Role in this decision |
|---|---|---|---|---|
| Nemotron 3.5 Lightning | `nvidia/nemotron-3.5-lightning` | 0.07 | 0.20 | Initial NVIDIA candidate |
| Nemotron 3 Super | `nvidia/nemotron-3-super-120b-a12b` | 0.30 | 2.40 | Alternative to evaluate if needed |
| Nemotron 3 Ultra | `nvidia/nemotron-3-ultra-550b-a55b` | 0.60 | 2.40 | Alternative for reasoning-heavy workloads |

Only Lightning occupies the mandatory NVIDIA slot in the planned three-candidate comparison; the other two are alternatives for a deliberate later evaluation, not automatic runtime fallbacks. A zero-cost NVIDIA trial route and a paid OpenRouter route are separate cost scenarios. No inference call, provider configuration change, price-row promotion or `.env` change was made for this selection. Arithmetic continues in the deterministic Python calculator.

Sources: [NVIDIA model card](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard), [OpenRouter catalog API](https://openrouter.ai/api/v1/models), and the installed Nightshift registry. The collected pricing payload was not retained by this diagnostic, so M05 still needs a replayable snapshot.

### Implementation outline

Proposed implementation, with file names to be chosen during M05:

1. Fetch with finite timeouts, response-size limits and bounded retries for these read-only calls. Capture URL, retrieval time, response validators when present, collector/schema version and raw-body SHA-256.
2. Validate unique model IDs, finite non-negative decimal prices, units, required fields and completeness. Convert token prices using exact Decimal arithmetic: USD/token × 1,000,000. Preserve missing values as null and explicit zeros as zero; do not invent cache-write, TTL, batch or context terms.
3. Preserve raw conditional pricing overrides. Map only supported conditions to the current tariff contracts; keep incompatible conditions ineligible for a verified effective total instead of dropping them. Fixed per-request or other charges need explicit handling before claiming a complete cost.
4. Write raw data, normalized records and a manifest to immutable keys such as `catalog/openrouter/<snapshot_id>/...`. Record S3 VersionId when available as well as content hashes; an ETag is not the content-hash contract.
5. Keep publisher credentials in the collection/deployment process and source-read credentials Zetaris-side. The application runtime only queries Zetaris. LocalStack remains an explicitly identified integration environment, separate from production AWS storage.
6. Validate staged data through Zetaris before publishing a release manifest. A proposed current-version pointer is updated only after that check; running evaluations retain their previously resolved snapshot ID.
7. Supply the existing adapter's record envelope or an explicitly versioned replacement. Pin Nightshift route mappings separately from the external catalog. Avoid a new table registration for every model or collection event where a supported version-filtered source can be reused.

**Acceptance:** collect → validate → publish → register → Zetaris read reproduces the normalized rates and snapshot hash. Repeating publication reuses identical content or reports a conflict. Interrupted/incomplete refreshes cannot replace the last accepted version. A second run can reproduce its original source version after the public catalog changes. Check route identity, Decimal conversion, unknowns, malformed prices, duplicates, pagination limits and stale-source disclosure.

## Option B: direct Zetaris REST tables

The installed connector classes and successful HTTPS fetch justify an isolated proof of concept. They do not yet justify replacing S3 registration.

1. Use the installed API schema or source wizard to define the REST table; do not guess Lightning SQL options from public documentation alone. Use a dedicated experimental namespace and keep existing sources intact.
2. Retrieve the OpenRouter model list and demonstrate extraction of `data[]`, nested `pricing` fields and conditional overrides. Preserve decimals as strings or exact decimals through the mapping.
3. Verify record counts and selected IDs against the same captured upstream response. Test pagination explicitly when enabled; a SQL `LIMIT` does not establish that the connector fetched every upstream page or pushed the bound to the API.
4. Observe caching and refresh behavior. A successful query cannot by itself establish that the upstream API was contacted for that evaluation. Preserve retrieval time when known and report it as unknown otherwise.
5. Exercise schema changes, rate limits, timeouts and malformed/error bodies. HTTP 200 containing an error or incomplete data must not become a valid price table.
6. Retain the exact records used by an evaluation, with hashes and a configuration reference. An unversioned live view alone cannot support reproducible recommendations.

**Acceptance:** a real Zetaris SQL query returns the expected model and exact prices; response mapping, completeness and caching are demonstrated; a run can reproduce its original evaluated records. Until then, mark this option experimental.

## Option C: hybrid

Use the validated REST table for discovery/refresh, then persist the exact retrieved records into supported versioned storage before evaluation. The application reads that version through Zetaris. Persist and evaluate the same retrieval; a second upstream fetch can already contain different data.

This offers direct federation plus an audit trail, but still needs a supported writer, manifest publication and all M06 evidence write/readback behavior. OpenRouter is a read source; inference results belong in the project's separate writable evidence store.

## Incremental delivery

1. M05: collector fixtures, immutable manifest and S3/LocalStack registration, with an actual cited catalog row read through Zetaris. Keep the row's catalog-reference meaning explicit.
2. M06: typed adapter reads, complete bounded retrieval, original citations plus Zetaris references, and independent evidence write/readback. Retain the milestone's separate verified-tariff stage-calculation acceptance requirement.
3. REST experiment: demonstrate the Option B checks independently of the controller, Nightshift and H-MEM. Adopt hybrid only if its demonstrated value justifies the extra writer/persistence work.

This exploration changes no milestone completion status. M05/M06 close only on their implemented, executed acceptance evidence.

## References

- [Zetaris source connections](https://kbase.zetaris.com/knowledge/connect): file and REST sources, including the source-registration workflow.
- [Zetaris SQL guide](https://kbase.zetaris.com/knowledge/sql-guide): REST table registration and lakehouse concepts; installed syntax still needs confirmation.
- [OpenRouter Models guide](https://openrouter.ai/docs/guides/overview/models): catalog semantics, units, pagination and pricing overrides.
- [OpenRouter model endpoints](https://openrouter.ai/docs/api/api-reference/endpoints/list-all-endpoints-for-a-model): serving-provider records and authentication.
- [M00 integration inventory](evidence/m00-integration-inventory.md): historical code and adaptation boundaries.
