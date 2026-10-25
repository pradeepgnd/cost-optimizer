# v4 Realignment: AI SaaS Cost Advisor

Version 4.0 | October 25, 2026 | Owner: Narin | **Authoritative.** Where this document conflicts with PRD/architecture/plan v3.4 or `06`, this document wins. Sections of v3.4 not contradicted here still apply: sponsor requirements, controller limits, trace format, sample mode rules, secrets, submission package.

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
2. **Plan** (Planner via Nightshift): turn each feature into a representative AI task with a rubric, and choose the candidate models. Ask the founder when a cost-critical input is missing.
3. **Retrieve** (Analyst via Zetaris): current prices (input, output, cache, batch, long-context thresholds) and an intelligence index for each candidate, dated and cited.
4. **Execute** (Analyst via Nightshift): run each task's example input on each candidate. Record **measured** input, output and reasoning tokens from the API `usage` fields, plus latency.
5. **Critique** (Critic via Nightshift): check each output against its rubric, flag unsupported claims, flag estimate-versus-measured token gaps, and propose one corrective action, such as a tighter output limit or moving a static instruction into a cacheable prefix.
6. **Repair** (at most one): apply the validated change and re-run the affected task once.
7. **Project** (deterministic): monthly cost per stage, per candidate, with levers applied where eligible, plus switch points.
8. **Recommend and remember**: the model stack per feature per stage, switch points with quality evidence, and risks. Store the accepted decisions in H-MEM.

User volume remains the founder's estimate and is labeled that way. Tokens and quality are measured. That is the difference from a spreadsheet, and from the session's manual method.

## 4. Candidate models

| Role | What | Purpose |
|---|---|---|
| Frontier | Best general route available in Nightshift | Quality ceiling |
| Mid-tier | A cheaper route from a frontier lab | The usual production choice |
| **Open-source (hero)** | **NVIDIA Nemotron via Nightshift** | The "frontier vs open source" question; NVIDIA award feature |
| Self-hosted open-source (stretch) | Same open model on rented GPU, priced by hour | Break-even against API pricing at scale |

Exact route IDs are pinned from Nightshift's `GET /v1/models` during setup. `meterless/auto` is not a candidate.

**The critic is not Nemotron.** Nemotron is now a candidate, and a model should not grade its own outputs. The critic uses the frontier route; human review stays authoritative. NVIDIA award eligibility comes from Nemotron handling a working feature with its model identity logged per request (Submission Requirements §4).

## 5. Economics (two ledgers, never summed)

### 5.1 Operating ledger by growth stage (primary)

Default stages, all editable: **Prototype 50 · Launch 500 · Traction 5,000 · Scale 50,000** active users.

```text
calls[f,s]       = users[s] × uses_per_user_month[f] × calls_per_use[f]
cost_call[f,m]   = (in_measured × p_in[m] + out_measured × p_out[m] + reasoning × p_out[m]) / 1e6
monthly[f,m,s]   = calls[f,s] × cost_call[f,m] × (1 + retry_rate)
```

**Levers**, each applied only when eligible and shown separately, never silently netted:

| Lever | Eligible when | Effect |
|---|---|---|
| Prompt caching | static prefix ≥ provider minimum (~1,024 tokens) and repeated within the cache TTL | cached share at cache-read rate; writes at write rate |
| Batch API | feature marked background, provider offers batch | 50% on input and output |
| Output cap | critic finds output longer than the rubric needs | measured re-run with the cap |
| Long-context cliff | measured input above the provider threshold | **warning**: surcharge applies to the whole request |

**Switch point:** the first stage at which moving a feature from frontier to mid or open-source saves at least the founder's threshold (default $100/month) **and** the cheaper model passed the same rubric checks. Reported as: "From Traction (5,000 users), plan generation on Nemotron saves ~$X/month; measured quality 5/6 checks vs 6/6 on frontier. Test on your own data before switching."

**Self-host break-even (stretch):** GPU $/hour × 730 against monthly API cost for the open model; reported as the user count at which renting a GPU becomes cheaper, plus the utilization assumption.

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
- **Quality comparison:** each task has 3–5 deterministic rubric checks plus human review. Small samples, stated as such. No "Nemotron is as good as frontier" claim beyond the measured tasks.
- **Founder impact:** Narin runs 2–3 of his own future ideas through the tool and records whether the output changed what he would build or which model he'd start with. Negative results are kept.

**Call budget:** 3 features × 3 candidates × 2 samples = 18 executions + 1 planning + 1 critique + ≤1 revision + ≤6 repair re-runs = ≤27. The cap rises from 23 to 30; the spend cap stays $25. At spec-sized outputs this is cents per run.

## 8. Sponsor mapping (unchanged requirements, sharper roles)

| Sponsor | Role in v4 |
|---|---|
| Zetaris | Data layer: price snapshots, intelligence index, founder ideas, measured runs (evaluation evidence). Every price the agent uses comes from a Zetaris query. |
| Meterless H-MEM | The idea's memory: confirmed assumptions and earlier stage decisions, recalled on a re-run so the agent reports what changed as the SaaS matures. |
| Meterless Nightshift | The router for every model call: frontier, mid and Nemotron all go through it, which is what makes side-by-side measurement possible. |
| NVIDIA Nemotron | The open-source contender in every comparison; its measured cost and quality drive the switch points. |
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
| **Pradeep** | Backend | Nightshift live adapter: route discovery, pin frontier/mid/Nemotron IDs, `usage` capture incl. reasoning tokens, model identity per request. H-MEM bridge (`bridge.mjs`, pinned revision, passing test) | One real request per candidate logged with resolved model; `test_hmem_engine.py` green |
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
| **Sun 6 p.m. gate** | One real Nemotron request through Nightshift; one real Zetaris price query; H-MEM save/restart/recall. If any fails: cut the self-host stretch, then the hosted demo, never sponsor proof |
| Mon | Live end-to-end on 3 ideas; UI wired; clean-clone rehearsal; video draft |
| Tue by noon | Final recording, deck, public repo, submission |
