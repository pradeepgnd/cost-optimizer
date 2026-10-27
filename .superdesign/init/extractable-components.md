# Extractable components

The current UI is a single Streamlit page. These functions are the available reusable visual sections; HTML structure and CSS selectors are internal to Streamlit and `STYLE` in `streamlit_app.py`.

## AppShell
- Source: `streamlit_app.py` (`main`)
- Category: layout
- Description: Composes the root page, sidebar, brief, run state, progress, and results.
- Extractable props: none currently; driven by Streamlit session state.
- Hardcoded: page structure, headings, action copy, CSS classes.

## Sidebar
- Source: `streamlit_app.py` (`sidebar`)
- Category: layout
- Description: Brand label, sample/live mode, example selection, and optional price-data override.
- Extractable props: selected mode, example, override path (session state).
- Hardcoded: labels, descriptions, brand wordmark.

## Hero
- Source: `streamlit_app.py` (`hero`)
- Category: layout
- Description: Brand-led masthead and product promise.
- Extractable props: none currently.
- Hardcoded: Cost.Advisor branding, title, explanatory copy.

## BriefForm
- Source: `streamlit_app.py` (`form`)
- Category: basic
- Description: Edits product idea, user, features, growth stages, assumptions, candidate models, approval and spend cap.
- Extractable props: form values and mode; Streamlit session keys.
- Hardcoded: field labels, helper copy, collapsible advanced sections.

## ProgressPipeline
- Source: `streamlit_app.py` (`pipeline_view`)
- Category: basic
- Description: Founder-facing Planner → Analyst → Critic stages with current progress and details.
- Extractable props: trace events, run summary.
- Hardcoded: phase labels and explanatory copy.

## Results
- Source: `streamlit_app.py` (`results`)
- Category: layout
- Description: Tabs for cost story, quality and Critic, risks and gaps, and trace/export.
- Extractable props: DecisionPack, mode, status, cost scenario.
- Hardcoded: tab names, trust explanations, empty states, disclosure copy.

## StageChart
- Source: `streamlit_app.py` (`stage_chart`)
- Category: basic
- Description: Altair stage-cost visualization using Bauhaus chart colors.
- Extractable props: dataframe, series column, value column.
- Hardcoded: chart styling and palette.
