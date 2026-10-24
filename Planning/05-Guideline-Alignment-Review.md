# Guideline alignment review: v3.2 → v3.3

October 23, 2026 (late evening) | Reviewer: Claude for Narin | Scope: PRD, architecture, implementation plan checked against the Open Agent Hackathon 2026 organizer documents

Documents treated as binding, in precedence order: Official Rules (draft copy; live page governs), Submission Requirements, Submission Form Preview, Technical Execution Guide (recommended practice unless the Rules say otherwise).

## 1. Verdict

The v3.2 documents were already compliant on every hard gate: Zetaris as data layer, one working Meterless Engine with a test, Nightshift as primary provider, attributable Nemotron use, public repo, 1–4 minute video, deck, sponsor explanation, no committed secrets, declared pre-existing work, deadline and timezone correct. Nothing in v3.2 would have caused disqualification.

The v3.3 changes are alignment and risk-removal, not redesign. Three were worth making tonight because they are irreversible or shape judge perception (F1, F3, F4); the rest are hygiene.

## 2. Findings and changes

| # | Finding | Source | Severity | Change made |
|---|---|---|---|---|
| F1 | Three files in the project folder (`metadata-json-template.md`, `demo-script-template.md`, `readme-template.md`) are from the **G42 Agentathon**: Compass models, port 8000, `metadata.json`, use-case IDs 1–25, 15-minute limit, 2–3 minute video, June deadline. v3.2 had partially absorbed them via "S5" references (HTTP `/run`, "day four", "Dockerfile strongly recommended by S5"). | Templates vs Official Rules §10, Submission Requirements §2 | High (building to the wrong spec wastes hours) | PRD header declares source precedence and marks these templates non-binding. Architecture and plan now cite the Open Agent Technical Execution Guide instead of S5. Explicit "do not invent obligations" line in plan §7. |
| F2 | No project name or one-sentence description existed anywhere; the form requires both and gives a weak/strong example. | Form Preview §3.1 | Medium | PRD header carries a draft name and one-sentence description in the form's "who / what / produces" shape. Confirm tonight. |
| F3 | Roster-lock and identity data (HackOS emails, GitHub usernames, prize split, one-account rule, contributor matching) were mentioned only in passing in W10. | Rules §3, §5.4–5.6; Form Preview §3.3 | High (irreversible once the first submission is created) | PRD §2 lists the rules; plan §1 adds six administrative must-dos for tonight. |
| F4 | Pre-existing-work boundary not dated. "Retain a Python/Streamlit app" implied code may exist from before October 22, 00:00 UTC. Data curated before the window also needs declaring. | Rules §8.2, §11.3; Submission Requirements §5 | High (undeclared pre-existing work is a disqualification ground) | PRD §2 states the boundary; architecture §1 says to declare and isolate any pre-window code; plan §1 adds an inventory step. H-MEM starter clarified as sponsor open source: name and pin it, no declaration needed. |
| F5 | Cursor: Rules say optional; Form Preview readiness list says "developed in Cursor." Sponsor explanation has a Cursor row regardless. | Rules §8.1; Submission Requirements §3.4; Form Preview §2 | Low compliance / Medium scoring | PRD §3 records the precedence and recommends real (not token) Cursor use so the row is truthful and earns Sponsor Tech credit. |
| F6 | Trace file name and fields differed from the guide's recommended format (`logs/trace-<run_id>.jsonl`, `model` per request, `input_summary`/`output_summary`). Guide says logs should show Zetaris queries and Meterless Engine activity. | Technical Execution Guide §8 | Medium (judges read traces; `model` is the NVIDIA award evidence) | Architecture §6 adopts the guide's field names, adds Zetaris/H-MEM event logging, readable stdout lines, `...redacted` masking. `confidence` omitted rather than fabricated. |
| F7 | No per-call timeouts or run-length target. | Technical Execution Guide §5 | Medium | New PRD R16; architecture §6 lists Zetaris 30–60 s, Nightshift 30–90 s, iteration 1–3 min, full run 5–10 min. |
| F8 | Hosting: v3.2 kept a $15 hosting line and language about a "required reachable deployment." No organizer document requires hosted deployment; judges run locally or use sample mode. | Submission Requirements §3.3; Technical Execution Guide §4, §11 | Low | Architecture §8 makes one local integration laptop the default; hosting becomes contingency. Removes a topology decision from the critical path. |
| F9 | Docker status overstated as "strongly recommended by S5." The Open Agent guide says Docker *or* a documented setup that installs at build time. | Technical Execution Guide §1, §3 | Low | Plan §9 and architecture §8: CLI + documented venv/npm path is primary; Dockerfile from reserve only, with `host.docker.internal` and Linux notes. |
| F10 | Demo and deck requirements were implicit. The video has six required points; the deck has eight; README/deck/video must name the same track. | Submission Requirements §3.1–3.2; Form Preview §3.5–3.6 | Medium (Demo 15 points; deck is required) | PRD §8 enumerates the nine submission parts; plan §7 maps the six video points to the timeline and lists eight slides one-to-one. |
| F11 | Sponsor explanation structure not specified (four rows plus "what was unique"; one-liners are a listed common mistake). | Submission Requirements §3.4; Form Preview §6 | Medium (10 points) | PRD §3 specifies the structure; W10 acceptance is the completed worksheet. |
| F12 | `.env.example` variable names should match the guide so judges can paste setup-guide values directly. | Technical Execution Guide §6 | Low | Architecture §10 aligns names and adds `LOG_LEVEL`, `METERLESS_CRITIC_MODEL`, `METERLESS_CANDIDATE_MODELS`, `MAX_SPEND_USD`. |
| F13 | Responsible AI: output includes cost/margin figures; Rules ask for disclaimers on financial-sensitive use and stated limitations. | Rules §18 | Low | PRD §2 adds a one-line disclaimer requirement for decision pack and README. |
| F14 | Deadline arithmetic verified: October 27, 23:45 UTC = 6:45 p.m. CDT (US DST ends November 1). Judging October 28; results November 6, 16:00 UTC. | Rules §2 | None | Confirmed; dates added to PRD §2. |
| F15 | Repository layout not stated; guide suggests `app/adapters/`, `app/engines/`, `tests/`. | Technical Execution Guide §10 | Low | Architecture §1 adds the layout with the engine test path judges will look for. |

## 3. What was deliberately not changed

- Product scope (R01–R15), evaluation design (3 dev + 7 holdout), 23-call cap, three-role Planner/Analyst/Critic design, and the 32+8 hour allocation. These are team decisions and are compatible with every organizer requirement.
- Track choice. "The Agent That Can Explain Why" ($1,600/$1,200/$900) fits the evidence-backed recommendation design better than "Reasoning Architecture" ($1,500/$1,200/$900), and the fit argument is stronger on Impact (30 points, the tiebreaker).
- The NVIDIA award pursuit. It costs little beyond pinning a Nemotron route and logging `model`, which the guide asks for anyway.

## 4. Risks the documents cannot fix

The binding constraint is not document alignment. It is that no sponsor account exists, Zetaris needs a 16 GB laptop with Docker, the H-MEM bridge is Node called from Python, and 40 person-hours must cover setup, build, evaluation, founder sessions, video and submission. The plan's four-person-hour spine checkpoint on October 24 is the real decision gate. If the spine is not working by then, cut founder sessions and the seven-case holdout to five before cutting anything sponsor-visible, and say so in the README. A smaller truthful submission beats a larger one judges cannot run.

## 5. Tonight's decisions, in order

1. Confirm project name and one-sentence description (PRD header).
2. Collect HackOS emails and GitHub usernames; agree prize split; create the public repo.
3. Inventory anything created before October 22, 00:00 UTC for the declaration.
4. Decide who does real work in Cursor.
5. Verify the integration laptop's RAM/Docker allocation.
6. Select the track in HackOS.

Then stop planning and start the Zetaris install.
