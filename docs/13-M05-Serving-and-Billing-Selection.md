# M05 serving and billing selection

Checked October 25, 2026. This selection uses the project's configured Nightshift connection without copying or changing `.env`. `GET /v1/models` advertised 75 routes and returned only ID, owner and creation metadata for the selected routes; it did not return prices, active serving endpoints or billable usage rules. No completion was sent.

| Role | Nightshift serving route | OpenRouter catalog ID | Catalog reference input/output, USD per 1M tokens |
|---|---|---|---|
| Frontier | `nvidia/nemotron-3-ultra-550b-a55b` | Same ID | 0.60 / 2.40 |
| Mid-tier | `nvidia/nemotron-3-super-120b-a12b` | Same ID | 0.30 / 2.40 |
| Required open model | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning` | 0.07 / 0.20 |

Ultra is [identified by NVIDIA as a frontier model](https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b/modelcard); Super is the smaller [120B model](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b) from the same lab; [Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) is the required 30B/3B-active Nemotron route. This available set gives a size/cost comparison within the NVIDIA open-model family. It does not demonstrate a closed frontier model versus an open model, which was the original product framing. None has yet been executed on this Nightshift instance, so discovery proves advertised route IDs only.

Planner: reuse the Lightning route already configured in `.env`. Critic: use the advertised `local-runtime/nemotron-3-nano-30b-a3b` route, a distinct [NVIDIA Nemotron Nano model](https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b) with catalog comparison ID `nvidia/nemotron-3-nano-30b-a3b`. This follows the requested NVIDIA-only Critic choice. The Critic shares NVIDIA as a lab with every candidate; route separation does not make its flags independent. Its local readiness, quality on the flags-only task, hardware cost and dispatch bounds remain unverified. Its OpenRouter catalog price is not the cost of a local Nightshift request.

The catalog rates above are from the retained OpenRouter API snapshot `a6cff78717992be3b332c65d`, fetched at `2026-10-25T22:27:42Z`. They are **market references**, not Nightshift execution tariffs. NVIDIA's model pages list provider-specific partner prices that may differ from the catalog snapshot. [Meterless says cloud providers added to Nightshift bill through the user's own provider key](https://meterless.ai/); the Nightshift response here does not identify which provider endpoint or billing account these three routes would actually use. [NVIDIA's Developer Program endpoints are free for prototyping](https://docs.api.nvidia.com/nim/docs/product), while production serving has separate licensing/hosting terms. A zero-dollar trial endpoint cannot be extrapolated into a founder's production cost projection. The [OpenRouter terms](https://openrouter.ai/terms) and each model's terms also need review before redistributing catalog data or using the service for a public product; this source review does not claim those rights.

The selected route map is [routes.nvidia-selected.json](../data/source_examples/routes.nvidia-selected.json). It starts as `planned` because the reusable JSON does not embed a machine-specific discovery; `prepare_source_bundle.py --discovery` attaches the retained discovery hash and upgrades the immutable bundle mapping to `discovery_observed`. Local artifacts:

- Discovery: `data/localstack/source-discovery-m05-20261025.json` (75 IDs, zero completions).
- Final bundle: `data/localstack/openrouter/bundles/740f951a20335bd2570f7a4c` (460 catalog rows, three candidate rows, one NVIDIA Critic row, one synthetic brief). It adds exact `market.catalog_id` mapping for each row. Earlier bundles remain immutable.
- LocalStack/Zetaris bindings: `data/localstack/openrouter/bindings-final-scenario.json`; registration and exact-reuse reports: `data/localstack/openrouter/registration-final-scenario-result.json` and `registration-final-scenario-repeat.json` (all three tables and published objects reused).
- Final typed-read check: `data/localstack/openrouter/final-scenario-read-001/report.json` (four exact model IDs and a catalog-reference calculation). A later `final-roundtrip-001/report.json` also passed fixture write/readback, append, restart and duplicate handling; its fixture SourceRef stayed `unverified`. `execution_billing_verified` is false.
- Full no-completion application preview: `data/localstack/openrouter/openrouter-projection-002/report.json` and `pack.json`. It queried three pinned catalog rows through Zetaris, produced 24 OpenRouter scenario rows for two features and four growth stages, left all 24 actual-route cost rows unknown, and dispatched zero completions.

Current role configuration in `.env` selects Lightning for Planner and Ultra for Critic. With Ultra selected as the frontier candidate, the controller rejects the current Critic route because an advertised noncandidate route exists. `METERLESS_CRITIC_MODEL` must be changed or overridden to `local-runtime/nemotron-3-nano-30b-a3b` before a live application run. The project's `CLAUDE.md` explicitly says never to edit `.env`, so this selection does not change it. Both role routes need verified execution tariffs and dispatch policies before any paid call.

Manual read check on this machine, with no model completions:

```bash
.venv/bin/python scripts/check_zetaris_sources.py --bindings data/localstack/openrouter/bindings-final-scenario.json --catalog-id nvidia/nemotron-3.5-lightning --output-dir data/localstack/openrouter/serving-read-002
```

Expected: `status: pass`, the four exact Nightshift model IDs above, and `execution_billing_verified: false`. Choose a new output directory on every run.

To preview OpenRouter monthly token costs using the actual controller without any model completion:

```bash
.venv/bin/python scripts/check_openrouter_projection.py --input input_examples/example_3.json --bindings data/localstack/openrouter/bindings-final-scenario.json --output-dir data/localstack/openrouter/openrouter-projection-next
```

Expected: two `openrouter_projection_tables`, 24 scenario rows (three candidates × four stages × two features), three Zetaris catalog source IDs, zero model completions and zero known actual-route monthly rows. The tool forces evaluation approval off and spend to zero. It overrides only the Critic route in memory; `.env` is untouched. Inspect `pack.json` for each row's tokens, monthly cost, lower-bound warning and source snapshot. The first sandboxed check could not reach local services; the recorded passing check used normal network access.

## Billing decision and remaining acceptance

The app now uses OpenRouter's pinned catalog prices for a **separate hypothetical serving projection**. Its rows carry the Zetaris source, use the same measured or estimated workload tokens, and are always labeled lower bounds. They are excluded from the actual-route operating table, switch decisions, dispatcher reservations and model-stack recommendations. [OpenRouter says token charges use posted model rates and account fees are charged on credit purchases](https://openrouter.ai/pricing); the current scenario reports the listed token subtotal, without account fees, provider-specific/conditional tariffs or proof that Nightshift's tokenization would match. It does not claim an actual invoice.

To compute the actual Nightshift bill or authorize paid evaluation, use the exact Nightshift serving provider/variant and its official billing source for each candidate, Planner and Critic. Pin the account/endpoint tariff, input/output and reasoning treatment, any fees, cache/batch/context rules, date, source URL, and content hash. Include a cited route-specific prompt/output bound and proof that `max_tokens` includes hidden reasoning. If Nightshift uses NVIDIA's free development endpoint, record that as a **prototype entitlement** only; use the OpenRouter scenario as an alternative production assumption. Do not fill `billing_profile` or mark actual-route rates verified from OpenRouter market prices alone.

The configured connection and `.env` do not expose these billing facts. Until they are confirmed, M05 remains partial and live dispatch correctly refuses to reserve a paid attempt. If the intended comparison must include a non-NVIDIA frontier lab, provision that route in Nightshift and replace the corresponding mapping before accepting M05. An intelligence index also needs a dated, licensed source if used in the shortlist; the current OpenRouter snapshot does not contain one.

Once the provider/tariff evidence is available: add cited `billing_profile` records to the selected route map, create a new immutable bundle, register it, read every model through Zetaris, run the verified-tariff stage-cost check, and repeat publication to confirm exact reuse. The [manual M05/M06 guide](12-M05-M06-Manual-Testing.md) gives the commands and negative checks. AWS publication, real measured model evidence and H-MEM remain separate later checks.
