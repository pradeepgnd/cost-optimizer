# Hackathon deck — speaker notes (Track 02)

**File:** `docs/hackathon-deck.pptx` (9 slides)  
**Spoken target:** **~3:15** (video/demo band **2:30–3:30**, hard cap **4:00**)  
**Rules sources:** `/cursor/stores/self/internal/hackathon-requirements.md` · `docs/DEMO_SCRIPT.md` · `docs/README_SUMMARY.md` · `docs/SPONSOR_PARAGRAPH.md`  
**Not our product:** ChurnWhy / SupplyLens / TriageDesk (illustrative examples only).

**Scoring (100):** Impact 30 · Technical 20 · Innovation 15 · Demo 15 · Product & UX 10 · Sponsor Tech 10

**Eight required deck points → slides:** 1 problem/users · 2 solution · 3 workflow · 4 stack · 5 Zetaris+Meterless(+NVIDIA) · 6 unique · 7 visuals (two slides) · 8 future

| # | Slide | Time | Must hit |
|---|---|---|---|
| 1 | Track + problem + users (+ scoring footnote) | **0:00–0:20** | Track name matches README; user + pain in ≤2 sentences |
| 2 | Solution I/O | **0:20–0:40** | Input/process/output; sample vs live; why output is useful; no “savings” |
| 3 | Agent workflow | **0:40–1:05** | ≥2 agents; Critic→controller→repair loop; H-MEM shared state |
| 4 | Stack | **1:05–1:15** | run.py, Streamlit, Zetaris, Nightshift, H-MEM, Nemotron; public repo |
| 5 | Sponsors at work | **1:15–1:40** | Zetaris query+writeback; H-MEM feature+test; one Nightshift request; Nemotron IDs |
| 6 | Unique sponsor use | **1:40–1:55** | Per-request Nightshift scopes after shared-scope leak |
| 7a | Visuals Brief→Run | **1:55–2:15** | Real UI; approval/cap; run starting |
| 7b | Visuals Results | **2:15–2:45** | Final DecisionPack; measured vs estimated; trace; impact |
| 8 | Future + close | **2:45–3:15** | Unbuilt next steps; repo; SAMPLE_MODE; sponsors |

**Total ~3:15.** Optional +10s: DEMO_SCRIPT Nightshift scope line if under 3:30. Never show secrets.
