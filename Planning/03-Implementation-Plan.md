# Implementation plan: October 24–27 build

Version 3.4 | Prepared late evening October 23, 2026 | Remaining effort: 40 team-hours | Cash ceiling: $100 | Aligned to Open Agent Hackathon organizer documents; see [05](05-Guideline-Alignment-Review.md) | v3.4 adopts the retrospective case study in [06](06-Retrospective-Case-Study-Design.md) and the Windows single-host decision

Implements [the PRD](01-Product-Requirements.md) and [architecture](02-Technical-Architecture.md). Latest roster is **Narin, Pradeep, Meena, Isioma, Shrie**, all registered. No Zetaris or Nightshift account exists yet. The project has planning documents but no verified working application. Assignments other than Narin's integration/deployment ownership are proposals for tonight's meeting.

## 1. Immediate orientation decisions

Tonight: finish the relevant welcome/setup materials; select one primary track in HackOS; assign account/setup owners; confirm laptop/runtime feasibility and each member's build times. Baseline: Zetaris data layer, Nightshift primary inference, one working Meterless Engine, a working Nemotron critic for the additional award objective, optional Cursor. Resolve conflicting challenge-page instructions through the event help process rather than relying on older public pages.

Narin owns sponsor onboarding and deployment; Pradeep is proposed to pair on the first live calls and H-MEM bridge. Every member must know where secrets belong and where the submission checklist lives. Accounts should be individual/shared only as permitted by sponsor terms; no requirement to create duplicate accounts or share passwords (credential sharing is a code-of-conduct violation).

Tonight's administrative must-dos, each irreversible or cheap now and expensive later:

1. Collect every member's full name, HackOS account email and GitHub username; confirm nobody is on another team and nobody has a second HackOS account. Narin is primary contact.
2. Agree the prize split in writing (default is equal; any other split must be submitted in writing).
3. Create the public GitHub repository under an agreed owner; every member makes at least one real commit so form usernames match contributors.
4. Decide Cursor usage: optional, but at least one member should do real work in Cursor so the sponsor explanation's Cursor row is truthful and non-empty.
5. ~~Inventory pre-existing components~~ **Settled Oct 23: none. Team started from scratch on Oct 23; the form field reads "none."**
6. Verify the integration host: run `scripts/preflight_windows.ps1` on each candidate Windows machine; the first to return READY (or READY WITH WARNINGS with no Docker RAM/CPU fail) is selected. Decision Oct 23: Zetaris in Docker Desktop/WSL2, Nightshift native, Python app native, no app container.
7. **Settled Oct 23: registered data lives in an Amazon S3 bucket.** Decide tonight whose AWS account hosts it and who holds the Zetaris-side credentials (never the app).
8. Narin reconstructs the founder brief from pre-build artifacts only, dated, before touching actuals (06 §3 M1–M2, §4 controls). Meena is named leakage reviewer.
9. Narin confirms the four priced approaches and the T1–T8 task list in 06 §2.3 and §10.

The 40 remaining hours cover all remaining project effort, including orientation catch-up, setup, integration, tests, founder sessions, recording, and submission. Do not assume every member can work all four days or that the calendar window equals engineering capacity.

## 2. Effort allocation and proposed owners

| Member | Base work within timebox | Planned | Reserve | Total |
|---|---|---:|---:|---:|
| Narin | Account/runtime/setup and deployment 3h; scope/rules 1h; founder session 1h; demo/submission 1h | 6 | 2 | 8 |
| Pradeep | Real H-MEM bridge 2h; bounded controller/sponsor adapters 3h; cost core 1h; technical checks 1h | 7 | 1 | 8 |
| Shrie | Minimal founder/results UI 1h; shared CLI/export 1h; trace/model attribution 1h; offline policy/adapters 2h | 5 | 3 | 8 |
| Isioma | Dated pricing snapshots for four approaches + candidate models 2h; eight dev-task cases/rubrics 3h; grading 2h | 7 | 1 | 8 |
| Meena | Evaluator/Nemotron critique checks 3h; live/sample/failure QA 2h; founder session 1h; award/submission evidence 1h | 7 | 1 | 8 |
| Total | Aggressive targets, subject to capability/access evidence | 32 | 8 | 40 |

This redistributes time from UI polish to sponsor/agent behavior. Pradeep's proposed seven base hours are the principal technical bottleneck; Narin's integration ownership includes coordinating and verifying that work. Shrie's larger reserve is available for critical-path support with review, not new optional features. Do not claim this timebox guarantees delivery. If an unfamiliar engine/runtime takes longer, use reserve and reduce optional scope immediately.

Keep the proposed cash envelope at $15 hosting, $10 planning/access calls, $25 candidate evaluations, and $50 uncommitted reserve. These are limits, not quotes. Account plans, Nightshift runtime, Zetaris infrastructure, and credits need verification. Hardware/cloud costs may require reallocation within $100. Record cash charges and credits separately. Do not authorize a subscription or expose a paid public endpoint on the strength of this document.

## 3. Sequence and milestone gates

Dates are America/Chicago. The uploaded guide's submission close is **October 27 at 6:45 p.m. Chicago (23:45 UTC)**. Proposed internal upload target is October 27 noon. Judging begins October 28 UTC in the uploaded guide, replacing the earlier October 27 statement. [G4, G8]

| Stage | Target | Required exit evidence |
|---|---|---|
| Orientation catch-up | Oct 23 evening / first session | Current rules read, track selected, setup owners and working times agreed |
| A: Sponsor/engine spine | Oct 24, first build block | Accounts/runtime ready, actual Zetaris query, NVIDIA-backed Nightshift call, real H-MEM save/restart/recall |
| B: Small working agent | Oct 24, before feature expansion | Founder brief selects evidence/tool action, sees a development failure, retrieves/revises or clarifies, then produces a traceable partial decision |
| C: Founder decision journey | Oct 25 | Two configurations, correct cost/economics, simple UI, one completed bounded development loop, exported recipe/report |
| D: Evidence and hardening | Oct 26 | Frozen configs, paired holdout run, founder sessions, failure/stop tests, working runtime topology, README and video draft |
| E: Freeze and submit | Oct 27 | Clean setup, final recording/deck, public repository/checklist, links tested and upload accepted before official close |

Treat access setup as an experiment. After approximately four **combined person-hours**, review the spine's actual status. If blocked, use sponsor support and reserve with a specific owner and return time. This is a replanning checkpoint, not a promise the services install in four hours. A fake integration or direct provider bypass cannot be used to declare the gate passed.

## 4. Work packages, dependency, and done

| ID | Package and proposed lead | Dependencies | Acceptance |
|---|---|---|---|
| W01 | Orientation/track/setup, Narin | None | Required technologies, accounts, model access, supported runtime topology and secret handling confirmed |
| W02 | Live sponsor adapters, Narin + Pradeep | W01 | Real Zetaris source query and Nightshift→NVIDIA request attributable in redacted trace |
| W03 | Real H-MEM feature, Pradeep | W01 | Pinned reference reused; approved project fact survives restart, retrieves with provenance, and is isolated from other projects |
| W04 | Case-study data, Isioma (+ Narin for brief and actuals, Meena for leakage review) | W01, W02 | Reconstructed brief with status labels; dated pricing snapshots for four approaches and two candidate models; three development and five holdout task cases with frozen rubrics; sealed actuals registered under a distinct source name; leakage review signed off |
| W05 | Tools/costs, Pradeep | W02, initial W04 | Deterministic calculator, candidate eligibility and source retrieval contracts work with fixtures |
| W06 | Critique/loop/evaluator, Meena + Pradeep | W02–W05 | Observed development result triggers a justified branch and at most one repair; holdout cannot feed repair |
| W07 | UI/report/trace, Shrie | Contracts from W04–W06 | Brief, confirmed assumptions, two options, action timeline, progress, export all consume same result IDs |
| W08 | Deployment/recovery, Narin | W02, W03, W06 | App reaches required runtimes, secrets safe, persistence works, interrupted/duplicate calls controlled |
| W09 | Validation/evidence, Isioma + Meena | W04, W06–W08 | Semantic grading, real memory test, outage case, arithmetic verification, two or three founder observations |
| W10 | Demo/submission, Narin + Meena | W08, W09 | Truthful live/recorded demo, public repo/README, deck/video, sponsor explanation, component declaration, tested checklist |

These packages share the 32 planned hours above; they are not extra allocations. Shared leads indicate a review/pairing boundary, not two separately staffed teams. Integrate as soon as the spine works. Minimize schema changes after October 25 and code changes after the October 26 recording rehearsal.

### Version 3.1 acceptance additions to existing packages

- **W01/W02, Oct 24:** Narin owns access, with Pradeep pairing on runtime verification. Start Zetaris first; obtain platform bundle and registry access, check Docker resources/WSL2, complete preflight/bootstrap/verification, then SELECT 1 and real data queries. Install Nightshift desktop, configure NVIDIA in Providers, choose a Nemotron lane, obtain runtime credentials from Console and test actual app calls with the required headers. Health checks/account signup alone do not pass. Record exact working versions, routes and models. S4 pages 6–11 and 16–20 are the setup references.
- **W03:** Keep passing H-MEM feature and relevant reference/conformance checks, engine revision, code locations and restart/recall evidence. Provider integration does not satisfy the separate engine requirement.
- **W04:** Isioma packages pricing snapshots (dated, URL-cited; unknown rates stay unknown) and the eight task cases with rubrics, uploads to the S3 bucket and registers each source. Narin supplies the brief and the sealed actuals (06 §3); the actuals go in a separately named source. Meena runs the forbidden-terms leakage review on the brief before registration. Create two or three additional synthetic founder briefs for input examples and sample mode, clearly labeled synthetic. Holdout rows and the sealed source are unavailable to the repair context by controller rule, not convention.
- **W06, Oct 25:** Implement Planner–Analyst–Nemotron Critic messages and one validated revision. Use one batched critic call within the existing three role-call budget, with a templated final report. Pradeep reviews contracts; Meena checks schema, invalid citations, false alarms and failed/timeout critique handling.
- **W07/W08:** Shrie adds a JSON CLI around the shared core and explicit offline policies/adapters with persistent labels. Pradeep reviews controller reuse; Narin verifies the live host path. By Oct 25, sample mode must execute fresh input-dependent decisions and traces with no credentials, replayed model responses or final-output lookup. Reuse tools/validation to keep offline logic small.
- **W09, Oct 25 first rehearsal; Oct 26 full validation:** Meena runs a fresh clone on a second teammate's machine, first without credentials/services and then with documented live setup. Verify all three example inputs plus a new in-domain input, real branching and meaningful output changes. Isioma reviews the live critic's development gaps and correct-answer control. Preserve before/after results, latency/cost and any negative outcome. Run actual sponsor tests separately.
- **W10:** Narin owns final submission; Meena checks sample instructions, Nemotron attribution and evidence links. Confirm the five-person HackOS team and repository owner before creating the first submission: team composition locks then. Declare pre-existing planning/data/code as applicable; the Meterless H-MEM starter is sponsor open source and is named and pinned in the README rather than declared. Confirm award-specific submission fields and agreed prize handling with the team. Submit early; ties use Impact then submission timestamp. Acceptance for W10 is the completed Preparation Worksheet from the Submission Form Preview (project name, one-sentence description, track, five member rows, public repo URL, video link, deck link, four-row sponsor explanation plus "what was unique", pre-existing declaration), with video and deck tested in a private browser window.

These additions replace generic NVIDIA usage, generic failure QA and UI polish; they do not add hours to the 32+8 allocation. If sample-mode wiring or setup exceeds its timebox, use reserve and cut optional charts before reducing live sponsor proof, the critic feature or reproducibility.

## 5. Minimal feedback-loop experiment

Use the founder brief with a confirmed constraint recalled from H-MEM, such as a cash ceiling or "solo founder, no DevOps." Start with development task T1 (ingestion module) whose spec needs a rate-limit or caching record the initial context selection misses. This is a disclosed stress fixture, not an invented founder failure.

1. Planner retrieves brief and pricing sources and proposes two approach/model configurations using constraints recalled by H-MEM.
2. Candidate generation through Nightshift produces a T1 spec with an unsourced cost note or a missing failure mode, failing the required-element check.
3. Nemotron Critic emits a concrete gap with task and source IDs; human review confirms as needed.
4. Planner chooses a targeted Zetaris re-query (the missing pricing or requirement record) or a permitted output-contract revision, rather than blindly asking the same prompt again.
5. Re-evaluate the affected three development cases once, recalculate changed token/cost assumptions, and record before/after results.
6. If still insufficient, abstain/ask the founder. If acceptable, freeze both candidates and run holdout. Persist accepted constraints/findings via H-MEM for a later run.

This proves decision/action/feedback with bounded work. It does not require a deliberately bad default in every founder run, automatic mutation of business requirements, or a guaranteed quality improvement. Save the all-pass/no-repair path as a separate acceptance fixture.

## 6. Tests prioritized by founder and judging value

Required behavior fixtures:

- Missing source evidence leads to re-query or clarification with cited IDs.
- A development failure triggers at most one valid revision; an all-pass case skips revision.
- Unresolved or unsafe requirement produces an honest partial result/abstention.
- Frozen holdout results cannot be sent into repair or rewrite the final configs.
- H-MEM saves and recalls a real approved constraint after restart; no cross-project leakage or stale-price authority.
- Every inference call goes through Nightshift; trace shows route and model identity when available. NVIDIA key is absent from project files and recordings.
- The Nemotron critic's underlying model is confirmed by a response or correlated Nightshift receipt/log; `meterless/auto` alone does not pass the award test. Its structured finding produces a validated action or an honest no-change/abstention result.
- SAMPLE_MODE=true runs without credentials or live services, makes zero network requests, recalculates edited usage, and labels every recorded result/export. Unsupported sample inputs remain unevaluated.
- Zetaris is used in the recommendation's actual evidence path, including task evidence source access/writeback as supported.
- UI rerun/double submit does not dispatch twice. Timeout or unknown call outcome stops/reconciles rather than replaying automatically.
- Cost fixtures distinguish paying/active users, missing rates/revenue, retries, zero usage/revenue, and rate units. Report/UI match after scale or workflow changes.

Add: a read of `retrospective_actuals` or a holdout row before freeze is denied and logged; the comparison script runs only on a frozen pack; no artifact contains a "saved $N" sentence (grep the README, deck notes and pack templates).

Review all eight task cases with approved rubrics. Record attempt/failure denominators, development versus holdout outcomes, grounding errors, costs, and small-sample limits. Do not rely on an LLM judge as the sole quality authority. Two or three founders supply before/after decisions and feedback with permission; a negative result remains valid evidence.

## 7. Demonstration and submission evidence

Proposed three-minute demo:

- **0:00–0:25:** Founder problem and confirmed workload/constraint.
- **0:25–0:55:** Agent recalls the constraint and retrieves distinct source records through Zetaris.
- **0:55–1:40:** Execute a development task, display the concrete failure/gap, show the selected corrective action and its bounded recheck. Display Nightshift route/NVIDIA model identity and cost.
- In that same segment, identify **Nemotron as the critic**, show its cited finding and the Planner/Analyst response, and display the underlying model plus Nightshift request evidence. Compare the observed result before/after correction without claiming general accuracy or guaranteed savings.
- **1:40–2:20:** Show frozen paired holdout results and a live scale change; explain the recommended configuration or evidence gap.
- **2:20–3:00:** Export prototype recipe and economics; show H-MEM recall after session restart and founder feedback. Use a clearly labeled recorded full run if needed for timing; preserve live small-run proof.

The demo must visibly cover the organizer's six required points: problem and user (0:00–0:25); the main workflow on a real input (0:25–1:40); how the agent solves the Explain-Why challenge (evidence IDs behind the decision, 1:40–2:20); key features (export, scale change); agent behavior (Planner/Analyst/Critic interaction and the one repair, 0:55–1:40); and Zetaris + Meterless integration shown three ways — the agent querying Zetaris, the H-MEM feature at work, one real request through Nightshift returning a result with its model name. The video is 1–4 minutes; three minutes is the target, not a cap. No `.env`, terminal token, or Nightshift Providers screen in frame.

Slide deck, eight slides mapping one-to-one to the required points: (1) problem and target users; (2) solution; (3) agent workflow/architecture (reuse the controller diagram); (4) technical stack; (5) how Zetaris and Meterless were used (table from PRD §3 plus the engine test name); (6) what was unique about the sponsor use (Nemotron as evidence critic with attributable model; H-MEM memory that constrains the next plan; Zetaris as the only source of pricing authority); (7) product visuals (results view, trace, export); (8) future enhancements. Deck claims must match code and traces; README, deck and video all name the same track.

README includes actual architecture, exact setup/version instructions, required services/hardware (no local GPU), no-key examples, known limits, component licenses/declarations, evaluation manifest, the path to the passing H-MEM test, and sponsor usage. Verify current HackOS challenge/submission fields. The Official Rules require a public repository, video, deck and sponsor explanation; do not invent extra eligibility obligations (port 8000, `metadata.json`, use-case IDs, 15-minute limit) from the G42 templates in the folder, which belong to a different event.

Scoring evidence follows G9: founder decision and usefulness for impact (30), real loop/recovery and correctness for technical (20), connected cost/quality/evidence reasoning for innovation (15), clear working execution for demo (15), understandable assumptions for UX (10), meaningful integrations for sponsor technology (10). Compliance is a release gate, not a discretionary ten-point feature that can be omitted.

## 8. Cuts, limits, and unresolved decisions

Cut in this order: decorative UI, extra scale charts, elaborate development-cost estimates, third candidate, additional task domain. Reduce the number of task cases only with visible sample-size labeling and retained development/holdout separation. Keep one functioning memory feature, Nightshift primary execution, Zetaris data use, one real branch/recovery, correct costs, and a useful report.

If access is blocked, seek a supported sponsor path immediately; do not rebuild H-MEM or disguise an unsupported substitute as compliant. If no eligible working route can fit the remaining effort/cash, record that as a submission blocker rather than claiming readiness. Forty hours and a functioning sponsor stack are prerequisites to the aggressive targets, not grounds for guaranteeing a win.

Tonight's open decisions: accept proposed workstream owners; finish orientation; nominate account owners; verify machines/runtime access; identify approved FAQ and founder appointments. First-build decisions: actual sponsor endpoints/models/rates, host/recording/deployment path, supported H-MEM setup, and spend reservations. Registration, roster, 40 remaining hours, budget cap, and Narin's integration ownership are settled.

Additional stop gates: ambiguous Nemotron identity or direct-provider-only execution blocks claiming the NVIDIA objective is met; a non-working no-key sample blocks judging reproducibility. Confirm and record guide conflicts with sponsor support, particularly any host-specific requirement. Keep both live integration evidence and a credential-free reviewer path; one does not substitute for the other.

## 9. Version 3.2 judging rehearsal and release checklist

Use [the release evidence checklist](04-Release-Evidence-Checklist.md) to record pass/fail and artifact locations; all gates start unverified. The Technical Execution Guide and Submission Form Preview are preparation guidance and explicitly defer to the Official Rules on the event page, which are still marked draft in our copy; Narin re-reads the live rules page and the HackOS form before submission. Confirm one participant account, one team and one submission per person; do not reopen registration or create duplicate accounts.

**Oct 24, first thing:** run `scripts/preflight_windows.ps1` on the candidate host(s) before any install; fix `.wslconfig` if Docker shows under 8 GB / 4 CPUs; re-run with `-ZetarisUrl`/`-NightshiftUrl` once each runtime is up and save the `SELECT 1` body for the adapter. Then Narin/Pradeep complete setup and source registration. The new Zetaris diagram (S6) reinforces registry access, correct extracted working directory, hardware allocation and password change. Keep the detailed S4 order: preflight, configure, start, then verify. Use supplied credentials only for initial access and replace defaults privately. Run a bounded starter query from the matching installed recipe, then our FAQ/rate query. The diagram's all-Pokemon table and S4's Pikachu view are different examples; neither table name is a universal requirement or application dataset.

**Oct 25:** First clean-checkout rehearsal, while fixes remain possible. Narin supplies only README instructions; Meena or a teammate who did not implement setup runs them on another machine without author coaching. Test a documented entry point, automated data/source setup, and empty-environment sample mode. Keep Python and Node setup in the same documented flow; dependencies cannot install after launch. Commit at least three matching generated input/output examples with mode, config version and provenance. Validate a fourth unseen input, a missing-field case and a changed constraint. Runtime must not read output_examples.

**Oct 26:** Full live/sample validation and fixes take precedence over optional features. Run the guide's "test it like a judge would" sequence verbatim: fresh clone → `cp .env.example .env` → documented install → live run on `input_examples/example_1.json` → read `logs/trace-*.jsonl` → then stop Zetaris and Nightshift, set `SAMPLE_MODE=true`, and run again. Any fix made by hand means the README is incomplete. Test sponsor timeouts, feedback/no-repair paths, memory test, logs and model attribution. Verify no local GPU is required: live model inference uses hosted providers through Nightshift. Docker is recommended by the guide, not mandated; prioritize the proven clean-environment CLI path and add a Dockerfile only from reserve. If packaging in Docker, include Node/reference dependencies, persistence paths and tested host connectivity. On Docker Desktop, host.docker.internal can address host services; localhost inside the container cannot. Verify the actual host binding/firewall and document Linux differences instead of assuming the hostname is universal.

**Oct 27 before noon internal target:** Meena checks public repository, deck and video links in a signed-out/private browser; Narin confirms submission acceptance. Audit README/deck capability claims against implementation and traces. Inspect source, tracked files and Git history for secrets, plus video frames/screenshots around terminals and provider settings. If a real key is exposed, revoke/rotate first and clean history/artifacts; deleting the latest copy alone is insufficient. No credentials are printed into the evidence ledger. After a material fix, repeat the affected checks and the final clean-run flow, regenerate outputs/traces from the fixed revision and update README commands.

**Oct 27 submission sequence (noon internal target):** confirm roster on HackOS → create the first submission (roster locks) → fill the worksheet fields → attach repo URL, video, deck, sponsor explanation, declaration → verify acceptance → re-check every link signed out. Updates remain possible until 23:45 UTC; use that only for corrections, not new features.

The revised work replaces UI time and strengthens existing W07–W10; 32 planned + 8 reserve hours and $100 remain. Docker packaging, HTTP hosting and extra visuals are lower priority than the shared CLI, genuine offline logic, live sponsor feature proof and a reproducible handoff. The $15 hosting line is now contingency only: no organizer document requires a hosted deployment, so the default is one local integration laptop.
