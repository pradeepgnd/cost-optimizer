# Routes

## `/` — Cost.Advisor single-page application

- Entry: `streamlit_app.py`
- Runtime: Streamlit, launched through `streamlit run streamlit_app.py` (project entry documentation in `README.md`).
- Layout: wide Streamlit page; built-in sidebar from `sidebar()`; main area from `main()`.
- URL routing: none; all interaction and results are on the root page.
- UI service boundary: `app/ui_service.py`; builds and validates requests, submits runs to `run.py`, reads traces/results, and exposes example/setup helpers. Business logic remains outside the UI.
