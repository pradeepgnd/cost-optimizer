# Cost Advisor — Product Design

Design system for the Streamlit DecisionPack UI (`streamlit_app.py` + `app/ui_service.py`).  
Stack stays Streamlit; all business rules stay in `run.py` / the controller. This doc is the visual and IA source of truth for redesign on branch `shrie-UI-ideas`.

**Direction note (Oct 2026):** the shipped visual system is **Bauhaus** (flat off-white / black / red / blue / yellow). It supersedes the earlier “cool ledger light” teal proposal on this branch; Brief → Run → Results IA is unchanged.

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
**Bauhaus** — flat planes of off-white, black, red, blue, yellow; heavy black seams; square corners; no gradients, glow, soft shadow, or glass. Rare circular primary actions use a hard black offset shadow. Yellow heading blocks, blue secondary actions, red primary CTA. Unequal sidebar/main split where Streamlit allows. Product imagery remains stage cost curves and the Planner→Analyst→Critic strip.

### Color tokens

| Token | Value | Use |
|---|---|---|
| `--dp-color-ground` | `#f5f4ee` | Page ground |
| `--dp-color-ink` | `#000000` | Text, seams, rules |
| `--dp-color-accent` | `#ff0000` | Primary CTA, brand dot |
| `--dp-color-field` | `#0000ff` | Active phase, selected tab, secondary buttons |
| `--dp-color-field-support` | `#ffff00` | Heading blocks, SAMPLE banner, done phase |
| `--dp-color-quiet` | `#e8e8e8` | Sidebar, quiet panels |
| `--dp-color-on-field` | `#ffffff` | Text on red/blue fields |
| Charts | `#ff0000`, `#0000ff`, `#ffff00`, `#000000` | Altair series |

Contrast: black on ground/yellow ≥ 4.5:1; white on red/blue for field labels. Do not encode status by color alone (keep text labels).

### Typography

| Role | Face / size / weight | Notes |
|---|---|---|
| Face | **Bauhaus Host**, then **Host Grotesk**, then `sans-serif` | Host Grotesk (Google Fonts) is the loaded web stand-in when Bauhaus Host is unavailable |
| Display | 800 | Brand + section titles (compact, heavy) |
| Action | 750 | Buttons |
| Label | 650 · 15px | Steps, tabs, SAMPLE |
| Reading | 450 · 17–18px · leading 1.5 | Body copy |
| Caption | 14px | Trust chrome, hints |

Streamlit loads Host Grotesk via `.streamlit/config.toml` + `@import` in `STYLE`.

### Spacing, radius, border, motion
- Gutter: `clamp(22px, 4.45cqi, 72px)`.
- Radius: **0** (square); primary Run uses **50%** circle only.
- Rules: **4px** seams / **3px** compact.
- Motion: `--dp-motion-interaction: 0s` (instant). Respect `prefers-reduced-motion` (no transform on hover). No ambient animation.

### Component rules
- **Default: no soft cards.** Heavy black borders only on interactive surfaces: feature editor, spend block, Run.
- **Tabs:** square selected blue field — not pills.
- **SAMPLE banner:** yellow field + 4px black rule.
- **Primary Run:** red circle, 4px black border, hard `6px 6px 0` black offset shadow.
- **Secondary (New run):** blue square field.
- **Charts:** Altair line+point; stages in growth order; Bauhaus chart colors.

---

## 4. Streamlit implementation notes

| Concern | Do |
|---|---|
| Boundary | UI builds `RunRequest` → `ui_service.submit_run` → `run.py`. No economics/dispatch in the front end. |
| Theme | Bauhaus tokens in `.streamlit/config.toml` + `STYLE` CSS variables (`--dp-*`). |
| Hero | Brand name largest; one sentence; black seam under hero; CTA = form + circular red Run. |
| Progress | Primary UI = three-phase timeline from `progress_rows` / trace `agent_name`; raw table under expander. |
| Results | Open on totals + one feature chart; demote four `st.metric` tiles to one status line. |
| Labels | Founder language on tabs: *Cost by stage* · *Will it pass checks?* · *What we still don’t know* · *Show your work*. |
| Mode | SAMPLE/OFFLINE banner is yellow field + black rule; live never displays secret values from `.env`. |
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

## 6. Checklist vs prior themes

Prior on this branch: cool ledger teal/light, then lime-on-black. Target now: Bauhaus flat planes.

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
