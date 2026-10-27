# Cost Advisor — Hyper-Saturated Fluid

## Product and audience
Cost.Advisor helps solo founders and hackathon judges understand monthly AI feature costs at each growth stage. It turns a founder's product brief into a costed model stack. Keep the tone precise, calm, and evidence-led. The UI must distinguish measured values, projected values, assumptions, and unknowns. Never claim dollars saved, invent confidence scores, or combine operating costs with build costs.

## Full-page information architecture
This is a complete redesign of the existing single-page `/` Streamlit interface, not a marketing landing page or generic fintech dashboard. Keep every part of the real product visible in one coherent, vertically scrollable page:

1. A compact brand/control rail and a dominant hero with the Cost.Advisor wordmark and its promise: know what AI features cost as usage grows.
2. The founder brief: product idea, target user, 2–5 editable AI feature rows, modality and usage assumptions, and editable growth stages.
3. Collapsible budget/revenue/switch-threshold assumptions and optional candidate-model selection.
4. Evaluation spend approval and maximum spend directly before the Run action. Make sample mode's no-model/no-network behavior unmistakable.
5. Run state and a three-part Planner → Analyst → Critic progress path; the Critic flags issues and never grades candidates.
6. Results with four complete views: cost by stage (overall monthly scenario and feature cost curves/tables, measured versus projected tokens), deterministic checks and Critic flags, unknowns/risks/evidence gaps with a secondary build-cost panel, and trace plus JSON/JSONL downloads.
7. Persistent trust details for mode, status, spend, and model-request count. Preserve empty, pending, incomplete, sample, and live states without fabricating data.

The reference UI and behavior are in `streamlit_app.py`. Preserve the existing labels and core logic. Do not add payment wallets, fabricated financial balances, unsupported awards, partner claims, or fictional model results. Any example values must be visibly labeled as sample placeholders.

## Visual direction: Hyper-Saturated Fluid
The user's supplied design system is the visual source of truth for the redesign. This direction intentionally replaces the previous Bauhaus look. Do not reuse its flat off-white canvas, red/blue/yellow primary palette, heavy black seams, square cards, or circular Run button.

- Core concept: high-contrast fluidity; premium fintech polish applied to an AI cost-planning product.
- Palette only: Cyber Yellow `#FDE047` (dominant shout color); Deep Onyx `#0A0A0A`; Charcoal `#171717`; Deep Gray `#262626`; Pure White `#FFFFFF`. Keep yellow flat with no gradient. Use yellow for the large hero surface and key value highlights, with onyx/charcoal void sections balancing it.
- Layout: asymmetrical organic transitions between yellow hero and dark sections. Use large flowing curves or clipped waves rather than straight horizontal section bands. Keep the page structured and highly usable despite the sculptural transitions.
- Typography: Inter (preferred) or General Sans. Oversized, bold, tight-tracked hero headline; clear medium subheads; small functional body labels; tiny uppercase tracking-wide metadata. Keep form labels and data legible.
- Shape: organic liquid cuts for major sections; pill buttons and badges; glass panels around data (32px radius, translucent white, 1px white border at 20% opacity, strong backdrop blur). Soft shadows may lift glass panels. Do not use standard small radii.
- Interaction: elastic upward entrance, subtle slow card drift, and button squish on press. Keep motion restrained and respect reduced-motion preferences.
- The main call to action should be a confident dark or yellow pill. No red/blue palette and no Bauhaus decoration.
- Keep information density intentional: make the hero breathe, then make forms and cost data compact and scannable. Use glass cards for meaningful figures and chart groupings, not every input row.
- At narrow widths, collapse the control rail, stack forms and results, preserve every section, and avoid horizontal overflow.

## Content and trust rules
Keep the product name `Cost.Advisor`. Keep measured/projected/unknown labels explicit. Preserve `SAMPLE/OFFLINE`; do not imply sample figures are real or that models ran. Preserve the “Critic only flags” meaning, human-review lock, lower-bound explanations, and separate build-cost disclosure. Use real product integrations only when supported by the source; no invented partner-logo ticker. Prefer text and charts to decorative stock imagery. Use no invented logo mark; a text wordmark is appropriate because the source has no logo asset.

## Source precedence
For page structure and behavior, read `streamlit_app.py`. For redesign styling, follow this file and the user's Hyper-Saturated Fluid brief. Source CSS values in `streamlit_app.py` describe the old baseline only and must not constrain the redesign.
