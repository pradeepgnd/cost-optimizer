## What was unique about our sponsor use

**We use the sponsors' tools to measure what AI costs, so the same tools that run the agent also produce the evidence.** The agent's answer is a monthly cost forecast. Every number in it can be traced back to a Zetaris query or a Nightshift request.

**Zetaris reads the prices and stores the evidence.** Model price tables (an OpenRouter catalog snapshot plus our role-route pricing profiles) are registered with Zetaris as S3-backed sources. Each run reads typed rows from a pinned snapshot, and every row is checked against its recorded hash. Results go the other way too: measured runs are written back to Zetaris by a separate publisher process, then read back to confirm they arrived. If that write fails, the records wait in a local outbox and can be replayed with `scripts/retry_evidence.py`. Each Zetaris query ID appears in the run trace.

**Meterless Nightshift handles every model call.** That covers the Planner, every candidate model, the Critic and the one allowed repair. Before any paid call, the agent lists Nightshift's routes (`GET /v1/models`) and picks candidates for each feature from any lab. Every request first passes a spend check: money and a slot are reserved, then reconciled against the measured usage. Each request logs both the model we asked for and the model that actually answered. While testing on 26 October we found a problem. With a shared `meterless-scope`, Nightshift's built-in memory put an earlier answer into similar prompts. Two different models returned identical text, and input tokens were inflated (1,542 against 751). We now give every request its own scope (`eval-<random>`), re-measured Examples 1 and 3, and threw out the earlier numbers. For a tool whose whole job is accurate token counts, finding that mattered.

**Meterless H-MEM is the idea's memory.** We use the unmodified H-MEM reference engine (pinned revision `1742dec`, Apache-2.0) through a Node bridge. At the start of a run it recalls confirmed assumptions for the idea. At the end it saves accepted decisions. A self-test checks save, recall after a restart, isolation between projects, and the audit ledger. *Not yet shown:* a saved memory changing a later run's decision. That is our next step.

**NVIDIA Nemotron runs the Planner and the Critic.** Both go through Nightshift: the Planner on `nvidia/nemotron-3.5-lightning-30b-a3b` and the Critic on `nvidia/nemotron-3-ultra-550b-a55b`. Both are also measured as candidate models. The Critic only flags issues and proposes one action, which the controller validates. Pass/fail is decided by deterministic checks and human review, never by a model. We turned thinking off for these routes because reasoning tokens count toward the output cap. With it on, the Planner returned empty answers and the Critic hit the cap.

---

### Sponsor table row (draft)

| Sponsor | Role in this project | Proof |
|---|---|---|
| Cursor | Used during development by [team member(s)] for [specific work, e.g. which Streamlit UI views / which Zetaris adapter or script, team to confirm]. Example: [describe one concrete task Cursor did and what came of it]. | [file paths or commit hashes, e.g. Cursor Agent commit `42ccec6` "Add product design system doc for Streamlit UI" on branch `shrie-UI-ideas`, if you merge it; add others] |

### AI coding tools note (draft)

> We also used **Claude Code** during development. The project rules it followed are in `CLAUDE.md`, and many commits carry a `Co-Authored-By: Claude` trailer. Every generated change was reviewed by the team and is covered by the offline test suite (`python -m pytest -q`).
