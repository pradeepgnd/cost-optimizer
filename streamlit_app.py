"""Streamlit front end for the AI SaaS Cost Advisor.

  python -m streamlit run streamlit_app.py

The UI holds no business rules. It builds a RunRequest, hands it to `run.py` through app/ui_service.py, and renders the
serialized DecisionPack. A run ID owns one stored result: rerenders and double clicks load it and never start a second run.

Visual system: .superdesign/drafts/cost-advisor-hyper-saturated-fluid.html.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app import ui_service as svc

st.set_page_config(page_title="Cost.Advisor", layout="wide")
if not os.getenv("COST_ADVISOR_NO_DOTENV"):
    load_dotenv()   # the same settings run.py reads; values are never displayed

CHART_COLORS = ["#fde047", "#a78bfa", "#34d399", "#fb7185"]

# The reference design lives in .superdesign/drafts/cost-advisor-hyper-saturated-fluid.html.
THEME = Path(__file__).with_name("streamlit_theme.css").read_text()


def style():
    st.markdown("<style>" + THEME + "</style>", unsafe_allow_html=True)


def hero():
    st.markdown(
        """<div class="ca-hero"><h1>Know what your AI features cost as you grow.</h1>
<p>Measured where a model ran, labeled estimated otherwise. No invented savings, just transparent operating costs.</p>
</div>""",
        unsafe_allow_html=True,
    )


def step(number: int, title: str, hint: str = ""):
    st.markdown(
        f'<div class="ca-step"><b>{number}</b><div>{title}'
        + (f"<small>{hint}</small>" if hint else "")
        + "</div></div>",
        unsafe_allow_html=True,
    )


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
        .configure(background="#101010")
        .configure_axis(labelColor="#c4c4c4", titleColor="#c4c4c4", gridColor="#333333", domainColor="#555555")
        .configure_legend(labelColor="#e5e5e5")
        .configure_view(stroke=None)
    )
    st.markdown('<div class="ca-chart-wrap">', unsafe_allow_html=True)
    st.altair_chart(chart, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def banner(pack: dict | None, sample: bool):
    if (pack or {}).get("execution_mode") == "sample" or (pack is None and sample):
        st.markdown(
            '<div class="ca-sample" role="status"><span class="ca-info">i</span><div>'
            '<strong>SAMPLE/OFFLINE</strong><p>No network calls, no model executed. '
            "Tokens are estimated and nothing here is measured.</p></div></div>",
            unsafe_allow_html=True,
        )


def controls() -> tuple[str, bool]:
    """The reference's top rail is made of native Streamlit controls."""
    with st.container(key="ca_header"):
        with st.container(key="ca_header_content"):
            brand, rail = st.columns([1, 2], vertical_alignment="center")
            with brand:
                st.markdown('<div class="ca-brand">Cost<span>.</span>Advisor</div>', unsafe_allow_html=True)
            with rail:
                mode_col, example_col = st.columns([1.25, 1], vertical_alignment="center")
                with mode_col:
                    mode = st.radio(
                        "Mode", ["Sample (offline)", "Live (Nightshift + Zetaris)"],
                        key="mode", horizontal=True, label_visibility="collapsed",
                    )
                with example_col:
                    example = st.selectbox(
                        "Start from example", svc.list_examples(),
                        format_func=svc.example_label, key="example", label_visibility="collapsed",
                    )
            hero()
    return example, mode.startswith("Sample")


def price_data(sample: bool) -> str:
    if sample:
        return ""
    st.caption("Live needs Zetaris, Nightshift and `.env`. Evaluation spend is capped below.")
    with st.expander("Override price data file"):
        override = st.text_input(
            "Zetaris bindings file", "", key="bindings",
            help="Leave empty to use ZETARIS_BINDINGS_FILE from .env.",
        )
    found = svc.find_bindings(override)
    if found["ok"]:
        counts = found["counts"]
        st.success(
            f"Price data: snapshot `{found['snapshot_id'][:8]}`, {counts.get('models', '?')} models, "
            f"{counts.get('catalog', '?')} catalog rows (from {found['source']})"
        )
        return found["path"]
    st.error("Price data not found: " + found["problem"] + (f" ({found['path']})" if found["path"] else ""))
    return ""


def form(example: str, sample: bool, bindings: str):
    template = svc.load_template(example)
    brief = template["brief"]
    key = lambda name: f"{example}:{name}"

    with st.container(border=True, key="ca_brief"):
        step(1, "Brief", "Idea, features, and growth assumptions")
        idea_col, user_col = st.columns(2)
        idea = idea_col.text_area("Product idea", brief["product_concept"], key=key("idea"), height=120)
        user = user_col.text_input("Target user", brief["target_user"], key=key("user"))

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

    with st.container(border=True, key="ca_eval"):
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
        actions = st.empty()

    return template, idea, user, features, stages, threshold, ceiling, approved, max_spend, picks, price, fraction, actions


def to_feature_rows(frame: pd.DataFrame) -> list[dict]:
    return [
        {k: ("" if pd.isna(v) else v) for k, v in row.items()}
        for row in frame.to_dict("records")
        if str(row.get("feature_id") or "").strip()
    ]


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


SCENARIO_LABEL = {
    "cheapest_per_feature": "Cheapest model per feature (cost only, quality not checked)",
    "recommended": "Recommended stack (quality-qualified models only)",
}


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


def status_line(pack: dict):
    st.markdown(
        f'<p class="ca-status">Status <b>{pack["status"]}</b> · Mode '
        f'<span class="ca-mono">{pack["execution_mode"]}</span> · Evaluation spend (USD) '
        f'<span class="ca-mono">{pack["spend_usd"]}</span> · Model requests '
        f'<span class="ca-mono">{pack["dispatch_count"]}</span></p>',
        unsafe_allow_html=True,
    )


def recommendation_view(pack: dict):
    """One frontier model and one open-source model, after the run has costed them."""
    picks = svc.tier_recommendations(pack)
    if not picks:
        return
    st.markdown("**Recommendation**")
    st.caption("One frontier model and one open-source model from the models compared in this run. "
               "Each is the cheapest of its tier that still fits your monthly AI budget at the furthest growth stage. "
               "With no budget, each is the cheapest at your largest stage. "
               "If a model is not priced for every feature, the card names the features left out. "
               "This is a cost fit for the requirements you entered. "
               "A model is quality-qualified only when every critical check, including human review, passes.")
    titles = {"frontier": "Frontier", "open_source": "Open source"}
    fit_label = {"within": "within budget", "over": "over budget", "unknown": "budget fit unknown",
                 "no_budget": "no budget set"}
    cols = st.columns(2)
    for col, pick in zip(cols, picks):
        with col:
            with st.container(border=True):
                st.markdown(f"**{titles[pick['tier']]}**")
                if pick["model_id"]:
                    st.markdown(f"`{pick['model_id'].removeprefix('openrouter/')}`")
                    st.metric("Monthly AI cost (USD)", pick["monthly_usd"])
                    st.caption(f"{pick['stage']} · {pick['active_users']} users · {pick['token_basis']} tokens · "
                               f"{fit_label.get(pick['budget_fit'], pick['budget_fit'])}")
                st.markdown(pick["reason"])


def results(pack: dict):
    step(3, "DecisionPack Results", f"Run {pack['run_id']}")
    status_line(pack)
    events = [json.loads(line) for line in svc.trace_text(pack).splitlines() if line.strip()]
    if events:
        pipeline_view(events, svc.progress_rows(events)[0])
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

    recommendation_view(pack)
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


def run_page(example: str, sample: bool):
    bindings = price_data(sample)
    state = st.session_state
    state.setdefault("run_id", svc.new_run_id())
    stored = svc.load_result(state["run_id"])
    outcome = state.get("outcome") or ({"result": stored, "reused": True} if stored else None)
    banner(outcome["result"] if outcome and "execution_mode" in outcome["result"] else None, sample)

    template, idea, user, features, stages, threshold, ceiling, approved, max_spend, picks, price, fraction, actions = form(
        example, sample, bindings
    )
    st.markdown(
        f'<p class="ca-trust">Run ID <span class="ca-mono">{state["run_id"]}</span>. '
        "A run ID runs once; use New run for another.</p>",
        unsafe_allow_html=True,
    )
    request = svc.build_request(
        template,
        run_id=state["run_id"],
        idea=idea,
        user=user,
        features=to_feature_rows(features),
        stages=stages.to_dict("records"),
        switch_threshold=threshold,
        monthly_ceiling=ceiling,
        approved=approved or sample,
        max_spend=max_spend,
        candidate_models=picks,
        subscription_price=price,
        paying_fraction=fraction,
    )
    parsed, problem = svc.validate(request)
    if problem:
        st.error("Fix the inputs: " + problem)
    if not sample and not approved:
        st.warning(
            "Approval is not ticked: a live run will read prices and pick candidates, then stop before any "
            "model request (status needs_input). Tick the approval box above to measure."
        )
    blocked = parsed is None or state.get("busy", False) or (not sample and not bindings)
    with actions.container():
        left, right, _ = st.columns([1, 1, 4], gap="small")
        run_clicked = left.button("Run", type="primary", disabled=blocked)
        if right.button("New run", type="secondary"):
            state["run_id"], state["outcome"] = svc.new_run_id(), None
            st.rerun()
    if run_clicked and parsed is not None:
        state["busy"] = True
        try:
            with st.status("Running…", expanded=True) as status:
                timeline, details = st.empty(), st.empty()

                def show(events):
                    summary, rows = svc.progress_rows(events)
                    with timeline.container():
                        pipeline_view(events, summary)
                    with details.expander("Trace steps", expanded=False):
                        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                    status.update(label=f"Running: {summary['latest']}")

                state["outcome"] = svc.submit_run(
                    request,
                    sample=sample,
                    on_progress=show,
                    env_extra={"ZETARIS_BINDINGS_FILE": bindings},
                )
                status.update(label="Run finished", state="complete", expanded=False)
        finally:
            state["busy"] = False
        st.rerun()

    if outcome is None:
        st.markdown(
            '<div class="ca-empty"><span>03 / DECISIONPACK</span>'
            '<h2>Your results will appear here.</h2>'
            '<p>Fill in the brief and press Run. Sample mode needs no accounts.</p></div>',
            unsafe_allow_html=True,
        )
    elif "code" in outcome["result"]:
        st.error(f"{outcome['result']['code']}: {outcome['result']['message']}")
    else:
        if outcome.get("reused"):
            st.caption("Showing the stored result for this run ID; nothing was run again.")
            if outcome["result"].get("status") != "complete":
                st.warning("This run ID already ran. After fixing the setup or inputs, press New run, then Run.")
        results(outcome["result"])


def main():
    style()
    example, sample = controls()
    with st.container(key="ca_body"):
        run_page(example, sample)


main()
