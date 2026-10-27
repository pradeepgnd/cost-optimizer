# Page dependency trees

## `/` — Cost.Advisor (Brief → Run → Results)

Entry: `streamlit_app.py` (`main()`)

Dependencies:
- `streamlit_app.py`
  - `style()` — injects CSS tokens and component styling
  - `hero()` — product masthead and explanatory text
  - `sidebar()` — sample/live mode and example selection
  - `form()` — idea, target user, features, stages, assumptions, candidates, approvals, and spend cap
  - `pipeline_view()` — Planner → Analyst → Critic progress
  - `results()`
    - `totals_view()` — monthly total scenario and stage trajectory
    - `cost_rows()` — per-feature cost records
    - `stage_chart()` — Altair visualization
    - quality/checks, Critic flags, risks/gaps, trace, and exports
  - `app/ui_service.py` (`app as svc`)
    - template loading and request assembly/validation
    - `submit_run()` runs `run.py` once per run ID and streams trace progress
    - results, setup hints, and example discovery
  - `run.py` — application entry point behind `ui_service.submit_run()`

The page is a single Streamlit script; it has no file-based frontend router, CSS files, or separately imported page components. Reusable helpers are documented with their full source in `components.md`.
