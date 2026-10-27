"""Streamlit front end for the AI SaaS Cost Advisor.

  python -m streamlit run streamlit_app.py

The UI holds no business rules. It builds a RunRequest, hands it to `run.py` through app/ui_service.py, and renders the
serialized DecisionPack. A run ID owns one stored result: rerenders and double clicks load it and never start a second run.

Visual system and IA: docs/design.md (cool ledger light; Brief → Run → Results).
"""
from __future__ import annotations

import json
import os

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app import ui_service as svc

st.set_page_config(page_title="Cost.Advisor", layout="wide")
if not os.getenv("COST_ADVISOR_NO_DOTENV"):
    load_dotenv()   # the same settings run.py reads; values are never displayed

# Theme tokens live in .streamlit/config.toml; STYLE adds brand hero, timeline, tabs, and mono figures.
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=Sora:wght@600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: "Source Sans 3", sans-serif; }
h1, h2, h3, .ca-brand-hero, .ca-brand, .ca-step div { font-family: Sora, sans-serif; }
.ca-mono, code, pre { font-family: "IBM Plex Mono", monospace !important; font-weight: 500; }
.block-container {padding-top: 1.75rem; max-width: 1180px;}
h1, h2, h3 {letter-spacing: -0.03em; color: #12151A;}
.ca-hero {position: relative; overflow: hidden; padding: 2rem 0 1.5rem; margin-bottom: 1.25rem;
  background:
    radial-gradient(90% 120% at 100% 0%, rgba(15,107,92,.10) 0%, rgba(15,107,92,0) 55%),
    linear-gradient(180deg, rgba(248,250,252,.9) 0%, rgba(238,241,245,0) 100%);
  border-bottom: 1px solid #C9D1DB;}
.ca-brand-hero {font-size: clamp(2.2rem, 4.5vw, 3.4rem); line-height: 1.05; font-weight: 700; margin: 0 0 .75rem;
  color: #12151A; letter-spacing: -0.04em;}
.ca-brand-hero span {color: #0F6B5C;}
.ca-hero p {color: #5A6570; font-size: 1.05rem; max-width: 52ch; margin: 0; line-height: 1.45;}
.ca-sample {margin: 0 0 1rem; padding: .65rem 1rem; border: 1px solid #C9D1DB; border-left: 4px solid #8A5A00;
  background: #FBF6EA; color: #8A5A00; font-size: .92rem; font-weight: 600;
  animation: ca-settle .45s ease-out both;}
@keyframes ca-settle {from {opacity: 0; transform: translateY(-4px);} to {opacity: 1; transform: none;}}
@media (prefers-reduced-motion: reduce) {
  .ca-sample {animation: none;}
  .ca-phase, .ca-chart-wrap {animation: none !important;}
}
.ca-step {display: flex; align-items: flex-start; gap: .85rem; margin: .15rem 0 .85rem;}
.ca-step b {display: inline-grid; place-items: center; min-width: 2rem; height: 2rem; border-radius: 8px;
  background: #0F6B5C; color: #F8FAFC; font-weight: 700; font-size: .85rem; font-family: "IBM Plex Mono", monospace;}
.ca-step div {font-size: 1.2rem; font-weight: 700; letter-spacing: -0.02em; color: #12151A;}
.ca-step small {display: block; color: #5A6570; font-size: .85rem; font-weight: 500; letter-spacing: 0;
  font-family: "Source Sans 3", sans-serif; margin-top: .15rem;}
.ca-brand {font-size: 1.05rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: .35rem; color: #12151A;}
.ca-brand span {color: #0F6B5C;}
.ca-status {margin: 0 0 1rem; padding: .55rem 0; border-bottom: 1px solid #C9D1DB; color: #5A6570; font-size: .95rem;}
.ca-status b {color: #12151A;}
.ca-trust {font-size: .85rem; color: #5A6570; margin: .25rem 0 .75rem;}
.ca-pipeline {display: grid; grid-template-columns: repeat(3, 1fr); gap: .75rem; margin: .5rem 0 1rem;}
.ca-phase {border: 1px solid #C9D1DB; border-radius: 10px; padding: .85rem 1rem; background: #F8FAFC;
  transition: border-color .2s, background .2s;}
.ca-phase[data-state="pending"] {opacity: .55;}
.ca-phase[data-state="active"] {border-color: #0F6B5C; background: #D5EDE8;
  animation: ca-phase-in .35s ease-out both;}
.ca-phase[data-state="done"] {border-color: #0F6B5C; background: #F8FAFC;}
@keyframes ca-phase-in {from {opacity: .7;} to {opacity: 1;}}
.ca-phase strong {display: block; font-family: Sora, sans-serif; font-size: .95rem; color: #12151A; margin-bottom: .25rem;}
.ca-phase span {display: block; font-size: .82rem; color: #5A6570; line-height: 1.35;}
.ca-phase em {display: block; margin-top: .45rem; font-style: normal; font-size: .78rem; color: #0F6B5C;
  font-family: "IBM Plex Mono", monospace;}
.ca-locked {margin: .75rem 0; padding: .75rem 1rem; border: 1px dashed #C9D1DB; border-radius: 10px;
  background: #F8FAFC; color: #5A6570; font-size: .92rem;}
.ca-chart-wrap {animation: ca-draw .55s ease-out both;}
@keyframes ca-draw {from {opacity: 0; transform: translateX(-6px);} to {opacity: 1; transform: none;}}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 10px; background: #F8FAFC; border-color: #C9D1DB;}
div[data-testid="stTabs"] [role="tablist"] {gap: .15rem; padding: 0; border-radius: 0; background: transparent;
  border: none; border-bottom: 1px solid #C9D1DB; width: 100%; margin-bottom: 1rem;}
div[data-testid="stTab"] {border-radius: 8px 8px 0 0; padding: .55rem 1rem; background: transparent;}
div[data-testid="stTab"]:hover {background: #F8FAFC;}
div[data-testid="stTab"][aria-selected="true"] {background: #D5EDE8; border-bottom: 2px solid #0F6B5C;}
div[data-testid="stTab"][aria-selected="true"] p {color: #12151A; font-weight: 600;}
button[data-testid="stBaseButton-primary"] {border-radius: 10px !important;}
button[data-testid="stBaseButton-primary"] p {color: #F8FAFC; font-weight: 700;}
@media (max-width: 720px) {
  .ca-pipeline {grid-template-columns: 1fr;}
  .ca-hero {padding: 1.25rem 0 1rem;}
}
</style>
"""

CHART_COLORS = ["#0F6B5C", "#1F4E79", "#6B5B3E", "#5A6570"]


def style():
    st.markdown(STYLE, unsafe_allow_html=True)


def hero():
    st.markdown(
        """<div class="ca-hero"><div class="ca-brand-hero">Cost<span>.</span>Advisor</div>
<p>Know what your AI features cost at every growth stage — measured where a model ran, labeled estimated otherwise.</p>
</div>""",
        unsafe_allow_html=True,
    )


def step(number: int, title: str, hint: str = ""):
    st.markdown(
        f'<div class="ca-step"><b>{number:02d}</b><div>{title}'
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
            '<div class="ca-sample" role="status">SAMPLE/OFFLINE: no network calls, no model executed. '
            "Tokens are estimated and nothing here is measured.</div>",
            unsafe_allow_html=True,
        )


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


def main():
    style()
    example, sample, bindings = sidebar()
    hero()
    state = st.session_state
    state.setdefault("run_id", svc.new_run_id())
    stored = svc.load_result(state["run_id"])
    outcome = state.get("outcome") or ({"result": stored, "reused": True} if stored else None)
    banner(outcome["result"] if outcome and "execution_mode" in outcome["result"] else None, sample)

    template, idea, user, features, stages, threshold, ceiling, approved, max_spend, picks, price, fraction = form(
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
    with st.container(border=True):
        left, right, _ = st.columns([1, 1, 8], gap="small")
        run_clicked = left.button("Run", type="primary", disabled=blocked)
        if right.button("New run"):
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

    st.divider()
    if outcome is None:
        st.info("Fill in the brief and press Run. Sample mode needs no accounts.")
    elif "code" in outcome["result"]:
        st.error(f"{outcome['result']['code']}: {outcome['result']['message']}")
    else:
        if outcome.get("reused"):
            st.caption("Showing the stored result for this run ID; nothing was run again.")
            if outcome["result"].get("status") != "complete":
                st.warning("This run ID already ran. After fixing the setup or inputs, press New run, then Run.")
        results(outcome["result"])


main()
