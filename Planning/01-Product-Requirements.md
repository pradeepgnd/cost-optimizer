# PRD: LLM Cost Intelligence decision agent

Version 3.3 | October 23, 2026 (late evening) | Product/integration/deployment owner: Narin

Authoritative project context and source index: [Changes and reading guide](00-Changes-and-Reading-Guide.md). Version 3.3 aligns v3.2 to the Open Agent Hackathon 2026 organizer documents (Official Rules, Submission Requirements, Submission Form Preview, Technical Execution Guide). Change log: [Guideline alignment review](05-Guideline-Alignment-Review.md).

**Source precedence for this project:** Official Rules on the event page > Submission Requirements > Submission Form Preview and Technical Execution Guide (recommended practice) > sponsor setup guide. The three G42 Agentathon templates in the project folder (`metadata-json-template.md`, `demo-script-template.md`, `readme-template.md`) belong to a different event. Nothing in them is binding here: no Compass, no port 8000 mandate, no `metadata.json`, no use-case ID, no 15-minute limit, no 2–3 minute video length. They remain useful only as examples of README/trace layout.

**Submission identity (draft for the HackOS form; one sentence, then one paragraph):**

- Project name: *LLM Cost Intelligence* (working title; confirm tonight).
- One-sentence description: "An agent that helps a founder choose which AI model and workflow to prototype by joining their constraints, verified pricing, approved FAQ knowledge and executed task evidence into one sourced, cost-modeled recommendation."
- Track: The Agent That Can Explain Why. Primary contact: Narin.

## 1. Product and user outcome

**Help a founder decide which AI model and workflow to prototype, what it could cost at scale, and what task evidence supports that choice.**

Primary users are a nontechnical founder with an idea and a technical founder building a prototype. Input is a product description, expected usage, structured assumptions, and optional prompt examples. The first supported task is a support assistant answering from an approved FAQ. This task is the evaluation sandbox; the product being built is the architecture decision agent, not a generic customer-support chatbot.

The agent performs useful work: identifies missing constraints, retrieves source evidence, builds two feasible prototype configurations, runs a bounded comparison, critiques the results, takes one corrective action when justified, and creates a founder-ready decision pack. It must be able to conclude that evidence is insufficient or neither candidate passes.

Deliverable to the founder:

- Named model/workflow candidate, reasons, assumptions, and an alternate option.
- Expected monthly cost, unit cost, and conditional contribution margin.
- A prototype recipe: workflow steps, configuration settings, FAQ/context strategy, escalation behavior, and next implementation/test steps. This is an exported specification, not automatic deployment.
- Task results, source references, observed failures, and what changed after critique.

## 2. Fixed constraints

Registered team: Narin, Pradeep, Meena, Isoma, Shrie. Forty team-hours remain starting October 24. Narin owns integration/deployment. Total hosting/API budget is $100. Exact remaining availability within those days still needs scheduling; there is no extra full-time engineering capacity.

Zetaris and Nightshift accounts are not opened as of the October 23 evening update. First build work is sponsor onboarding and a functioning vertical slice. No credentials, deployed system, engine integration, evaluation dataset, or results are presumed to exist.

Submission deadline in G4/G8: October 27, 23:45 UTC, or **October 27, 6:45 p.m. Chicago** (CDT; US clocks do not change until November 1). Judging opens October 28 UTC; results November 6, 16:00 UTC. Late submissions are not evaluated and nothing can be fixed after close.

Build window opened **October 22, 00:00 UTC**. Anything committed, written or prepared before that moment — product code, a prior Streamlit prototype, curated FAQ/rate data, planning documents — must be declared as a pre-existing component in the submission form or it is ineligible. Sponsor-published starter code (the Meterless H-MEM starter) is open source and does not need declaring, but the README names it and pins its revision.

Team rules that cannot be undone: one HackOS account per person (duplicates disqualify the whole team); each person on exactly one team; the roster locks when the first submission is created; cash prizes split equally unless a different split is submitted in writing; GitHub usernames on the form should match repository contributors. Collect every member's HackOS email and GitHub username tonight, and have each member make at least one real commit.

Responsible-AI expectation (Rules §18): because the output includes cost and margin figures, the decision pack and README state that economics are modeled estimates from entered assumptions and verified rates, not financial advice, and list limitations plainly.

## 3. Track and sponsor alignment

Recommended single primary track: **The Agent That Can Explain Why**. The agent joins founder constraints, model/pricing evidence, FAQ knowledge, and task results to explain a decision. A complex multi-agent topology is not required for this fit. Select the track in HackOS and verify its challenge checklist. [G3]

| Requirement | Product use | Acceptance evidence |
|---|---|---|
| Zetaris as data layer | Retrieve model/rate facts, approved FAQ, and evaluation evidence | Trace has actual read/query IDs, source-record IDs, and versions used in the recommendation. |
| At least one working Meterless Engine | H-MEM stores/retrieves founder-approved constraints and prior findings | Restart/resume recalls the constraint, cites the memory ID, and changes or preserves a decision appropriately. |
| Nightshift as primary AI provider | Advisor and candidate generation use the Nightshift connection | Redacted runtime trace identifies gateway and requested/resolved model when available. No silent direct-provider bypass. |
| Best use of Nemotron objective | Nemotron acts as the evidence critic through Nightshift, identifying unsupported FAQ answers and proposing a targeted correction | A live critique affects the next action; request evidence identifies the actual Nemotron model, its Nightshift route, and the resulting action. |
| Coding tooling | Cursor (with Space XAI) is **optional** under Official Rules §8.1 and Submission Requirements §4. The Submission Form Preview's readiness line "the project was developed in Cursor" is superseded by the Rules. The sponsor explanation still has a Cursor row, so the team should do some real development in Cursor (not a token install) and describe it truthfully; this is a cheap Sponsor Tech point, not a compliance gate. | README and sponsor explanation state actual tools used without claiming a mandatory Cursor dependency. |

The sponsor technology explanation (10 points) must answer four rows plus a closing "what was unique": Zetaris as data layer; Meterless (which engine, what feature it powers, the passing test, and how the app connects to Nightshift); NVIDIA (which Nemotron model, where it contributes, through Nightshift); Cursor (how used, or a truthful statement of the tooling actually used). A one-line explanation is a listed common mistake.

G1/G7 establish the mandatory sponsor baseline. A copied prompt, unused dependency, SQLite row labeled “memory,” or mocked sponsor response does not satisfy it. The additional executive summary (S2) makes a working Nemotron feature through Nightshift, with model identity shown, an NVIDIA-award eligibility condition. The user has explicitly adopted that award objective, so it is a project release requirement. It supplements the single primary track; it does not create a second primary-track entry or guarantee an award.

## 4. Required scope and acceptance

| ID | Requirement | Acceptance condition |
|---|---|---|
| R01 | Guided founder brief | Idea, usage, latency/budget/quality needs, optional price/paid-user assumptions. Every generated default is marked assumed and editable. |
| R02 | Evidence retrieval | Read relevant facts from at least two distinct domain source sets through Zetaris: model/rates and FAQ; task evidence adds a third set. Each fact retains provenance. |
| R03 | Bounded planning | Agent selects a next action from allowlisted tools based on evidence gaps or constraints, rather than merely passing text along a fixed chain. |
| R04 | Deterministic economics | Calculate two options using explicit units/rates, low/base/high scenarios, and unit economics with missing-data warnings. |
| R05 | Executed evaluation | Run approved FAQ cases through two configurations with grounded-answer checks, expected facts, errors, usage, and elapsed time. |
| R06 | Critique and revision | A detected development-case failure or missing evidence produces a targeted re-query, one approved workflow revision, or founder clarification; rerun the affected development cases. All-pass input can finish without artificial failure. |
| R07 | Shared memory | Confirmed constraints and accepted findings survive restart via H-MEM and are retrieved into a subsequent decision. A superseded assumption cannot silently remain authoritative. |
| R08 | Explainable decision | Display action, concise reason, evidence IDs, evaluation findings, and before/after changes. Export Markdown and scenario/configuration JSON. |
| R09 | Recovery and stop | Handle missing evidence, provider failure, invalid structured output, or budget exhaustion with bounded retry, visible partial state, clarification, or abstention. |
| R10 | Actual sponsor use | Demonstrate the G7 integrations in the target environment and preserve redacted proof in the submission. Recorded evidence is labeled as recorded. |
| R11 | Nemotron evidence critic | Given development answers, approved FAQ evidence and rubric, Nemotron returns structured gaps with source/case IDs and a permitted corrective action. The controller validates it and records whether it changed the plan. The actual Nemotron model and Nightshift request are attributable. |
| R12 | Credential-free sample mode | With SAMPLE_MODE=true, no credentials and sponsor services stopped, execute fresh planning, retrieval, validation, branching, economics and report generation against cached data. Changed and previously unseen supported inputs produce appropriate results and new traces. No saved final answers or model-response replay drives decisions; no live inference is claimed. |
| R13 | Reproducible judging package | Clean setup instructions, small licensed/de-identified sample data, input/output examples, the passing Meterless Engine test pointed to from the README, action traces, dependency versions and sponsor explanation are included. No runtime installation, local GPU, or large download is needed; repository stays small. `.env.example` has placeholders only; `.env` is gitignored. |
| R14 | Noninteractive judging interface | A documented `run.py` JSON-in/JSON-out command uses the same core as the UI, requires no clicks or prompts, and returns structured needs_input/partial/error results. Approval and spend bounds are explicit input fields; absent approval cannot launch paid work. An HTTP `POST /run` is an acceptable alternative per the Technical Execution Guide, not a requirement. |
| R15 | Input-responsive evidence | Ship at least three input examples and three matching generated outputs; also test a new in-domain input. Current-run traces (stdout and `logs/trace-<run_id>.jsonl`) show at least two named interacting agents, handoffs, a real validation/branch event, each Zetaris query, each H-MEM operation, and the model that handled each Nightshift request. Runtime never reads output_examples as its answer source. |
| R16 | Bounded runtime | A full live run targets 5–10 minutes with per-call timeouts (Zetaris 30–60 s, Nightshift 30–90 s, loop iteration 1–3 min) and capped iterations; a sample-mode run finishes in well under a minute. Failures return a controlled, structured error rather than a hang or silent crash. |

### Scope deliberately excluded

Full application generation, AST/code refactoring, changes to a real founder's repository, runtime model switching in a live business, all four engines, self-hosted GPUs, vector database work, automatic price scraping, multimodal support, accounts/billing, and complex custom UI. One bounded agent with planner/evaluator roles is sufficient; separate services and swarms are unnecessary.

Prefer one results view with adjustable usage, a short evidence/action timeline, two candidate rows, and export. Expand detailed economics only when needed. Source transparency and correctness take precedence over dashboard polish. [G1, G2]

## 5. Agent behavior in the founder journey

1. Founder describes the product and confirms workload/economic assumptions.
2. Agent recalls approved constraints, identifies missing facts, and retrieves evidence from Zetaris.
3. Planner proposes two eligible configurations and a task-test plan.
4. Founder approves the bounded evaluation scope and estimated spend.
5. Tools execute development cases; evaluator checks grounding, factual content, cost bounds, and evidence completeness.
6. On failure, agent selects a specific action: retrieve missing FAQ context, ask a clarification, or revise the prototype context/escalation setting. One repair is permitted under the approved envelope. Confirmed business constraints cannot be changed automatically.
7. Freeze configurations; run final holdout comparison. Show a conditional decision or “insufficient evidence.”
8. Store confirmed constraints/accepted findings through H-MEM; export the prototype recipe, economics, evidence, and next step.

The demo should show one real branch and recovery. A prepared synthetic stress case may make that branch reproducible if labeled. Do not claim that a favorable result or a revision will always happen. Use three distinct cooperating roles inside the app: Planner assigns the bounded investigation, Analyst executes evidence/cost/task tools, and Nemotron Critic challenges the Analyst's evidence. A critique returns to Planner and Analyst for revision. Role-specific structured messages and observable tool work matter; merely renaming stages does not establish agent interaction. [S2, S3]

The Nemotron feature should help a founder avoid selecting a cheap configuration that produces unsupported answers. Demonstrate its contribution with the same development outputs before critique and after the accepted correction: gap detected, source cited, action selected, recheck outcome, and added latency/cost. Include one correct-answer control to expose false alarms. Human review remains authoritative for this small study. If the critique fails or produces no benefit, report that result. This is contribution evidence, not a claim Nemotron outperforms other critics; a separate critic tournament is outside scope.

## 6. Evaluation without misleading quality claims

Dataset target remains ten approved FAQ cases: three development cases and seven sealed holdout cases. Include known answers, paraphrases, ambiguity, and out-of-FAQ questions. Founder approves required facts, acceptable clarification/refusal, and critical failures.

Default primary comparison: two actual model IDs behind Nightshift using the same FAQ workflow. Record model resolution; if two models are unavailable, two workflow configurations of one named model may be compared, clearly described as workflow evidence rather than proof of a model ranking.

Use three development cases for critique and at most one repair of one candidate. Then freeze both final configurations before the seven-case paired holdout test. All versions and costs remain available. If both model and workflow differ after repair, describe the final result as a configuration comparison, not attribution of the gain to the model alone.

Do not feed holdout answers, grading, or failures back into the planner before freezing results. A holdout failure can block the recommendation or become a future test, not trigger repeated tuning on the same test. Suggested quality gate: all seven holdout cases pass the predefined rubric with no observed critical failure. Report the count and small sample; it does not establish general accuracy.

Three levels of evidence remain separate:

- **Agent behavior:** retrieves missing evidence, selects a permitted action, respects constraints, persists memory, and stops appropriately.
- **Task quality:** deterministic checks plus human review of semantic grounding. Model critique can identify a gap, but cannot by itself certify correctness.
- **Founder impact:** two or three founders can explain the recommended prototype choice, main cost driver, and remaining test after using the tool. Record their original choice, changed/unchanged decision, and feedback with consent.

Maximum primary candidate generations: 6 development + 3 repair + 14 holdout = 23. Extra calls and operational retries require reserved budget; no unlimited evaluation loop. Targets may be reduced transparently if integration consumes capacity. Evaluation, a real feedback branch, and required sponsor use remain release gates.

## 7. Economics and uncertainty

```text
calls = active_users × workflows_per_user × calls_per_workflow
billable_calls = calls × (1 + average_extra_attempts)
monthly_cash_cost = sum(provider-normalized usage × verified rates)
                  + entered application/retrieval/storage/other cash costs
paying_users = active_users × paying_fraction
revenue = paying_users × subscription_price
contribution = revenue - included_monthly_cash_cost
margin = contribution / revenue  [only when revenue > 0]
```

Use Decimal arithmetic, provider-specific billing adapters, separate input/output/cache/reasoning categories, and displayed cost scope. Unknown fees do not become zero. Treat long-context thresholds, cache eligibility, and stacking rules as provider-specific facts requiring verification. Avoid speculative KV-memory calculations unless serving hardware is actually modeled; token API billing does not follow a generic KV formula.

Show per-workflow cost and low/base/high volume, with 10× growth as the main demonstration. More scale presets are optional. Development effort is an editable range, not a quote. Separate imputed labor, team evaluation expense, and the founder's forecast production costs. Sponsor credits cannot establish a zero production price.

No revenue assumptions means a cost-only report and focused follow-up questions, not a viability verdict. No published rate means an explicitly unknown/modeling scenario; no paid run until the team can bound its actual spend. A small benchmark informs assumptions but does not prove production workload distribution.

## 8. Definition of done and current gaps

Done means a founder brief produces a real sponsor-backed investigation, an executed task comparison, one demonstrated evidence-dependent revision/clarification path, H-MEM recall after restart, a reproducible decision pack, and a clear explanation of limitations. Arithmetic fixtures, no-duplicate-call checks, an outage/stop test, credential-free sample mode, and the attributable Nemotron critic feature pass. [G8, S1–S3]

The submission package on HackOS has exactly these parts, each of which judges check as a whole:

1. Project name and description (one sentence plus a short paragraph).
2. One primary track, named identically in README, deck and video.
3. Team roster: full name, HackOS email, GitHub username, role, one primary contact.
4. Public GitHub repository with README covering setup, usage and dependencies (Zetaris and Nightshift included), runnable from a fresh clone with no undocumented manual step.
5. Demo video, 1–4 minutes, covering: the problem and user; the main workflow on a real input; how the agent solves the track challenge; key features; agent behavior (interaction, critique, retry); and Zetaris + Meterless integration shown as the agent querying Zetaris, the feature H-MEM powers, and one real request through Nightshift returning a result. No keys on screen; link opens in a private browser window.
6. Slide deck covering all eight points: problem and target users; solution; agent workflow/architecture; technical stack; how Zetaris and Meterless were used; what was unique about the sponsor use; product visuals; future enhancements.
7. Sponsor technology explanation: Zetaris, Meterless (engine + test + Nightshift), NVIDIA, Cursor, and what was unique.
8. Pre-existing components declaration (anything before October 22, 00:00 UTC).
9. Colab links only if agents run in Colab (they do not).

Current gaps: sponsor accounts/access, actual approved FAQ/cases, runtime hardware/deployment topology, two candidate IDs and rates, workstream agreement, and founder appointment times. Registration and the 40-hour commitment are confirmed by Narin; do not reopen them as unanswered questions.

### Judging readiness

The Technical Execution Guide is recommended practice and defers to the Official Rules; its "test it like a judge would" flow is our release rehearsal. Our release acceptance includes a teammate following the README on a second machine from a fresh clone, both the live and credential-free paths, the noninteractive entry point, and three meaningfully different example outputs. Installation and sponsor provisioning may be documented prerequisites; copying project data by hand, editing source, notebook preparation and undocumented source registration are not acceptable setup steps.

Sample mode is a bounded offline decision system: rule-based Planner/Analyst/Critic policies run the shared controller on cached facts, real H-MEM and deterministic calculations. It can retrieve additional cached evidence, reject unsupported assumptions, change eligibility and request missing information. It cannot claim fresh model answers, new benchmark quality or live Nemotron critique. Historical evaluation records may inform a clearly scoped recommendation, with date/configuration provenance. An unfamiliar task gets a useful partial decision and explicit evidence gaps rather than a canned success or a blanket failure. This replaces v3.1's replay-oriented sample design. The organizer's own words set the bar: sample mode must work "without Zetaris, Nightshift or any network access," because a judge may have neither running — so it is a reproducibility requirement, not a courtesy fallback. It never substitutes for live sponsor proof.
