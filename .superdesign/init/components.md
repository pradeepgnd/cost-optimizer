# UI components and reusable helpers

Framework: Streamlit (Python), with UI code co-located in `streamlit_app.py`; there is no separate component directory or JS component library. These functions are the reusable visual primitives and page sections. Full function source follows.

## `style` — `streamlit_app.py`

Reusable UI/helper function.

```python
def style():
    st.markdown(STYLE, unsafe_allow_html=True)
```

## `hero` — `streamlit_app.py`

Reusable UI/helper function.

```python
def hero():
    st.markdown(
        """<div class="ca-hero"><div class="ca-brand-hero">Cost<span>.</span>Advisor</div>
<p>Know what your AI features cost at every growth stage — measured where a model ran, labeled estimated otherwise.</p>
</div>""",
        unsafe_allow_html=True,
    )
```

## `step` — `streamlit_app.py`

Reusable UI/helper function.

```python
def step(number: int, title: str, hint: str = ""):
    st.markdown(
        f'<div class="ca-step"><b>{number:02d}</b><div>{title}'
        + (f"<small>{hint}</small>" if hint else "")
        + "</div></div>",
        unsafe_allow_html=True,
    )
```

## `stage_chart` — `streamlit_app.py`

Reusable UI/helper function.

```python
def stage_chart(frame: pd.DataFrame, series: str, value: str):
    """Monthly cost per stage, one line per series; stages stay in growth order (a plain line chart sorts them A-Z)."""
    order = list(dict.fromkeys(frame["stage"]))
    chart = (
        alt.Chart(frame.dropna(subset=[value]))
        .mark_line(point=True, strokeWidth=2.5)
        .encode(
            x=alt.X("stage:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{value}:Q", title="USD per month"),
            color=alt.Color(
                f"{series}:N",
                title=None,
                scale=alt.Scale(range=CHART_COLORS),
                legend=alt.Legend(orient="bottom", columns=2, labelLimit=460),
            ),
            tooltip=["stage", series, alt.Tooltip(f"{value}:Q", format=",.2f")],
        )
    )
    st.markdown('<div class="ca-chart-wrap">', unsafe_allow_html=True)
    st.altair_chart(chart, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)
```

## `num` — `streamlit_app.py`

Reusable UI/helper function.

```python
def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
```

## `banner` — `streamlit_app.py`

Reusable UI/helper function.

```python
def banner(pack: dict | None, sample: bool):
    if (pack or {}).get("execution_mode") == "sample" or (pack is None and sample):
        st.markdown(
            '<div class="ca-sample" role="status">SAMPLE/OFFLINE: no network calls, no model executed. '
            "Tokens are estimated and nothing here is measured.</div>",
            unsafe_allow_html=True,
        )
```

## `sidebar` — `streamlit_app.py`

Reusable UI/helper function.

```python
def sidebar() -> tuple[str, bool, str]:
    with st.sidebar:
        st.markdown('<div class="ca-brand">Cost<span>.</span>Advisor</div>', unsafe_allow_html=True)
        mode = st.radio("Mode", ["Sample (offline)", "Live (Nightshift + Zetaris)"], key="mode")
        sample = mode.startswith("Sample")
        st.caption(
            "Sample makes zero network calls."
            if sample
            else "Live needs Zetaris, Nightshift and `.env`. Spend is capped by the approved limit below."
        )
        example = st.selectbox("Start from example", svc.list_examples(), key="example")
        st.caption("Examples are the starting point; every number is an editable assumption.")
        bindings = ""
        if not sample:
            with st.expander("Override price data file"):
                override = st.text_input(
                    "Zetaris bindings file",
                    "",
                    key="bindings",
                    help="Leave empty to use ZETARIS_BINDINGS_FILE from .env.",
                )
            found = svc.find_bindings(override)
            if found["ok"]:
                counts = found["counts"]
                st.success(
                    f"Price data: snapshot `{found['snapshot_id'][:8]}`, {counts.get('models', '?')} models, "
                    f"{counts.get('catalog', '?')} catalog rows (from {found['source']})"
                )
                bindings = found["path"]
            else:
                st.error(
                    "Price data not found: "
                    + found["problem"]
                    + (f" ({found['path']})" if found["path"] else "")
                )
    return example, sample, bindings
```

## `form` — `streamlit_app.py`

Reusable UI/helper function.

```python
def form(example: str, sample: bool, bindings: str):
    template = svc.load_template(example)
    brief = template["brief"]
    key = lambda name: f"{example}:{name}"

    step(1, "Brief", "Idea, features, and growth assumptions")
    idea = st.text_area("Product idea", brief["product_concept"], key=key("idea"), height=90)
    user = st.text_input("Target user", brief["target_user"], key=key("user"))

    st.caption(
        "2 to 5 AI features. Modality: any of "
        + ", ".join(svc.MODALITIES)
        + " (comma-separated). Usage values are assumptions. Audio and image features are priced, not executed."
    )
    with st.container(border=True):
        rows = pd.DataFrame(
            [
                {
                    "feature_id": f["feature_id"],
                    "description": f["description"],
                    "example_input": f["example_input"],
                    "mode": f["mode"],
                    "modality": ", ".join(f["modality"]),
                    "uses_per_user_month": str(f["uses_per_user_month"]),
                }
                for f in brief["ai_features"]
            ]
        )
        features = st.data_editor(
            rows,
            num_rows="dynamic",
            width="stretch",
            key=key("features"),
            column_config={"mode": st.column_config.SelectboxColumn(options=["interactive", "background"])},
        )

    st.markdown("**Growth stages** (assumed)")
    stages = st.data_editor(
        pd.DataFrame(brief["growth_stages"])[["name", "active_users"]],
        num_rows="dynamic",
        width="stretch",
        key=key("stages"),
    )

    usage = brief.get("usage") or {}
    with st.expander("Assumptions (budget, revenue, switch threshold)", expanded=False):
        left, right = st.columns(2)
        threshold = left.text_input(
            "Switch threshold (USD/month)", str(brief.get("switch_threshold_usd", "100")), key=key("thr")
        )
        ceiling = right.text_input(
            "Monthly AI budget ceiling (USD, optional)", brief.get("monthly_ai_budget_usd") or "", key=key("ceil")
        )
        left, right = st.columns(2)
        price = left.text_input(
            "Price per paying user per month (USD, optional)",
            str(usage.get("subscription_price_usd") or ""),
            key=key("price"),
            help="With the paying fraction, gives revenue per stage. Assumed.",
        )
        fraction = right.text_input(
            "Paying fraction of active users (0 to 1, optional)",
            str(usage.get("paying_fraction") or ""),
            key=key("fraction"),
            help="e.g. 0.08 for 8% of active users paying. Assumed.",
        )

    with st.expander("Advanced: candidate models (optional)", expanded=False):
        st.caption("Leave empty to let the app choose per feature.")
        options = svc.candidate_options(sample, bindings)
        picks = st.multiselect(
            "Choose up to 3, at most one per tier (frontier, mid-tier, open-source).",
            list(options),
            format_func=lambda mid: options.get(mid, mid),
            max_selections=3,
            key=f"picks:{'sample' if sample else 'live'}",
        )
        if picks:
            st.caption(
                "Your picks replace the automatic choice for every feature. A pick that can't handle a feature's "
                "modality is skipped for that feature; two picks in the same tier stop the run with a message."
            )

    with st.container(border=True):
        step(
            2,
            "Evaluation spend",
            "Approve measured runs and cap what they may spend"
            if not sample
            else "Sample mode runs nothing measurable",
        )
        approved = st.checkbox(
            "I approve measured evaluation runs (live mode only; sample mode runs nothing)",
            value=False,
            key=key("approved"),
        )
        max_spend = st.text_input("Maximum evaluation spend (USD)", "0.50", key=key("spend"))

    return template, idea, user, features, stages, threshold, ceiling, approved, max_spend, picks, price, fraction
```

## `to_feature_rows` — `streamlit_app.py`

Reusable UI/helper function.

```python
def to_feature_rows(frame: pd.DataFrame) -> list[dict]:
    return [
        {k: ("" if pd.isna(v) else v) for k, v in row.items()}
        for row in frame.to_dict("records")
        if str(row.get("feature_id") or "").strip()
    ]
```

## `cost_rows` — `streamlit_app.py`

Reusable UI/helper function.

```python
def cost_rows(pack: dict) -> tuple[list[dict], str]:
    """The headline cost view: measured (or estimated) tokens at the dated market price. Sample packs carry no market
    projection, so they fall back to their placeholder stage tables, labeled as such."""
    tables, label = pack.get("openrouter_projection_tables") or [], "market reference price (OpenRouter catalog, dated)"
    if not tables:
        tables, label = pack.get("stage_tables") or [], "sample placeholder prices (not real)"
    return [
        {
            "feature": t["feature_id"],
            "stage": r["stage"],
            "users": r["active_users"],
            "model": r["model_id"].removeprefix("openrouter/"),
            "tokens": r["token_basis"],
            "monthly USD": num(r["gross_monthly_usd"]),
            "lower bound": r["lower_bound"],
        }
        for t in tables
        for r in t["rows"]
    ], label
```

## `pipeline_view` — `streamlit_app.py`

Reusable UI/helper function.

```python
def pipeline_view(events: list[dict], summary: dict):
    """Founder-facing Planner → Analyst → Critic strip; raw steps stay under an expander."""
    phases = svc.pipeline_phases(events)
    cells = []
    for phase in phases:
        detail = phase.get("detail") or ("in progress" if phase["state"] == "active" else "")
        cells.append(
            f'<div class="ca-phase" data-state="{phase["state"]}"><strong>{phase["name"]}</strong>'
            f'<span>{phase["copy"]}</span>'
            + (f"<em>{detail}</em>" if detail else "")
            + "</div>"
        )
    st.markdown('<div class="ca-pipeline">' + "".join(cells) + "</div>", unsafe_allow_html=True)
    st.caption(
        f"{summary['latest']} · {summary['steps']} trace steps · {summary['model_requests']} model requests"
        + (f" · {summary['errors']} errors" if summary["errors"] else "")
    )
```

## `totals_view` — `streamlit_app.py`

Reusable UI/helper function.

```python
def totals_view(pack: dict):
    """R9: one monthly AI number per stage for all features together, with revenue, AI contribution and budget fit."""
    totals = pack.get("stage_totals") or []
    if not totals:
        return
    scope = (
        "openrouter_listed_token_scenario"
        if any(t["pricing_scope"] != "actual_route" for t in totals)
        else "actual_route"
    )
    scoped = [t for t in totals if t["pricing_scope"] == scope]
    st.markdown("**Monthly AI cost, all features together**")
    label = lambda o: SCENARIO_LABEL.get(o[0]) or f"Same model for every feature: {o[1].removeprefix('openrouter/')}"
    options = {label(key): key for key in dict.fromkeys((t["scenario"], t["model_id"]) for t in scoped)}
    choice = options[st.selectbox("How models are chosen", list(options), key="total_scenario")]
    rows = [t for t in scoped if (t["scenario"], t["model_id"]) == choice]
    frame = pd.DataFrame(
        [
            {
                "stage": t["stage"],
                "users": t["active_users"],
                "monthly AI cost USD": num(t["monthly_usd"]),
                "complete": t["complete"],
                "lower bound": t["lower_bound"],
                "revenue USD": num(t["revenue_usd"]),
                "AI contribution USD": num(t["ai_contribution_usd"]),
                "AI margin": None
                if t["ai_contribution_margin"] is None
                else f"{num(t['ai_contribution_margin']) * 100:.1f}%",
                "budget": t["budget_fit"].replace("_", " "),
            }
            for t in rows
        ]
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    over = next((t for t in rows if t["budget_fit"] == "over"), None)
    if over:
        st.warning(
            f"First stage over the monthly AI budget: {over['stage']} ({over['active_users']} users), "
            f"at least ${over['monthly_usd']}/month."
        )
    notes = list(dict.fromkeys(t["note"] for t in rows if t["note"]))
    price = (
        "dated market reference price (OpenRouter)"
        if scope != "actual_route"
        else "sample placeholder prices"
        if pack["execution_mode"] == "sample"
        else "your actual route's verified rate"
    )
    st.caption(
        f"Priced at the {price}. AI-only: other operating costs are not included, and build costs are separate. "
        "Lower bound: some cost is unknown or not priced, so the true total is at least this, and the "
        "contribution at most this. " + " ".join(n[0].upper() + n[1:] + "." for n in notes)
    )
    compare = pd.DataFrame(
        [
            {"stage": t["stage"], "choice": label((t["scenario"], t["model_id"])), "USD": num(t["monthly_usd"])}
            for t in scoped
            if t["scenario"] != "recommended"
        ]
    )
    if not compare.empty:
        stage_chart(compare, "choice", "USD")
    st.divider()
```

## `status_line` — `streamlit_app.py`

Reusable UI/helper function.

```python
def status_line(pack: dict):
    st.markdown(
        f'<p class="ca-status">Status <b>{pack["status"]}</b> · Mode '
        f'<span class="ca-mono">{pack["execution_mode"]}</span> · Evaluation spend (USD) '
        f'<span class="ca-mono">{pack["spend_usd"]}</span> · Model requests '
        f'<span class="ca-mono">{pack["dispatch_count"]}</span></p>',
        unsafe_allow_html=True,
    )
```

## `results` — `streamlit_app.py`

Reusable UI/helper function.

```python
def results(pack: dict):
    step(3, "Results", f"DecisionPack for run {pack['run_id']}")
    status_line(pack)
    status = pack["status"]
    if status != "complete":
        st.info("This result is " + status + ". Missing or unknown evidence is listed below, not filled in.")
        if svc.outbox_hint(pack):
            st.warning(svc.outbox_hint(pack))
        why = svc.stop_reason(pack)
        if why:
            st.error("Why it stopped: " + why)
            if svc.setup_hint(why):
                st.warning(svc.setup_hint(why))
    for item in pack.get("questions", []):
        st.write("- " + item)

    tabs = st.tabs(
        [
            "Cost by stage",
            "Will it pass checks?",
            "What we still don't know",
            "Show your work",
        ]
    )
    runs = [r for r in pack["feature_runs"] if not r.get("is_repair")]
    rows, label = cost_rows(pack)

    with tabs[0]:
        totals_view(pack)
        st.markdown("**What each feature would cost per month as you grow**")
        if not rows:
            st.write("No cost rows in this pack.")
        else:
            frame = pd.DataFrame(rows)
            pick = st.selectbox("Feature", list(dict.fromkeys(frame["feature"])), key="cost_feature")
            subset = frame[frame["feature"] == pick]
            stage_chart(subset, "model", "monthly USD")
            st.dataframe(subset.drop(columns="feature"), width="stretch", hide_index=True)
            st.caption(
                f"Priced at the {label}. 'measured' rows use token counts from real model runs; 'estimated' rows "
                "are projected only (the model was not run). Lower bound: some lines, such as reasoning, are not "
                "priced. This is not your Nightshift bill and not a recommendation."
            )
        st.markdown("**Measured versus estimated tokens**")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "feature": r["feature_id"],
                        "model": r["model_id"],
                        "state": "measured" if r["executed"] else "projected only",
                        "estimated output tokens": r["estimated"]["output_tokens"],
                        "measured output tokens": (r.get("measured_mean") or {}).get("output_tokens"),
                        "measured / estimated": r.get("output_gap_ratio"),
                        "why not run": r.get("not_executed_reason") or "",
                    }
                    for r in runs
                ]
            ),
            width="stretch",
            hide_index=True,
        )

    with tabs[1]:
        st.markdown("**Deterministic checks decide quality. The Critic only flags.**")
        checks = [
            {"feature": r["feature_id"], "model": r["model_id"], "check": name, "result": "pass" if ok else "fail"}
            for r in runs
            if r.get("rubric")
            for name, ok in r["rubric"]["checks"].items()
        ]
        checks += [
            {
                "feature": r["feature_id"],
                "model": r["model_id"],
                "check": name,
                "result": "pending human review",
            }
            for r in runs
            if r.get("rubric")
            for name in r["rubric"].get("pending", [])
        ]
        if checks:
            st.dataframe(pd.DataFrame(checks), width="stretch", hide_index=True)
        else:
            st.write("No outputs were checked (no model was run).")
        st.markdown(
            '<div class="ca-locked" role="status">Recommendations locked until human review. '
            "No model stack is recommended until every critical check, including human review, passes.</div>",
            unsafe_allow_html=True,
        )
        findings = [f for c in pack.get("critiques", []) for f in c.get("findings", [])]
        st.markdown(f"**Critic flags ({len(findings)})**")
        if findings:
            st.dataframe(
                pd.DataFrame(
                    [{k: f.get(k) for k in ("kind", "severity", "feature_id", "model_id", "claim")} for f in findings]
                ),
                width="stretch",
                hide_index=True,
            )

    with tabs[2]:
        if pack["risks"]:
            st.dataframe(
                pd.DataFrame([{k: r.get(k) for k in ("severity", "description", "origin")} for r in pack["risks"]]),
                width="stretch",
                hide_index=True,
            )
        for item in pack["limitations"]:
            st.write("- " + item)
        with st.expander(f"Evidence gaps ({len(pack['evidence_gaps'])}): unknown or assumed values, never filled in"):
            st.dataframe(pd.DataFrame(pack["evidence_gaps"]), width="stretch", hide_index=True)
        with st.expander("Build panel (secondary; never added to running costs)"):
            panel = pack["build_panel"]
            for item in panel.get("reasons", []) + panel.get("questions", []):
                st.write("- " + item)
        st.caption(pack["disclaimer"])

    with tabs[3]:
        events = [json.loads(line) for line in svc.trace_text(pack).splitlines() if line.strip()]
        st.markdown("**Every Zetaris query, model request and memory operation, in order**")
        if events:
            st.dataframe(
                pd.DataFrame(
                    [
                        {k: e.get(k) for k in ("seq", "agent_name", "action", "status", "model", "output_summary")}
                        for e in events
                    ]
                ),
                width="stretch",
                hide_index=True,
            )
        suffix = "-SAMPLE-OFFLINE" if pack["execution_mode"] == "sample" else ""
        st.download_button(
            "Download decision pack (JSON)",
            json.dumps(pack, indent=2),
            file_name=f"{pack['run_id']}{suffix}.pack.json",
            mime="application/json",
        )
        if events:
            st.download_button(
                "Download trace (JSONL)",
                svc.trace_text(pack),
                file_name=f"{pack['run_id']}{suffix}.trace.jsonl",
            )
```
