# M05 serving and billing selection

> **Superseded route roles (October 26, 2026).** The role assignments in this document (Ultra frontier, Lightning mid-tier, Gemma required open model) are superseded by `Planning/07-Realignment-v4.md` v4.2 and [routes.selected.json](../data/source_examples/routes.selected.json): Nemotron 3.5 Lightning 30B is the required open-source route, Gemma 4 31B is mid-tier, and Nemotron 3 Ultra 550B is frontier ("largest available (open weights)"). The Critic must not use a candidate's route while Nightshift offers another, so the Ultra-as-Critic configuration described below now stops before any paid call. The serving, billing and catalog-price findings below still apply; bundles and bindings named below were registered under the old roles and need re-preparing.

Updated October 25, 2026: Gemma 4 31B Dense (free OpenRouter route) replaces Super as the required open-model contender. Lightning remains mid-tier and Ultra remains frontier. Fresh `GET /v1/models` discovery advertised 112 routes, including the exact Gemma route; it did not return active serving endpoints or billable usage rules. No completion was sent during this selection check. The earlier `feature/plan-07-impl-meena` Stage 3 record separately documents live Ultra and Lightning requests with NVIDIA cloud winning-route receipts.

| Role | Nightshift serving route | OpenRouter catalog ID | Catalog reference input/output, USD per 1M tokens |
|---|---|---|---|
| Frontier | `nvidia/nemotron-3-ultra-550b-a55b` | Same ID | 0.60 / 2.40 |
| Mid-tier | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning` | 0.07 / 0.20 |
| Required open model | `openrouter/google/gemma-4-31b-it:free` | `google/gemma-4-31b-it:free` | 0 / 0 (listed free tier only) |

Ultra is [identified by NVIDIA as a frontier model](https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b/modelcard); [Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) is the selected mid-tier route; [Google's model card](https://ai.google.dev/gemma/docs/core/model_card_4) identifies Gemma 4 31B as the dense open model. The user's `gemma-4-31b-dense-free` label maps to Nightshift's exact advertised route `openrouter/google/gemma-4-31b-it:free`, not a literal route ID. [OpenRouter lists that free model](https://openrouter.ai/google/gemma-4-31b-it%3Afree). This gives a Google-versus-NVIDIA comparison. The prior live Ultra and Lightning probes are historical; Gemma has no current verified completion or cost bound.

Planner: reuse the Lightning route already configured in `.env`. The current Ultra Critic has a prior successful NVIDIA cloud probe and may be used with an explicit disclosure that it shares a candidate and lab. NVIDIA Nemotron still appears in the Ultra and Lightning candidate slots, but a measured Nemotron-backed working feature remains necessary for the NVIDIA sponsor claim. Gemma's free catalog listing does not prove Nightshift's active provider, quota, rate limits, identity or production serving cost.

The catalog rates above are from the retained OpenRouter API snapshot `a6cff78717992be3b332c65d`, fetched at `2026-10-25T22:27:42Z`. They are **market references**, not Nightshift execution tariffs. NVIDIA's model pages list provider-specific partner prices that may differ from the catalog snapshot. [Meterless says cloud providers added to Nightshift bill through the user's own provider key](https://meterless.ai/); the Nightshift response here does not identify which provider endpoint or billing account these three routes would actually use. [NVIDIA's Developer Program endpoints are free for prototyping](https://docs.api.nvidia.com/nim/docs/product), while production serving has separate licensing/hosting terms. A zero-dollar trial endpoint cannot be extrapolated into a founder's production cost projection. The [OpenRouter terms](https://openrouter.ai/terms) and each model's terms also need review before redistributing catalog data or using the service for a public product; this source review does not claim those rights.

The selected route map is [routes.selected.json](../data/source_examples/routes.selected.json). It starts as `planned` because the reusable JSON does not embed a machine-specific discovery; `prepare_source_bundle.py --discovery` attaches the retained discovery hash and upgrades the immutable bundle mapping to `discovery_observed`. Local artifacts:

- Discovery: `data/localstack/source-discovery-gemma4-20261025.json` (112 IDs, zero completions).
- Current bundle: `data/localstack/openrouter/bundles/d85a2e103d87ba5069bf26e3` (460 catalog rows, three candidate rows, one synthetic brief). It adds exact `market.catalog_id` mapping for each row. Earlier bundles remain immutable.
- Current LocalStack/Zetaris bindings: `data/localstack/openrouter/bindings-lightning-mid-gemma-open.json`; registration report: `data/localstack/openrouter/registration-lightning-mid-gemma-open.json`. Three new tables were created without switching the current pointer.
- Current typed read: `data/localstack/openrouter/read-lightning-mid-gemma-open/report.json` passed with exact Ultra, Lightning and Gemma IDs. The no-completion projection at `data/localstack/openrouter/openrouter-projection-lightning-mid-gemma-open-retry/report.json` passed with 24 separate listed-token scenario rows and no known actual-route monthly rows. The read-only M08 gate at `/private/tmp/m08-lightning-mid-gemma-open-gate-retry.json` found all three routes advertised and registered, with `selection_matches_current: true`, but all three still lack verified tariffs and dispatch policies; zero completions were sent.
- Historical NVIDIA-only selected map: `data/source_examples/routes.nvidia-selected.json` and registered Super bundle `data/localstack/openrouter/bundles/361e255d5d2c9365a8ef7985`.
- Historical Nano candidate bundle: `data/localstack/openrouter/bundles/e973176980302f17185b6d0b` and its binding `data/localstack/openrouter/bindings-lightning-mid-nano-open.json` document the previous selection.
- Historical bundle: `data/localstack/openrouter/bundles/740f951a20335bd2570f7a4c` (Ultra, Super, Lightning, optional Nano Critic). Its binding and checks below document the earlier selection only.
- Final typed-read check: `data/localstack/openrouter/final-scenario-read-001/report.json` (four exact model IDs and a catalog-reference calculation). A later `final-roundtrip-001/report.json` also passed fixture write/readback, append, restart and duplicate handling; its fixture SourceRef stayed `unverified`. `execution_billing_verified` is false.
- Full no-completion application preview: `data/localstack/openrouter/openrouter-projection-002/report.json` and `pack.json`. It queried three pinned catalog rows through Zetaris, produced 24 OpenRouter scenario rows for two features and four growth stages, left all 24 actual-route cost rows unknown, and dispatched zero completions.

Current role configuration in `.env` selects Lightning for Planner and Ultra for Critic. The controller accepts those shared candidate routes and discloses the Critic's lack of independence. The project's `CLAUDE.md` explicitly says never to edit `.env`, so this selection does not change it. The chosen role routes still need verified execution tariffs and dispatch policies before any paid call.

Manual read check on this machine, with no model completions:

```bash
.venv/bin/python scripts/check_zetaris_sources.py --bindings data/localstack/openrouter/bindings-lightning-mid-gemma-open.json --catalog-id google/gemma-4-31b-it:free --output-dir data/localstack/openrouter/serving-read-next
```

Expected: `status: pass`, the three exact candidate Nightshift model IDs above, and `execution_billing_verified: false`. Choose a new output directory on every run.

To preview OpenRouter monthly token costs using the actual controller without any model completion:

```bash
.venv/bin/python scripts/check_openrouter_projection.py --input input_examples/example_3.json --bindings data/localstack/openrouter/bindings-lightning-mid-gemma-open.json --output-dir data/localstack/openrouter/openrouter-projection-next
```

Expected: two `openrouter_projection_tables`, 24 scenario rows (three candidates × four stages × two features), three Zetaris catalog source IDs, zero model completions and zero known actual-route monthly rows. The tool forces evaluation approval off and spend to zero. Its default Critic is Ultra; `.env` is untouched. Inspect `pack.json` for each row's tokens, monthly cost, lower-bound warning and source snapshot. Gemma's listed free scenario is not a verified Nightshift invoice. The current bindings passed this preview with no completions.

## Billing decision and remaining acceptance

The app now uses OpenRouter's pinned catalog prices for a **separate hypothetical serving projection**. Its rows carry the Zetaris source, use the same measured or estimated workload tokens, and are always labeled lower bounds. They are excluded from the actual-route operating table, switch decisions, dispatcher reservations and model-stack recommendations. [OpenRouter says token charges use posted model rates and account fees are charged on credit purchases](https://openrouter.ai/pricing); the current scenario reports the listed token subtotal, without account fees, provider-specific/conditional tariffs or proof that Nightshift's tokenization would match. It does not claim an actual invoice.

To compute the actual Nightshift bill or authorize paid evaluation, use the exact Nightshift serving provider/variant and its official billing source for each candidate, Planner and Critic. Pin the account/endpoint tariff, input/output and reasoning treatment, any fees, cache/batch/context rules, date, source URL, and content hash. Include a cited route-specific prompt/output bound and proof that `max_tokens` includes hidden reasoning. If Nightshift uses NVIDIA's free development endpoint, record that as a **prototype entitlement** only; use the OpenRouter scenario as an alternative production assumption. Do not fill `billing_profile` or mark actual-route rates verified from OpenRouter market prices alone.

The configured connection and `.env` do not expose these billing facts. Until they are confirmed, M05 remains partial and live dispatch correctly refuses to reserve a paid attempt. If the intended comparison must include a non-NVIDIA frontier lab, provision that route in Nightshift and replace the corresponding mapping before accepting M05. An intelligence index also needs a dated, licensed source if used in the shortlist; the current OpenRouter snapshot does not contain one.

Once the provider/tariff evidence is available: add cited `billing_profile` records to the selected route map, create a new immutable bundle, register it, read every model through Zetaris, run the verified-tariff stage-cost check, and repeat publication to confirm exact reuse. The [manual M05/M06 guide](12-M05-M06-Manual-Testing.md) gives the commands and negative checks. AWS publication, real measured model evidence and H-MEM remain separate later checks.
