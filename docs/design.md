# Cost Advisor — Product Design

Design system for the Streamlit DecisionPack UI (`streamlit_app.py` + `app/ui_service.py`).  
Stack stays Streamlit; all business rules stay in `run.py` / the controller. This doc is the visual and IA source of truth for redesign on branch `shrie-UI-ideas`.

Related: Project plan notes (store) · README Streamlit UI · `Planning/07-Realignment-v4.md`

---

## 1. Brand & voice

| | |
|---|---|
| **Name** | **Cost.Advisor** (UI) · AI SaaS Cost Advisor (docs/hackathon) |
| **Promise** | Know what your AI features cost at every growth stage — measured where we ran a model, labeled estimated otherwise. |
| **Audience** | Solo founders and hackathon judges who need a costed model stack, not a model beauty contest. |
| **Tone** | Precise, calm, ledger-honest. Short sentences. Prefer “measured / projected / unknown” over hype. |
| **Never say** | That the tool “saved” or “would have saved” dollars. Never invent confidence. Never sum operating + build ledgers. |
| **Brand test** | First viewport still reads as Cost.Advisor after removing the sidebar — brand is hero-level, not an eyebrow chip. |

---

## 2. Information architecture

One job per stage. Founder path is vertical; judge/sponsor depth is progressive disclosure.

```
Brief  →  Run  →  Results (DecisionPack)
  │         │         ├─ Cost story (default)
  │         │         ├─ Quality & Critic
  │         │         ├─ Risks & gaps
  │         │         └─ Trace & export (judges)
```

### Brief
1. Product idea + target user  
2. 2–5 AI features (interactive editor)  
3. Growth stages  
4. Assumptions (budget, revenue, switch threshold) — **collapsed**  
5. Advanced: optional candidate picks — **collapsed**  
6. Live only: evaluation approval + spend cap, directly above **Run**

### Run
Map live trace into three founder-facing phases (not a raw event dump as primary UI):

| Phase | Copy | Show |
|---|---|---|
| Planner | Domain risks for this idea | Risk lines as they arrive |
| Analyst | Prices, candidates, samples | Model request count; measured vs projected |
| Critic | Flags only — not grades | Finding count; no confidence scores |

Keep SAMPLE/OFFLINE unmistakable. Reused run IDs stay captioned as stored results (never re-spend).

### Results
1. **Headline** — one monthly AI trajectory for all features (R9 totals; scenario picker)  
2. **Per-feature cost by stage** — chart + table; *measured* vs *projected only*  
3. **Quality & Critic** — deterministic checks; Critic flags; empty state until human review (R7): *Recommendations locked until human review*  
4. **Risks & gaps** — unknowns stay unknown; build panel secondary/collapsed  
5. **Trace & export** — JSONL + pack download for judges  

Trust chrome (quiet, persistent): mode · snapshot id · spend used/cap · status.

---

## 3. Visual system

### Direction
**Cool ledger light** — paper/ink atmosphere with a soft grid or radial wash. Product imagery = stage cost curves and the Planner→Analyst→Critic strip. Not flat white, not neon cyber-dark, not purple-on-white, not cream+terracotta+serif, not broadsheet density.

### Color tokens

| Token | Value | Use |
|---|---|---|
| `--bg` | `#EEF1F5` | Page atmosphere |
| `--surface` | `#F8FAFC` | Interactive surfaces only |
| `--ink` | `#12151A` | Primary text |
| `--muted` | `#5A6570` | Captions, secondary |
| `--line` | `#C9D1DB` | Hairline rules / editor chrome |
| `--accent` | `#0F6B5C` | Primary actions, active step |
| `--accent-soft` | `#D5EDE8` | Selected tab / soft fill |
| `--warn` | `#8A5A00` | SAMPLE/OFFLINE, lower-bound notes |
| `--danger` | `#9B1C1C` | Stop / failed (text + icon, not color alone) |
| `--chart-1..4` | `#0F6B5C`, `#1F4E79`, `#6B5B3E`, `#5A6570` | Altair series (colorblind-safer) |

Contrast target: body text ≥ 4.5:1 on `--bg` / `--surface` ([Colorable](https://colorable.jxnblk.com/), [Contrast](https://usecontrast.com/) — see §6).

### Typography

| Role | Face | Notes |
|---|---|---|
| Display / brand | **Sora** 600–700 | Hero brand + section titles; not Inter/Roboto/system |
| Body | **Source Sans 3** 400–600 | Forms, captions, tables |
| Figures | **IBM Plex Mono** 500 | USD, tokens, run IDs |

Streamlit: set via `.streamlit/config.toml` `font` / `headingFont` Google Fonts URLs (same pattern as today’s Manrope load).

### Spacing & radius
- Page max width ~1120–1280px; top padding modest (brand first, not a tall black slab).  
- Vertical rhythm: 8 / 16 / 24 / 40.  
- Radius: **8–12px** on interactive controls. Avoid `full`/pill chrome for tabs and buttons.  
- Section titles: number + title + one hint line (keep current step pattern; restyle markers).

### Motion (exactly three)
1. Run phases light in sequence (Planner → Analyst → Critic).  
2. Stage cost line draws left→right when Results open.  
3. SAMPLE/OFFLINE banner settles once.  

Respect `prefers-reduced-motion` (skip 1–2; keep final semantic state). No ambient glow, particles, or looping neon.

### Component rules
- **Default: no cards.** No bordered “metric cards,” no hero media cards, no decorative `st.container(border=True)` around static copy.  
- **Cards/borders only** for interaction: feature `data_editor`, spend approval block, primary **Run**.  
- **Tabs:** underline or soft rectangular selected state — not pill capsules.  
- **Icons:** SVG (Lucide/Heroicons), never emoji-as-icon.  
- **Charts:** Altair line+point; stages in growth order; tooltip shows USD + measured/estimated basis.

---

## 4. Streamlit implementation notes

| Concern | Do |
|---|---|
| Boundary | UI builds `RunRequest` → `ui_service.submit_run` → `run.py`. No economics/dispatch in the front end. |
| Theme | Replace lime/dark tokens in `.streamlit/config.toml`; restyle `STYLE` in `streamlit_app.py`. |
| Hero | Brand name largest; one sentence; **no** capability pill row; **no** glow eyebrow. CTA = form + Run. |
| Progress | Primary UI = three-phase timeline from `progress_rows` / trace `agent_name`; raw table under expander. |
| Results | Open on totals + one feature chart; demote four `st.metric` tiles to one status line. |
| Labels | Founder language on tabs: *Cost by stage* · *Will it pass checks?* · *What we still don’t know* · *Show your work*. |
| Mode | SAMPLE/OFFLINE banner uses `--warn`; live never displays secret values from `.env`. |
| Persistence | One run ID → one stored result under `data/ui/` (unchanged). |
| Tests | Keep `tests/test_streamlit_app.py` + `tests/test_ui_service.py` green after CSS/copy changes. |
| Restart | After theme/module edits, restart Streamlit (cached imports). |

Launch: `python -m streamlit run streamlit_app.py`

---

## 5. Inspiration & tooling (distilled)

Not an awesome-list dump — only what we use.

### [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- Generate/persist a **MASTER** design system (colors, type, spacing, anti-patterns) and keep page overrides thin — this `docs/design.md` plays that role for Cost.Advisor.  
- Adopt its **pre-delivery habits**: no emoji icons; contrast ≥ 4.5:1; respect reduced motion; don’t encode meaning in color alone.  
- Explicit **anti-patterns** we inherit: bright neon accents, harsh animation, default AI purple/pink gradients, dark-mode-as-default cyber look.  
- Chart domain guidance: prefer clear multi-series lines for stage cost (already Altair); avoid ornamental 3D.

### [Awesome Design Tools](https://github.com/goabstract/Awesome-Design-Tools)
Use when validating or extending tokens — cite the category, pick one tool:

| Need | Tool |
|---|---|
| Contrast | [Colorable](https://colorable.jxnblk.com/), [Contrast](https://usecontrast.com/) |
| Accessible palettes | [ColorBox](http://www.colorbox.io/), [Accessible Palette Builder](https://toolness.github.io/accessible-color-matrix/) |
| Color-blind check | [Color Oracle](https://colororacle.org/) |
| Palette exploration | [Coolors](https://coolors.co/), [Viz Palette](https://projects.susielu.com/viz-palette) (charts) |
| Type pairing inspo | [Typewolf](https://www.typewolf.com/) (then lock choices in §3 — don’t keep exploring mid-ship) |

---

## 6. Checklist vs current lime-on-black UI

Current baseline (`.streamlit/config.toml` + `STYLE`): near-black `#050505`, lime `#8cff2e`, Manrope, pill tabs, glow eyebrow, capability pills, metric cards, bordered step containers.

| Target | Current | Redesign |
|---|---|---|
| Brand-first first viewport | Eyebrow pill + long headline; brand in sidebar | Brand wordmark hero-level; one sentence; no pills |
| Atmosphere | Flat black + neon wash | Cool ledger light (`--bg` / soft wash) |
| Accent | Lime `#8cff2e` + glow | Teal ink `#0F6B5C`, no glow |
| Type | Manrope only | Sora + Source Sans 3 + IBM Plex Mono |
| Cards | Metrics + bordered steps + dark wrappers | Only feature editor / spend / Run |
| Tabs | Pill capsule selected lime | Soft rect / underline |
| Hero capability chips | Four pills under hero | Remove |
| Run UX | Flat trace dataframe primary | Planner → Analyst → Critic timeline |
| Results | Four metrics + five equal tabs | Cost story first; metrics → status line |
| SAMPLE labeling | `st.warning` | Persistent `--warn` trust chrome |
| Motion | Tab hover only | Three intentional motions above |
| A11y | Neon-on-black risk | ≥4.5:1; Color Oracle pass; no color-only status |
| Human review (R7) | Caption only | Explicit locked empty state for recommendations |
| Build panel | Expander (good) | Keep secondary; never visual-sum with OpEx |

**Done when:** a judge can sample-mode example → Run → read stage cost + SAMPLE in under two minutes, and the first viewport fails the “could be any AI app” test.
