# M05 serving and billing selection

Checked October 25, 2026. This selection uses the project's configured Nightshift connection without copying or changing `.env`. `GET /v1/models` advertised 75 routes and returned only ID, owner and creation metadata for the selected routes; it did not return prices, active serving endpoints or billable usage rules. No completion was sent.

| Role | Nightshift serving route | OpenRouter catalog ID | Catalog reference input/output, USD per 1M tokens |
|---|---|---|---|
| Frontier | `nvidia/nemotron-3-ultra-550b-a55b` | Same ID | 0.60 / 2.40 |
| Mid-tier | `nvidia/nemotron-3-super-120b-a12b` | Same ID | 0.30 / 2.40 |
| Required open model | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning` | 0.07 / 0.20 |

Ultra is [identified by NVIDIA as a frontier model](https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b/modelcard); Super is the smaller [120B model](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b) from the same lab; [Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) is the required 30B/3B-active Nemotron route. This available set gives a size/cost comparison within the NVIDIA open-model family. It does not demonstrate a closed frontier model versus an open model, which was the original product framing. None has yet been executed on this Nightshift instance, so discovery proves advertised route IDs only.

Planner: reuse the Lightning route already configured in `.env`. Critic: select the advertised `local-runtime/qwen3.8-27b` route (`qwen/qwen3.8-27b` is its catalog comparison ID). It is a different route and lab from the three candidates. Its local readiness, suitability for the flags-only critique, hardware cost and dispatch bounds remain unverified. Its OpenRouter catalog price is not the cost of a local Nightshift request.

The catalog rates above are from the retained OpenRouter API snapshot `a6cff78717992be3b332c65d`, fetched at `2026-10-25T22:27:42Z`. They are **market references**, not Nightshift execution tariffs. NVIDIA's model pages list provider-specific partner prices that may differ from the catalog snapshot. [Meterless says cloud providers added to Nightshift bill through the user's own provider key](https://meterless.ai/); the Nightshift response here does not identify which provider endpoint or billing account these three routes would actually use. [NVIDIA's Developer Program endpoints are free for prototyping](https://docs.api.nvidia.com/nim/docs/product), while production serving has separate licensing/hosting terms. A zero-dollar trial endpoint cannot be extrapolated into a founder's production cost projection. The [OpenRouter terms](https://openrouter.ai/terms) and each model's terms also need review before redistributing catalog data or using the service for a public product; this source review does not claim those rights.

The selected route map is [routes.nvidia-selected.json](../data/source_examples/routes.nvidia-selected.json). It starts as `planned` because the reusable JSON does not embed a machine-specific discovery; `prepare_source_bundle.py --discovery` attaches the retained discovery hash and upgrades the immutable bundle mapping to `discovery_observed`. Local artifacts:

- Discovery: `data/localstack/source-discovery-m05-20261025.json` (75 IDs, zero completions).
- Bundle: `data/localstack/openrouter/bundles/8c467013304eccab368b2455` (460 catalog rows, three candidate rows, one Critic row, one synthetic brief). The earlier three-candidate bundle `88181fa032d26720a9ab244c` remains immutable.
- LocalStack/Zetaris bindings: `data/localstack/openrouter/bindings-serving-selected.json`; registration and exact-reuse reports: `data/localstack/openrouter/registration-serving-result.json` and `registration-serving-repeat.json`.
- Typed read check: `data/localstack/openrouter/serving-read-001/report.json` (four exact model IDs, source hashes, and a catalog-reference calculation). `execution_billing_verified` is false.

Current role configuration in `.env` selects Lightning for Planner and Ultra for Critic. With Ultra selected as the frontier candidate, the controller rejects the current Critic route because an advertised noncandidate route exists. `METERLESS_CRITIC_MODEL` must be changed to `local-runtime/qwen3.8-27b` (or another independently verified noncandidate route) before an application run. The project's `CLAUDE.md` explicitly says never to edit `.env`, so this selection does not change it. Both role routes need verified execution tariffs and dispatch policies before any paid call.

Manual read check on this machine, with no model completions:

```bash
.venv/bin/python scripts/check_zetaris_sources.py --bindings data/localstack/openrouter/bindings-serving-selected.json --catalog-id nvidia/nemotron-3.5-lightning --output-dir data/localstack/openrouter/serving-read-002
```

Expected: `status: pass`, the four exact Nightshift model IDs above, and `execution_billing_verified: false`. Choose a new output directory on every run.

## Billing decision and remaining acceptance

Use the exact Nightshift serving provider/variant and its official billing source for each candidate, Planner and Critic. Pin the account/endpoint tariff, input/output and reasoning treatment, any fees, cache/batch/context rules, date, source URL, and content hash. Include a cited route-specific prompt/output bound and proof that `max_tokens` includes hidden reasoning. If Nightshift uses NVIDIA's free development endpoint, record that as a **prototype entitlement** only; choose and cite a production serving provider separately for monthly projections. Do not fill `billing_profile` or mark rates verified from OpenRouter market prices alone.

The configured connection and `.env` do not expose these billing facts. Until they are confirmed, M05 remains partial and live dispatch correctly refuses to reserve a paid attempt. If the intended comparison must include a non-NVIDIA frontier lab, provision that route in Nightshift and replace the corresponding mapping before accepting M05. An intelligence index also needs a dated, licensed source if used in the shortlist; the current OpenRouter snapshot does not contain one.

Once the provider/tariff evidence is available: add cited `billing_profile` records to the selected route map, create a new immutable bundle, register it, read every model through Zetaris, run the verified-tariff stage-cost check, and repeat publication to confirm exact reuse. The [manual M05/M06 guide](12-M05-M06-Manual-Testing.md) gives the commands and negative checks. AWS publication, real measured model evidence and H-MEM remain separate later checks.
