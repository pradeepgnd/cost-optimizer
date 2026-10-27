# Live runs: proof

These are real **LIVE** runs, not sample output. Every model call went through Meterless Nightshift, prices were read from Zetaris, and memory used the Meterless H-MEM engine. Each folder holds the exact `request.json`, the resulting `pack.json` (the DecisionPack) and the full `trace.jsonl`.

- **When:** 2026-10-27, 02:37 to 02:41 UTC, one after another.
- **Code:** application code identical to `main` at `1bdc9c7`; Python 3.12.12; `python run.py --input request.json --output pack.json` with `SAMPLE_MODE=false`.
- **Setup:** Zetaris and LocalStack in Docker; Nightshift with the NVIDIA and OpenRouter providers (111 routes listed); the evidence publisher running. `python scripts/smoke_live.py` passed for Zetaris (`SELECT 1`, 37 model rows), Nightshift discovery and the H-MEM self-test just before.
- **Spend:** $0 on every run. The NVIDIA key is a free Developer Program key, and only the two Nemotron routes have a verified rate, so only they are executed. Every other candidate is **projected only** from its Zetaris reference price and is never run.
- **Approval and caps:** `evaluation_approved: true`, `max_spend_usd: 0.50`, production sampling (two samples per model and feature).

Nothing here was edited except replacing the local trace path inside each pack with its path in this folder.

## Runs

| Folder | Run ID | Status | Model requests | Spend (USD) | Zetaris queries | Evidence written back and read back | Unpublished | H-MEM recall |
|---|---|---|---|---|---|---|---|---|
| `example_1` | `live-ex1-20261027T023748Z` | complete | 10 | 0 | 15 | 9 | 0 | 0 memories |
| `example_2` | `live-ex2-20261027T023748Z` | complete | 14 | 0 | 17 | 13 | 0 | 0 memories |
| `example_3` | `live-ex3-20261027T023748Z` | complete | 10 | 0 | 13 | 9 | 0 | 0 memories |
| `example_3_recall` | `live-ex3-recall-20261027T023748Z` | complete | 10 | 0 | 13 | 9 | 0 | 2 memories |

"Evidence written back" counts the `evaluation_evidence` references in each pack: every measured sample was written to Zetaris by the publisher, read back, and checked against its content hash. The empty outbox (`unpublished_evidence_ids`) confirms none is waiting.

## NVIDIA Nemotron runs the Planner and the Critic

Requested and resolved model match on every request; the ID is the provider's request ID from Nightshift.

| Run | Role | Requested | Resolved | Provider request ID | Tokens in / out |
|---|---|---|---|---|---|
| `example_1` | Planner | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning-30b-a3b` | `chatcmpl-3d11ae7d-b9b6-4f15-acb6-87896415817f` | 353 / 166 |
| `example_1` | Critic | `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia/nemotron-3-ultra-550b-a55b` | `chatcmpl-b603cff9-8eb1-41e1-84f0-af10673d7e1d` | 1584 / 252 |
| `example_2` | Planner | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning-30b-a3b` | `chatcmpl-360fa5b8-1c72-4d72-9d19-0c0aaf8553f9` | 332 / 390 |
| `example_2` | Critic | `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia/nemotron-3-ultra-550b-a55b` | `chatcmpl-915d9e36-cebc-45ce-ad56-9b56bd2afdc7` | 2204 / 414 |
| `example_3` | Planner | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning-30b-a3b` | `chatcmpl-7637525c-6b87-4c93-bf6f-31aae6dba39f` | 244 / 346 |
| `example_3` | Critic | `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia/nemotron-3-ultra-550b-a55b` | `chatcmpl-59bed220-0ae8-4192-ad7c-e1ce742acb35` | 1031 / 100 |
| `example_3_recall` | Planner | `nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning-30b-a3b` | `chatcmpl-40f2b937-e8d8-4229-a5bf-f51ce849a8f3` | 244 / 316 |
| `example_3_recall` | Critic | `nvidia/nemotron-3-ultra-550b-a55b` | `nvidia/nemotron-3-ultra-550b-a55b` | `chatcmpl-49c143ca-b824-4cff-8aec-74d1f3df93a0` | 1036 / 176 |

The Ultra and Lightning routes are also candidates, so the Critic shares a lab with two of the models it reviews. Each trace discloses this (`critic_shares_candidate_route`). The Critic only flags; deterministic checks and human review decide quality.

## Measured tokens against the estimate

Mean of two samples on the founder's own example input. The estimate uses the 4/3 tokens-per-word rule on the expected output length.

| Run | Feature | Model | Estimated output | Measured in / out |
|---|---|---|---|---|
| `example_1` | A2_next_target_and_feedback | `nvidia/nemotron-3-ultra-550b-a55b` | 54 | 142 / 15 |
| `example_1` | A2_next_target_and_feedback | `nvidia/nemotron-3.5-lightning-30b-a3b` | 54 | 142 / 15 |
| `example_1` | A4_weekly_progress_summary | `nvidia/nemotron-3-ultra-550b-a55b` | 400 | 751 / 768.5 |
| `example_1` | A4_weekly_progress_summary | `nvidia/nemotron-3.5-lightning-30b-a3b` | 400 | 751 / 446.5 |
| `example_2` | B1_parse_request_to_quote | `nvidia/nemotron-3-ultra-550b-a55b` | 40 | 172 / 33.5 |
| `example_2` | B1_parse_request_to_quote | `nvidia/nemotron-3.5-lightning-30b-a3b` | 40 | 172 / 34 |
| `example_2` | B2_explain_flagged_transaction | `nvidia/nemotron-3-ultra-550b-a55b` | 160 | 407 / 327.5 |
| `example_2` | B2_explain_flagged_transaction | `nvidia/nemotron-3.5-lightning-30b-a3b` | 160 | 407 / 304.5 |
| `example_2` | B3_dispute_or_receipt_summary | `nvidia/nemotron-3-ultra-550b-a55b` | 107 | 433 / 239.5 |
| `example_2` | B3_dispute_or_receipt_summary | `nvidia/nemotron-3.5-lightning-30b-a3b` | 107 | 433 / 261 |
| `example_3` | summarize_notes | `nvidia/nemotron-3-ultra-550b-a55b` | 334 | 141 / 148.5 |
| `example_3` | summarize_notes | `nvidia/nemotron-3.5-lightning-30b-a3b` | 334 | 141 / 128.5 |
| `example_3` | weekly_digest | `nvidia/nemotron-3-ultra-550b-a55b` | 400 | 86 / 34.5 |
| `example_3` | weekly_digest | `nvidia/nemotron-3.5-lightning-30b-a3b` | 400 | 86 / 46.5 |
| `example_3_recall` | summarize_notes | `nvidia/nemotron-3-ultra-550b-a55b` | 334 | 141 / 151.5 |
| `example_3_recall` | summarize_notes | `nvidia/nemotron-3.5-lightning-30b-a3b` | 334 | 141 / 128.5 |
| `example_3_recall` | weekly_digest | `nvidia/nemotron-3-ultra-550b-a55b` | 400 | 86 / 31.5 |
| `example_3_recall` | weekly_digest | `nvidia/nemotron-3.5-lightning-30b-a3b` | 400 | 86 / 49 |

The audio feature in Example 1 (`A1_transcribe_attempt`) is priced, not executed, because chat completions cannot carry audio.

## Critic flags

| Run | Kind | Claim |
|---|---|---|
| `example_1` | token_gap | Estimated output tokens (400) vs measured (768.5) differ materially. |
| `example_1` | token_gap | Estimated output tokens (400) vs measured (446.5) differ materially. |
| `example_2` | token_gap | estimated_output_tokens 160 vs measured_output_tokens 327.5 |
| `example_2` | token_gap | estimated_output_tokens 160 vs measured_output_tokens 304.5 |
| `example_2` | token_gap | estimated_output_tokens 107 vs measured_output_tokens 239.5 |
| `example_2` | token_gap | estimated_output_tokens 107 vs measured_output_tokens 261 |
| `example_3` | unsupported_claim | Action item with owner 'Team' and task 'Revisit pricing page copy' |
| `example_3_recall` | unsupported_claim | Action item with owner 'Team' and task 'Revisit pricing page copy' |
| `example_3_recall` | unsupported_claim | Group header '**Thu**' with item 'mockups' |

## H-MEM changes the second run

`example_3` states a budget of 40 USD, a price of 15 USD per paying user and a paying fraction of 0.08. `example_3_recall` is the same idea with those three fields blank, sharing the same memory store. Its trace shows `hmem_recall` with 2 memories, then `hmem_apply` filling all three fields from run `live-ex3-20261027T023748Z`, each labelled as assumed and with its source run. Its stage totals therefore show revenue (60 USD at 50 users up to 60,000 USD at 50,000 users), AI margin and budget fit, the same as the first run. Without memory those columns are empty.

## What these runs do not show

- No candidate is quality-qualified: human review is pending, so no model is recommended (`recommended` totals stay unknown).
- Only Nemotron routes are measured; candidates from other labs are projected from reference prices.
- One idea per run, two samples per pair: the token numbers are indicative, not statistics.
- Windows and a second machine were not used for these live runs.
