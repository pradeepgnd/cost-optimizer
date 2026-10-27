# Theme and design tokens

## Compact token summary

Source of truth: `docs/design.md` and `STYLE` in `streamlit_app.py`. Direction is Bauhaus: flat off-white, black, red, blue, and yellow planes; square corners; heavy black seams; no gradients, glow, soft shadow, glass, or ambient animation.

- Colors: ground `#f5f4ee`; ink `#000000`; accent / primary action `#ff0000`; field / secondary action and active phase `#0000ff`; field support / done phase `#ffff00`; quiet panels/sidebar `#e8e8e8`; on field `#ffffff`.
- Typography: `"Bauhaus Host", "Host Grotesk", sans-serif`; display 800; action 750; label 650 at 15px; reading 450 at 17–18px with 1.5 line height; caption 14px.
- Spacing: content gutter `clamp(22px, 4.45cqi, 72px)`; content max width 1180px.
- Corners: square (`0`); circular primary run action (`50%`).
- Borders: strong 4px, compact 3px; primary Run uses hard `6px 6px 0 #000000` offset shadow.
- Motion: instant (`0s`); no ambient animation; respect reduced motion.
- Chart colors: `#ff0000`, `#0000ff`, `#ffff00`, `#000000`.

## Raw style source

Full CSS assigned to `STYLE` in `streamlit_app.py`:

```css

<style>
@import url('https://fonts.googleapis.com/css2?family=Host+Grotesk:wght@400;450;500;650;700;750;800&display=swap');
:root {
  --dp-color-ground: #f5f4ee;
  --dp-color-ink: #000000;
  --dp-color-accent: #ff0000;
  --dp-color-field: #0000ff;
  --dp-color-field-support: #ffff00;
  --dp-color-quiet: #e8e8e8;
  --dp-color-on-field: #ffffff;
  --dp-typography-face: "Bauhaus Host", "Host Grotesk", sans-serif;
  --dp-typography-body: 18px;
  --dp-typography-reading: 17px;
  --dp-typography-label: 15px;
  --dp-typography-caption: 14px;
  --dp-typography-weight-display: 800;
  --dp-typography-weight-action: 750;
  --dp-typography-weight-label: 650;
  --dp-typography-weight-reading: 450;
  --dp-typography-reading-leading: 1.5;
  --dp-spacing-gutter: clamp(22px, 4.45cqi, 72px);
  --dp-radius-square: 0;
  --dp-radius-circle: 50%;
  --dp-border-rule: 4px;
  --dp-border-compact: 3px;
  --dp-motion-interaction: 0s;
}
html, body, [class*="css"], .stApp {
  font-family: var(--dp-typography-face);
  font-size: var(--dp-typography-body);
  font-weight: var(--dp-typography-weight-reading);
  color: var(--dp-color-ink);
  background: var(--dp-color-ground) !important;
}
.stApp { background: var(--dp-color-ground) !important; }
h1, h2, h3, .ca-brand-hero, .ca-brand, .ca-step div, .ca-phase strong {
  font-family: var(--dp-typography-face);
  font-weight: var(--dp-typography-weight-display);
  letter-spacing: -0.03em;
  color: var(--dp-color-ink);
}
.ca-mono, code, pre { font-family: var(--dp-typography-face) !important; font-weight: 650; }
.block-container {
  padding-top: 1.5rem;
  padding-left: var(--dp-spacing-gutter);
  padding-right: var(--dp-spacing-gutter);
  max-width: 1180px;
}
section[data-testid="stSidebar"] {
  background: var(--dp-color-quiet) !important;
  border-right: var(--dp-border-rule) solid var(--dp-color-ink) !important;
  min-width: 15rem !important;
  max-width: 18rem !important;
}
section[data-testid="stSidebar"] > div { background: var(--dp-color-quiet) !important; }
.ca-hero {
  position: relative; overflow: hidden;
  padding: 1.5rem 0 1.25rem; margin-bottom: 1rem;
  background: var(--dp-color-ground);
  border-bottom: var(--dp-border-rule) solid var(--dp-color-ink);
  border-radius: var(--dp-radius-square);
}
.ca-brand-hero {
  font-size: clamp(2.4rem, 5vw, 3.6rem); line-height: 1; font-weight: var(--dp-typography-weight-display);
  margin: 0 0 .65rem; color: var(--dp-color-ink);
}
.ca-brand-hero span { color: var(--dp-color-accent); }
.ca-hero p {
  color: var(--dp-color-ink); font-size: var(--dp-typography-reading);
  font-weight: var(--dp-typography-weight-reading); line-height: var(--dp-typography-reading-leading);
  max-width: 52ch; margin: 0;
}
.ca-sample {
  margin: 0 0 1rem; padding: .75rem 1rem;
  background: var(--dp-color-field-support); color: var(--dp-color-ink);
  border: var(--dp-border-rule) solid var(--dp-color-ink); border-radius: var(--dp-radius-square);
  font-size: var(--dp-typography-label); font-weight: var(--dp-typography-weight-label);
  transition: none; animation: none;
}
.ca-step { display: flex; align-items: stretch; gap: 0; margin: .25rem 0 1rem; border: var(--dp-border-rule) solid var(--dp-color-ink); }
.ca-step b {
  display: inline-grid; place-items: center; min-width: 2.75rem; padding: .55rem .4rem;
  background: var(--dp-color-field-support); color: var(--dp-color-ink);
  border-right: var(--dp-border-rule) solid var(--dp-color-ink); border-radius: var(--dp-radius-square);
  font-weight: var(--dp-typography-weight-display); font-size: var(--dp-typography-label);
}
.ca-step div {
  flex: 1; padding: .55rem .85rem; background: var(--dp-color-field-support);
  font-size: 1.15rem; font-weight: var(--dp-typography-weight-display); line-height: 1.15;
}
.ca-step small {
  display: block; margin-top: .2rem; color: var(--dp-color-ink);
  font-size: var(--dp-typography-caption); font-weight: var(--dp-typography-weight-reading);
  letter-spacing: 0; line-height: var(--dp-typography-reading-leading);
}
.ca-brand {
  font-size: 1.15rem; font-weight: var(--dp-typography-weight-display);
  margin-bottom: .4rem; color: var(--dp-color-ink);
}
.ca-brand span { color: var(--dp-color-accent); }
.ca-status {
  margin: 0 0 1rem; padding: .65rem .85rem;
  background: var(--dp-color-quiet); color: var(--dp-color-ink);
  border: var(--dp-border-compact) solid var(--dp-color-ink); border-radius: var(--dp-radius-square);
  font-size: var(--dp-typography-label); font-weight: var(--dp-typography-weight-reading);
}
.ca-status b { font-weight: var(--dp-typography-weight-label); }
.ca-trust { font-size: var(--dp-typography-caption); color: var(--dp-color-ink); margin: .25rem 0 .75rem; }
.ca-pipeline {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0;
  margin: .5rem 0 1rem; border: var(--dp-border-rule) solid var(--dp-color-ink);
}
.ca-phase {
  padding: .85rem 1rem; background: var(--dp-color-quiet); border-radius: var(--dp-radius-square);
  border-right: var(--dp-border-compact) solid var(--dp-color-ink);
  transition: none; animation: none;
}
.ca-phase:last-child { border-right: none; }
.ca-phase[data-state="pending"] { opacity: .45; }
.ca-phase[data-state="active"] { background: var(--dp-color-field); color: var(--dp-color-on-field); }
.ca-phase[data-state="active"] strong,
.ca-phase[data-state="active"] span,
.ca-phase[data-state="active"] em { color: var(--dp-color-on-field); }
.ca-phase[data-state="done"] { background: var(--dp-color-field-support); }
.ca-phase strong {
  display: block; font-size: var(--dp-typography-label);
  font-weight: var(--dp-typography-weight-display); margin-bottom: .25rem;
}
.ca-phase span {
  display: block; font-size: var(--dp-typography-caption);
  font-weight: var(--dp-typography-weight-reading); line-height: 1.35;
}
.ca-phase em {
  display: block; margin-top: .45rem; font-style: normal;
  font-size: var(--dp-typography-caption); font-weight: var(--dp-typography-weight-label);
}
.ca-locked {
  margin: .75rem 0; padding: .75rem 1rem;
  border: var(--dp-border-compact) solid var(--dp-color-ink); border-radius: var(--dp-radius-square);
  background: var(--dp-color-quiet); color: var(--dp-color-ink);
  font-size: var(--dp-typography-reading); font-weight: var(--dp-typography-weight-reading);
}
.ca-chart-wrap { animation: none; }
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--dp-radius-square) !important;
  background: var(--dp-color-quiet) !important;
  border: var(--dp-border-rule) solid var(--dp-color-ink) !important;
}
div[data-testid="stTabs"] [role="tablist"] {
  gap: 0; padding: 0; border-radius: 0; background: transparent;
  border: none; border-bottom: var(--dp-border-rule) solid var(--dp-color-ink);
  width: 100%; margin-bottom: 1rem;
}
div[data-testid="stTab"] {
  border-radius: var(--dp-radius-square); padding: .55rem 1rem;
  background: var(--dp-color-quiet); border: var(--dp-border-compact) solid var(--dp-color-ink);
  border-bottom: none; margin-right: -3px; transition: none;
}
div[data-testid="stTab"]:hover { background: var(--dp-color-field-support); }
div[data-testid="stTab"][aria-selected="true"] {
  background: var(--dp-color-field); border-color: var(--dp-color-ink);
}
div[data-testid="stTab"][aria-selected="true"] p {
  color: var(--dp-color-on-field) !important; font-weight: var(--dp-typography-weight-label);
}
button[data-testid="stBaseButton-primary"] {
  border-radius: var(--dp-radius-circle) !important;
  min-width: 4.75rem !important; min-height: 4.75rem !important;
  padding: .85rem !important;
  background: var(--dp-color-accent) !important;
  border: var(--dp-border-rule) solid var(--dp-color-ink) !important;
  box-shadow: 6px 6px 0 var(--dp-color-ink) !important;
  transition: none !important;
}
button[data-testid="stBaseButton-primary"]:hover {
  box-shadow: 4px 4px 0 var(--dp-color-ink) !important;
  transform: translate(2px, 2px);
}
button[data-testid="stBaseButton-primary"] p {
  color: var(--dp-color-on-field) !important; font-weight: var(--dp-typography-weight-action) !important;
}
button[data-testid="stBaseButton-secondary"],
button[kind="secondary"] {
  border-radius: var(--dp-radius-square) !important;
  background: var(--dp-color-field) !important;
  color: var(--dp-color-on-field) !important;
  border: var(--dp-border-compact) solid var(--dp-color-ink) !important;
  box-shadow: none !important; transition: none !important;
}
button[data-testid="stBaseButton-secondary"] p { color: var(--dp-color-on-field) !important; font-weight: var(--dp-typography-weight-action) !important; }
*:focus-visible {
  outline: var(--dp-border-compact) solid var(--dp-color-field) !important;
  outline-offset: 2px !important;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important; transition: none !important; scroll-behavior: auto !important;
  }
  button[data-testid="stBaseButton-primary"]:hover { transform: none; }
}
@media (max-width: 720px) {
  .ca-pipeline { grid-template-columns: 1fr; }
  .ca-phase { border-right: none; border-bottom: var(--dp-border-compact) solid var(--dp-color-ink); }
  .ca-phase:last-child { border-bottom: none; }
  .ca-hero { padding: 1.1rem 0 .9rem; }
  section[data-testid="stSidebar"] { max-width: 100% !important; min-width: 100% !important; }
}
</style>

```

## Design reference

```markdown
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

```
