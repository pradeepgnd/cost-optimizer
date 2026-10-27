# v4 Realignment: AI SaaS Cost Advisor

Version 4.3 | October 26, 2026 | Owner: Narin | Signed off: Narin, 27 Oct (only routes with verified billing profiles are measured, under NVIDIA's prototype entitlement) | **Authoritative.** Where this document conflicts with PRD/architecture/plan v3.4 or `06`, this document wins. Sections of v3.4 not contradicted here still apply: sponsor requirements, controller limits, trace format, sample mode rules, secrets, submission package.

**Version history.** v4.1 applied Isioma's review (precision, reasoning tokens, critic authority, lever labels, self-host inputs). v4.2 briefly put Gemma in the open-model slot. **v4.3 separates hackathon requirements from app requirements:** candidates are an app choice, made per feature and modality from any lab; the NVIDIA proof is carried by the **Planner and Critic**. The earlier text (v4.0–v4.2) had moved the NVIDIA proof onto the candidates; the reasoning is in `CLAUDE.md` and `docs/17` §1–2. The official NVIDIA rule wording is still to be quoted from the organizer's Submission Requirements §4; if it requires a Nemotron *candidate*, allow one but do not pin one. Implementation status is tracked in `docs/08-v4-Implementation-Plan.md` and `docs/17-v4-Revised-Implementation-Steps.md`, not here.

## 1. What changed and why

v3.4 drifted toward one question: *which build platform should a founder commit to, and what will the build cost?* The original idea came from the Outskill cost-optimization session (Sep 4, 2026), where every step was done by hand. It asked something broader: *what will my AI SaaS idea cost to run as it grows, frontier versus open-source models, and what stack should I choose?*

v4 restores the original question as the primary output. Build-approach cost, which is already built, becomes a secondary panel. The AVL retrospective is no longer the evaluation backbone. It stays as the founder story that opens the demo.

**Working title:** AI SaaS Cost Advisor (confirm with the team).

**One-sentence description:** "An agent that helps solo founders turn an AI SaaS idea into a costed technology plan. It runs the idea's core AI tasks on frontier and open-source models, measures real token usage and quality, and projects how monthly costs evolve from prototype to scale, including when to switch models."

## 2. The founder's input (one form)

| Field | Example | Required |
|---|---|---|
| Idea, one paragraph | "A career portal that turns a goal into a 90-day plan, interview prep and a promotion evidence bank." | yes |
| Target user | Mid-career professionals | yes |
| AI features (2–5), each with: what the AI does, one example input, interactive or background | "Generate 90-day plan · input: PM → Program Manager in 90 days · interactive" | yes |
| Uses per user per month, per feature | 4 | estimate ok |
| Expected active users at launch, and growth ambition | 500 → 50,000 | estimate ok |
| Monthly AI budget ceiling | $300 | optional |
| Quality bar | "Plans must be specific and not invent employer facts" | optional |
| Price per paying user, and paying fraction | $15, 8% | optional (revenue view) |
| Build constraints: skills, DevOps capacity, cash for the build | as in v3.4 | optional (build panel) |

Every default the agent fills in is marked `assumed` and is editable.

## 3. What the agent does (and why it is an agent, not a spreadsheet)

The objection to answer: *an architecture advisor is a spreadsheet with guessed inputs.* The agent's answer is to **measure what can be measured, and label what can't**.

1. **Recall** (H-MEM): the founder's earlier runs and confirmed assumptions for this idea, so a re-run at a later stage can show what changed.
2. **Plan** (Planner via Nightshift): turn each feature into a representative AI task with a rubric, and ask the founder when a cost-critical input is missing. **Candidate models are chosen per feature** from the routes Nightshift offers that have a cited price and cover the feature's modality (text, audio, image), from any lab. The controller applies the selection rules in §4; the Planner may also propose candidates from that filtered pool, and the controller validates each proposal.
3. **Retrieve** (Analyst via Zetaris): current prices (input, output, cache, batch, long-context thresholds) and an intelligence index for each candidate, dated and cited.
4. **Execute** (Analyst via Nightshift): run each task's example input on each candidate whose route has a verified rate source and dispatch policy. Record **measured** input, output and reasoning tokens from the API `usage` fields, plus latency. A candidate without those proofs is **projected only**: priced from the dated catalog reference with estimated tokens, quality unknown, never dispatched and never recommended.
5. **Check, then critique.** Deterministic rubric checks score each output; they and human review are the authority. The Critic (via Nightshift) only *flags*: unsupported claims, flag estimate-versus-measured token gaps, and propose one corrective action, such as a tighter output limit or moving a static instruction into a cacheable prefix.
6. **Repair** (at most one): apply the validated change and re-run the affected task once.
7. **Project** (deterministic): monthly cost per stage, per candidate, with levers applied where eligible, plus switch points.
8. **Recommend and remember**: the model stack per feature per stage, switch points with quality evidence, and risks. Store the accepted decisions in H-MEM.

User volume remains the founder's estimate and is labeled that way. Tokens and quality are measured. That is the difference from a spreadsheet, and from the session's manual method.

## 4. Candidate models

| Role | What | Purpose |
|---|---|---|
| Frontier | A top-priced closed route that covers the feature | Quality ceiling |
| Mid-tier | A cheaper closed route that covers the feature | The usual production choice |
| **Open-source (hero)** | **An open-weights route that covers the feature, from any lab** | The "frontier vs open source" question |
| Self-hosted open-source (stretch) | Same open model on rented GPU, priced by hour | Break-even against API pricing at scale |

**Selection rules (per feature).** Eligible: a Nightshift route with a reference price whose catalog entry lists the modalities the feature needs. A catalog entry with no modality data stays eligible and is labeled unknown; it is never assumed text-only. Tier: a tier curated in the route map wins; otherwise open-weights models (the catalog lists published weights) are open-source and the rest split by reference price, upper half frontier and lower half mid-tier. That price split is a proxy and is labeled as one. One candidate per tier; a route with a verified rate and dispatch policy ranks first because it can be measured, then intelligence score, market usage rank and snapshot order. A feature that no route covers gets no candidate and an evidence gap. A founder may set an optional override for the open-source slot.

The Planner and Critic routes are pinned from Nightshift's `GET /v1/models` during setup; candidate routes are discovered, not pinned. No candidate is tied to a lab or hard-coded. A candidate is executed only with a verified rate source and dispatch policy; otherwise it is projected from the dated catalog reference and labeled so. A verified free-tier rate of $0 is valid. `meterless/auto` is not a candidate.

Incremental `validation` runs may select two candidate tiers while testing the Nightshift path. The request and pack must name the selected tiers and mark the omitted tier as pending. The full founder comparison still requires all three candidates.

**No model grades the comparison.** Every candidate, frontier included, is being compared, so pass/fail comes from deterministic rubric checks plus human review. The Critic only flags issues and proposes one corrective action. The Critic's route is chosen first for the NVIDIA proof; the trace discloses when it is also a candidate's route or lab. NVIDIA award eligibility comes from the Planner and Critic running on Nemotron through Nightshift, with the resolved model identity logged per request (Submission Requirements §4; exact wording to be quoted in the R0 record). The Critic is independent whenever no candidate is a Nemotron model; otherwise the trace discloses the shared lab.

## 5. Economics (two ledgers, never summed)

### 5.1 Operating ledger by growth stage (primary)

Default stages, all editable: **Prototype 50 · Launch 500 · Traction 5,000 · Scale 50,000** active users.

```text
calls[f,s]       = users[s] × uses_per_user_month[f] × calls_per_use[f]
cost_call[f,m]   = (in_measured × p_in[m] + out_measured × p_out[m]) / 1e6
                   # out_measured = completion/output tokens, which already INCLUDE reasoning tokens
                   # (OpenAI-compatible usage). Reasoning is reported as a breakdown, never added.
                   # Pradeep confirms Nightshift's usage semantics on one real response.
# Precision: full Decimal internally; round only for display. Per-call costs show
# at least 6 decimal places (or per 1,000 calls); monthly totals to cents.
monthly[f,m,s]   = calls[f,s] × cost_call[f,m] × (1 + retry_rate)
```

**Levers**, each applied only when eligible and shown separately, never silently netted. Caching and batch are **projections for the founder's production setup**, not measured in our runs (whether they pass through Nightshift is unknown). Rules are per provider: cache minimums, TTLs and long-context thresholds differ.

| Lever | Eligible when | Effect |
|---|---|---|
| Prompt caching | static prefix ≥ provider minimum (~1,024 tokens) and repeated within the cache TTL | cached share at cache-read rate; writes at write rate |
| Batch API | feature marked background, provider offers batch | 50% on input and output |
| Output cap | critic finds output longer than the rubric needs | measured re-run with the cap |
| Long-context cliff | measured input above the provider threshold | **warning**: surcharge applies to the whole request |

**Switch point:** the first stage at which moving a feature from frontier to mid or open-source is projected to cost at least the founder's threshold (default $100/month) less **and** the cheaper model passed every critical rubric check. Reported as: "From Traction (5,000 users), plan generation on the open-weights model is projected to cost ~$X/month less; measured quality 5/6 checks vs 6/6 on frontier. Test on your own data before switching."

**Self-host break-even (stretch, cut first):** needs three inputs, not one: GPU $/hour (Isioma, AWS), the pinned open-weights model's served throughput in tokens/second on that GPU (cited benchmark), and a utilization assumption. Without a cited throughput figure, this item is not shown.

Unknown prices stay unknown. Revenue present → contribution and margin per stage; absent → cost-only.

### 5.2 Build ledger (secondary panel, already implemented)

The four build approaches and the rework multiplier from v3.4, unchanged. Shown under "Alternative technology stack: how to build it".

## 6. Output (the decision pack)

1. Recommended model stack per feature, per stage, with reasons and an alternate.
2. Cost-evolution table and chart: monthly AI cost by stage for each candidate, with levers.
3. Switch points with quality evidence.
4. Measured versus estimated tokens per feature (the 4/3 rule against `usage`), showing why measurement matters.
5. Build panel: approaches, build ranges, checkpoints.
6. Risks, evidence gaps and limitations; disclaimer.
7. Trace: every Zetaris query, every Nightshift request with its model, every H-MEM operation.

## 7. Evaluation

- **Agent behaviour:** retrieves missing evidence, runs tasks, critiques, one repair, stops within limits, remembers across runs.
- **Measurement validity:** measured tokens come only from API `usage` fields; estimate-versus-measured gaps are reported, never hidden.
- **Quality comparison:** each task has 3–5 deterministic rubric checks plus human review. Small samples, stated as such. No cross-model quality claim beyond the measured tasks.
- **Founder impact:** Narin runs his own ideas (self-evaluation, labeled as such), **plus one or two outside founders**, e.g. from the Outskill cohort, who run one idea each and record before/after decisions with consent. Negative results are kept.

**Call budget (M04 clarification):** at most **30 total inference dispatches**, including Planner, candidates, Critic, the single repair and all transport retries; the approved spend cap stays at most $25. There is one logical Planner call, one logical Critic call and at most one logical repair; retries of these operations count toward both the total dispatch cap and the global limit of two retries. Reserve one repair slot and two retry slots before selecting the sample count. Four executable features can use two samples (`24 + 1 Planner + 1 Critic + 1 repair + 2 retries = 29`); five use one sample. The explicit `validation` profile always uses one sample per executable pair, while `production` uses two when these slots fit. Every paid attempt needs a cited route-specific prompt/output bound and verified billing rates; unknown bounds stop execution. Ambiguous dispatched outcomes are held and not replayed. Projected-only candidates make no dispatch and do not count. Diagnostic completions use the same durable dispatcher with a separate explicit allowance (at most $1, default $0). Actual cost depends on the verified route tariffs and measured usage; estimates alone do not establish a spend bound.

## 8. Sponsor mapping (unchanged requirements, sharper roles)

| Sponsor | Role in v4 |
|---|---|
| Zetaris | Data layer: price snapshots, intelligence index, founder ideas, measured runs (evaluation evidence). Every price the agent uses comes from a Zetaris query. |
| Meterless H-MEM | The idea's memory: confirmed assumptions and earlier stage decisions, recalled on a re-run so the agent reports what changed as the SaaS matures. |
| Meterless Nightshift | The router for every model call: every candidate and both role models go through it, which is what makes side-by-side measurement possible. |
| NVIDIA Nemotron | Planner and Critic run on Nemotron; corroborated resolved identity per request supplies the NVIDIA-specific evidence. Candidates are not tied to a lab. |
| Cursor | Used by Shrie for UI and Zetaris work, truthfully described. |

## 9. Hosting: why Zetaris runs locally, and what Vercel can and can't do

- **Zetaris is required** as the data layer by the Official Rules. Its local edition runs in Docker and needs ~8 GB of RAM. It cannot run on Vercel.
- **Nightshift is a desktop runtime.** The app must reach it, so live mode runs on the machine where Nightshift runs.
- **No hosted deployment is required for submission.** The judged artifacts are the public repo (runnable from a clean clone, with sample mode for judges without sponsor accounts), the video and the deck.
- **Vercel** hosts web front ends and short serverless functions. It doesn't run Streamlit, Docker or a desktop runtime. A hosted **sample-mode** demo (no sponsors, no secrets) is possible as a stretch, more easily on Streamlit Community Cloud than on Vercel.
- **After the hackathon:** a production version would use Zetaris Cloud or Zetaris on AWS, a hosted model gateway, and a Vercel or AWS front end. That's an architecture decision for later, not this week.

## 10. What is shelved

`scripts/compare_retrospective.py` (kept in the repo, unused), sealed actuals, the leakage review, and dev-spec tasks T1–T6. `06` becomes historical design context. The AVL story moves to the demo opening and the "problem" slide.

## 11. Roles (40-hour envelope unchanged)

| Member | Strength | v4 responsibility | Acceptance |
|---|---|---|---|
| **Narin** | Product, integration owner | Realignment in Claude Code (contracts, economics, controller); 2–3 founder ideas as example inputs; demo narration and story; submission | Sample mode produces a stage-cost pack for 3 ideas; video recorded; submission accepted |
| **Pradeep** | Backend | Nightshift live adapter: route discovery, pin the Planner and Critic Nemotron routes, `usage` capture incl. reasoning tokens, model identity per request. H-MEM bridge (`bridge.mjs`, pinned revision, passing test) | One real Planner and one real Critic request logged with resolved Nemotron model; executed candidates logged the same way; `test_hmem_engine.py` green |
| **Meena** | Backend | Zetaris live adapter: source registration from S3, fixed query templates, read path for prices and ideas, writeback of measured runs. Monday clean-clone rehearsal | `SELECT 1` and real price rows through the app; rehearsal passes on a second machine |
| **Shrie** | Front end, already running Zetaris | Streamlit UI: the founder form (modeled on the 180 Lift Hub layout), cost-evolution table and chart, switch points, evidence timeline. Candidate integration host, since Zetaris already runs there | Form → pack → views, live and sample, same core |
| **Isioma** | AWS | S3 bucket and IAM for Zetaris registration (bucket credentials Zetaris-side only); price snapshots for the candidates (input, output, cache, batch, thresholds) plus intelligence index, dated and cited; AWS GPU hourly rates for the self-host break-even; optional hosted sample-mode demo | `data/README.md` lists every source with URL, date, licence; registration script works from S3 |
| **Meena + Narin** | — | Deck (8 slides) and sponsor explanation | All eight points covered; claims match traces |

**Integration host:** whichever machine passes `scripts\preflight_windows.ps1` and has Zetaris + Nightshift both running. Shrie's machine is the first candidate. Two other installs remain fallbacks, not parallel efforts.

**Coding tools:** Claude Code, Cursor and Grok are all acceptable for writing code. App inference goes only through Nightshift. `CLAUDE.md` rules apply to everyone; Cursor users copy them into `.cursor/rules/project.mdc` so their tool reads them too.

## 12. Schedule from here (America/Chicago)

| When | Exit evidence |
|---|---|
| Sun midday–evening | v4 sample mode working (Narin); price snapshots v1 (Isioma); Nightshift routes pinned (Pradeep); Zetaris `SELECT 1` body shared (Shrie/Meena) |
| **Sun 6 p.m. gate** | One real Planner and one real Critic request on Nemotron through Nightshift plus one real candidate request; one real Zetaris price query; H-MEM save/restart/recall. If any fails: cut the self-host stretch, then the hosted demo, never sponsor proof. *Met on Mon 26 Oct by the bounded live pack in the release ledger.* |
| Mon | Live end-to-end on 3 ideas; UI wired; clean-clone rehearsal; video draft |
| Tue by noon | Final recording, deck, public repo, submission. Submission closes Tue 27 Oct, 23:45 UTC (6:45 p.m. Chicago) |
