# Data

All runtime data is read through **Zetaris** (live) or from `data/sample/` (SAMPLE_MODE). Registered files live in the team's Amazon S3 bucket; Zetaris reads them from there. Bucket credentials are Zetaris-side configuration and never appear in this repository.

| Source set | Live source name | Sample file | Status | Notes |
|---|---|---|---|---|
| founder_briefs | `oah.founder_briefs` | `founder_briefs.json` | reconstructed | The AVL brief is reconstructed from pre-build artifacts by the founder, leakage-reviewed by a teammate (06 §4). Two additional briefs are synthetic. |
| pricing_snapshots | `oah.pricing_snapshots_*` | `pricing_snapshots.json` | **PLACEHOLDER / unverified** | To be replaced by dated, URL-cited public pricing (W04). Unknown rates stay unknown. |
| dev_task_cases | `oah.dev_task_cases` | `dev_task_cases.json` | derived | 8 spec-level tasks; 3 development, 5 holdout. Holdout rows are sealed until freeze. |
| evaluation_evidence | `oah.evaluation_evidence` | written at run time | generated | Case results and critiques; live writeback via the supported registration path. |
| retrospective_actuals | `oah_sealed.retrospective_actuals` | `retrospective_actuals_SYNTHETIC.json` | **synthetic in repo** | The founder's real aggregate exists only in the live sealed source and the deck, with the founder's consent. The repository never contains it. |

Regenerate sample outputs: `scripts/regen_examples.sh`. Source URL, licence, subset and hash for each live registration are recorded here by Isoma as they are registered. No data predates the build window (22 Oct 2026, 00:00 UTC).
