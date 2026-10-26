"""Streamlit front end for the AI SaaS Cost Advisor.

  python -m streamlit run streamlit_app.py

The UI holds no business rules. It builds a RunRequest, hands it to `run.py` through app/ui_service.py, and renders the
serialized DecisionPack. A run ID owns one stored result: rerenders and double clicks load it and never start a second run.
"""
from __future__ import annotations

import json
import os

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app import ui_service as svc

st.set_page_config(page_title="AI SaaS Cost Advisor", layout="wide")
if not os.getenv("COST_ADVISOR_NO_DOTENV"):
    load_dotenv()   # the same settings run.py reads; values are never displayed

# Colors and type come from .streamlit/config.toml; this adds only the hero, step cards, pill tabs and metric cards.
STYLE = """
<style>
.block-container {padding-top: 2.5rem; max-width: 1280px;}
h1, h2, h3 {letter-spacing: -0.04em;}
.ca-hero {position: relative; overflow: hidden; padding: 3rem 2.5rem 2.6rem; margin-bottom: 1.5rem; border-radius: 30px;
  border: 1px solid #1f1f1f; background: radial-gradient(120% 140% at 85% -10%, rgba(140,255,46,.16) 0%,
  rgba(140,255,46,0) 45%), linear-gradient(180deg, #0d0d0d 0%, #050505 100%);}
.ca-eyebrow {display: inline-flex; align-items: center; gap: .5rem; padding: .35rem .85rem; border-radius: 999px;
  border: 1px solid rgba(140,255,46,.35); background: rgba(140,255,46,.08); color: #8cff2e; font-size: .72rem;
  font-weight: 700; letter-spacing: .2em; text-transform: uppercase;}
.ca-eyebrow::before {content: ""; width: 6px; height: 6px; border-radius: 50%; background: #8cff2e;
  box-shadow: 0 0 10px #8cff2e;}
.ca-hero h1 {font-size: clamp(2.1rem, 4.2vw, 3.6rem); line-height: 1.05; font-weight: 800; margin: 1.1rem 0 .9rem;
  padding: 0; max-width: 18ch; color: #f5f5f2;}
.ca-hero .ca-accent {color: #8cff2e;}
.ca-hero p {color: rgba(255,255,255,.65); font-size: 1.05rem; max-width: 60ch; margin: 0;}
.ca-pills {display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.6rem;}
.ca-pills span {padding: .4rem .9rem; border-radius: 999px; background: #171717; border: 1px solid #262626;
  color: #c8c8c0; font-size: .82rem; font-weight: 600;}
.ca-step {display: flex; align-items: center; gap: .85rem; margin: .2rem 0 .9rem;}
.ca-step b {display: inline-grid; place-items: center; min-width: 2.1rem; height: 2.1rem; border-radius: 12px;
  background: #8cff2e; color: #050505; font-weight: 800; font-size: .95rem;}
.ca-step div {font-size: 1.3rem; font-weight: 700; letter-spacing: -0.02em;}
.ca-step small {display: block; color: rgba(255,255,255,.55); font-size: .85rem; font-weight: 500; letter-spacing: 0;}
.ca-brand {font-size: 1.15rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: .2rem;}
.ca-brand span {color: #8cff2e;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 24px; background: #0d0d0d;}
div[data-testid="stMetric"] {background: #0d0d0d; border: 1px solid #1f1f1f; border-radius: 20px; padding: 1rem 1.2rem;}
div[data-testid="stMetricLabel"] p {text-transform: uppercase; letter-spacing: .14em; font-size: .7rem;
  color: rgba(255,255,255,.55); font-weight: 700;}
div[data-testid="stTabs"] [role="tablist"] {gap: .35rem; padding: .35rem; border-radius: 999px; background: #0d0d0d;
  border: 1px solid #1f1f1f; width: fit-content; max-width: 100%; overflow-x: auto; margin-bottom: 1rem;}
div[data-testid="stTab"] {border-radius: 999px; padding: .5rem 1.1rem; transition: background .15s;}
div[data-testid="stTab"]:hover {background: #171717;}
div[data-testid="stTab"][aria-selected="true"] {background: #8cff2e;}
div[data-testid="stTab"][aria-selected="true"] p {color: #050505; font-weight: 700;}
button[data-testid="stBaseButton-primary"] p {color: #050505; font-weight: 800;}
@media (max-width: 640px) {.ca-hero {padding: 2rem 1.25rem; border-radius: 24px;}}
</style>
"""


def style():
    st.markdown(STYLE, unsafe_allow_html=True)


def hero():
    st.markdown("""<div class="ca-hero"><span class="ca-eyebrow">AI SaaS Cost Advisor</span>
<h1>Know what your AI features cost <span class="ca-accent">at every stage.</span></h1>
<p>Turn an AI SaaS idea into a costed model stack by feature and growth stage, using measured tokens where a model
was run and dated market prices. Estimates, not advice.</p>
<div class="ca-pills"><span>Measured vs estimated tokens</span><span>Cost by growth stage</span>
<span>Deterministic quality checks</span><span>Full trace</span></div></div>""", unsafe_allow_html=True)


def step(number: int, title: str, hint: str = ""):
    st.markdown(f'<div class="ca-step"><b>{number:02d}</b><div>{title}'
                + (f"<small>{hint}</small>" if hint else "") + "</div></div>", unsafe_allow_html=True)


def stage_chart(frame: pd.DataFrame, series: str, value: str):
    """Monthly cost per stage, one line per series; stages stay in growth order (a plain line chart sorts them A-Z)."""
    order = list(dict.fromkeys(frame["stage"]))
    chart = alt.Chart(frame.dropna(subset=[value])).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("stage:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{value}:Q", title="USD per month"),
        color=alt.Color(f"{series}:N", title=None, legend=alt.Legend(orient="bottom", columns=2, labelLimit=460)),
        tooltip=["stage", series, alt.Tooltip(f"{value}:Q", format=",.2f")])
    st.altair_chart(chart, width="stretch")


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def banner(pack: dict | None, sample: bool):
    if (pack or {}).get("execution_mode") == "sample" or (pack is None and sample):
        st.warning("SAMPLE/OFFLINE: no network calls, no model executed. Tokens are estimated and nothing here is measured.")


def sidebar() -> tuple[str, bool]:
    with st.sidebar:
        st.markdown('<div class="ca-brand">Cost<span>.</span>Advisor</div>', unsafe_allow_html=True)
        mode = st.radio("Mode", ["Sample (offline)", "Live (Nightshift + Zetaris)"], key="mode")
        sample = mode.startswith("Sample")
        st.caption("Sample makes zero network calls." if sample else
                   "Live needs Zetaris, Nightshift and `.env`. Spend is capped by the approved limit below.")
        example = st.selectbox("Start from example", svc.list_examples(), key="example")
        st.caption("Examples are the starting point; every number is an editable assumption.")
        bindings = ""
        if not sample:
            with st.expander("Override price data file"):
                override = st.text_input("Zetaris bindings file", "", key="bindings",
                                         help="Leave empty to use ZETARIS_BINDINGS_FILE from .env.")
            found = svc.find_bindings(override)
            if found["ok"]:
                counts = found["counts"]
                st.success(f"Price data: snapshot `{found['snapshot_id'][:8]}`, {counts.get('models', '?')} models, "
                           f"{counts.get('catalog', '?')} catalog rows (from {found['source']})")
                bindings = found["path"]
            else:
                st.error("Price data not found: " + found["problem"] + (f" ({found['path']})" if found["path"] else ""))
    return example, sample, bindings


def form(example: str, sample: bool, bindings: str):
    template = svc.load_template(example)
    brief = template["brief"]
    key = lambda name: f"{example}:{name}"
    with st.container(border=True):
        step(1, "Idea and features", "What you are building and the AI features in it")
        idea = st.text_area("Product idea", brief["product_concept"], key=key("idea"), height=90)
        user = st.text_input("Target user", brief["target_user"], key=key("user"))
        rows = pd.DataFrame([{"feature_id": f["feature_id"], "description": f["description"], "example_input": f["example_input"],
                              "mode": f["mode"], "modality": ", ".join(f["modality"]),
                              "uses_per_user_month": str(f["uses_per_user_month"])} for f in brief["ai_features"]])
        st.caption("2 to 5 AI features. Modality: any of " + ", ".join(svc.MODALITIES) + " (comma-separated). "
                   "Usage values are assumptions. Audio and image features are priced, not executed.")
        features = st.data_editor(rows, num_rows="dynamic", width="stretch", key=key("features"),
                                  column_config={"mode": st.column_config.SelectboxColumn(options=["interactive", "background"])})
        st.markdown("**Growth stages** (assumed)")
        stages = st.data_editor(pd.DataFrame(brief["growth_stages"])[["name", "active_users"]], num_rows="dynamic",
                                width="stretch", key=key("stages"))
        left, right = st.columns(2)
        threshold = left.text_input("Switch threshold (USD/month)", str(brief.get("switch_threshold_usd", "100")), key=key("thr"))
        ceiling = right.text_input("Monthly AI budget ceiling (USD, optional)", brief.get("monthly_ai_budget_usd") or "", key=key("ceil"))
        usage = brief.get("usage") or {}
        left, right = st.columns(2)
        price = left.text_input("Price per paying user per month (USD, optional)", str(usage.get("subscription_price_usd") or ""),
                                key=key("price"), help="With the paying fraction, gives revenue per stage. Assumed.")
        fraction = right.text_input("Paying fraction of active users (0 to 1, optional)", str(usage.get("paying_fraction") or ""),
                                   key=key("fraction"), help="e.g. 0.08 for 8% of active users paying. Assumed.")
    with st.container(border=True):
        step(2, "Candidate models", "Optional: leave empty to let the app choose per feature")
        options = svc.candidate_options(sample, bindings)
        picks = st.multiselect("Choose up to 3, at most one per tier (frontier, mid-tier, open-source). Leave empty to let "
                               "the app choose per feature.", list(options), format_func=lambda mid: options.get(mid, mid),
                               max_selections=3, key=f"picks:{'sample' if sample else 'live'}")
        if picks:
            st.caption("Your picks replace the automatic choice for every feature. A pick that can't handle a feature's "
                       "modality is skipped for that feature; two picks in the same tier stop the run with a message.")
    with st.container(border=True):
        step(3, "Evaluation spend", "Approve measured runs and cap what they may spend")
        approved = st.checkbox("I approve measured evaluation runs (live mode only; sample mode runs nothing)",
                               value=False, key=key("approved"))
        max_spend = st.text_input("Maximum evaluation spend (USD)", "0.50", key=key("spend"))
    return template, idea, user, features, stages, threshold, ceiling, approved, max_spend, picks, price, fraction


def to_feature_rows(frame: pd.DataFrame) -> list[dict]:
    return [{k: ("" if pd.isna(v) else v) for k, v in row.items()} for row in frame.to_dict("records")
            if str(row.get("feature_id") or "").strip()]


def cost_rows(pack: dict) -> tuple[list[dict], str]:
    """The headline cost view: measured (or estimated) tokens at the dated market price. Sample packs carry no market
    projection, so they fall back to their placeholder stage tables, labeled as such."""
    tables, label = pack.get("openrouter_projection_tables") or [], "market reference price (OpenRouter catalog, dated)"
    if not tables:
        tables, label = pack.get("stage_tables") or [], "sample placeholder prices (not real)"
    return [{"feature": t["feature_id"], "stage": r["stage"], "users": r["active_users"], "model": r["model_id"].removeprefix("openrouter/"),
             "tokens": r["token_basis"], "monthly USD": num(r["gross_monthly_usd"]), "lower bound": r["lower_bound"]}
            for t in tables for r in t["rows"]], label


SCENARIO_LABEL = {"cheapest_per_feature": "Cheapest model per feature (cost only, quality not checked)",
                  "recommended": "Recommended stack (quality-qualified models only)"}


def totals_view(pack: dict):
    """R9: one monthly AI number per stage for all features together, with revenue, AI contribution and budget fit."""
    totals = pack.get("stage_totals") or []
    if not totals:
        return
    scope = "openrouter_listed_token_scenario" if any(t["pricing_scope"] != "actual_route" for t in totals) else "actual_route"
    scoped = [t for t in totals if t["pricing_scope"] == scope]
    st.markdown("**Monthly AI cost, all features together**")
    label = lambda o: SCENARIO_LABEL.get(o[0]) or f"Same model for every feature: {o[1].removeprefix('openrouter/')}"
    options = {label(key): key for key in dict.fromkeys((t["scenario"], t["model_id"]) for t in scoped)}
    choice = options[st.selectbox("How models are chosen", list(options), key="total_scenario")]
    rows = [t for t in scoped if (t["scenario"], t["model_id"]) == choice]
    frame = pd.DataFrame([{
        "stage": t["stage"], "users": t["active_users"], "monthly AI cost USD": num(t["monthly_usd"]),
        "complete": t["complete"], "lower bound": t["lower_bound"], "revenue USD": num(t["revenue_usd"]),
        "AI contribution USD": num(t["ai_contribution_usd"]),
        "AI margin": None if t["ai_contribution_margin"] is None else f"{num(t['ai_contribution_margin']) * 100:.1f}%",
        "budget": t["budget_fit"].replace("_", " ")} for t in rows])
    st.dataframe(frame, width="stretch", hide_index=True)
    over = next((t for t in rows if t["budget_fit"] == "over"), None)
    if over:
        st.warning(f"First stage over the monthly AI budget: {over['stage']} ({over['active_users']} users), "
                   f"at least ${over['monthly_usd']}/month.")
    notes = list(dict.fromkeys(t["note"] for t in rows if t["note"]))
    price = ("dated market reference price (OpenRouter)" if scope != "actual_route"
             else "sample placeholder prices" if pack["execution_mode"] == "sample" else "your actual route's verified rate")
    st.caption(f"Priced at the {price}. AI-only: other operating costs are not included, and build costs are separate. "
               "Lower bound: some cost is unknown or not priced, so the true total is at least this, and the "
               "contribution at most this. " + " ".join(n[0].upper() + n[1:] + "." for n in notes))
    compare = pd.DataFrame([{"stage": t["stage"], "choice": label((t["scenario"], t["model_id"])),
                             "USD": num(t["monthly_usd"])} for t in scoped if t["scenario"] != "recommended"])
    if not compare.empty:
        stage_chart(compare, "choice", "USD")
    st.divider()


def results(pack: dict):
    status = pack["status"]
    step(4, "Results", f"Run {pack['run_id']}")
    cols = st.columns(4)
    cols[0].metric("Status", status)
    cols[1].metric("Mode", pack["execution_mode"])
    cols[2].metric("Evaluation spend (USD)", pack["spend_usd"])
    cols[3].metric("Model requests", pack["dispatch_count"])
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

    tabs = st.tabs(["Cost by stage", "Measured vs estimated", "Quality checks", "Risks and gaps", "Trace and export"])
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
            st.caption(f"Priced at the {label}. 'measured' rows use token counts from real model runs; 'estimated' rows "
                       "are projected only (the model was not run). Lower bound: some lines, such as reasoning, are not "
                       "priced. This is not your Nightshift bill and not a recommendation.")
    with tabs[1]:
        st.markdown("**Why measuring matters: the 4/3 word rule against the API's own token counts**")
        st.dataframe(pd.DataFrame([{
            "feature": r["feature_id"], "model": r["model_id"],
            "state": "measured" if r["executed"] else "projected only",
            "estimated output tokens": r["estimated"]["output_tokens"],
            "measured output tokens": (r.get("measured_mean") or {}).get("output_tokens"),
            "measured / estimated": r.get("output_gap_ratio"),
            "why not run": r.get("not_executed_reason") or ""} for r in runs]), width="stretch", hide_index=True)
    with tabs[2]:
        st.markdown("**Deterministic checks decide quality. The Critic only flags.**")
        checks = [{"feature": r["feature_id"], "model": r["model_id"], "check": name, "result": "pass" if ok else "fail"}
                  for r in runs if r.get("rubric") for name, ok in r["rubric"]["checks"].items()]
        checks += [{"feature": r["feature_id"], "model": r["model_id"], "check": name, "result": "pending human review"}
                   for r in runs if r.get("rubric") for name in r["rubric"].get("pending", [])]
        if checks:
            st.dataframe(pd.DataFrame(checks), width="stretch", hide_index=True)
        else:
            st.write("No outputs were checked (no model was run).")
        st.caption("No model is recommended until every critical check, including human review, passes. "
                   "Human-review entry is not built in this version.")
        findings = [f for c in pack.get("critiques", []) for f in c.get("findings", [])]
        st.markdown(f"**Critic flags ({len(findings)})**")
        if findings:
            st.dataframe(pd.DataFrame([{k: f.get(k) for k in ("kind", "severity", "feature_id", "model_id", "claim")}
                                       for f in findings]), width="stretch", hide_index=True)
    with tabs[3]:
        if pack["risks"]:
            st.dataframe(pd.DataFrame([{k: r.get(k) for k in ("severity", "description", "origin")} for r in pack["risks"]]),
                         width="stretch", hide_index=True)
        for item in pack["limitations"]:
            st.write("- " + item)
        with st.expander(f"Evidence gaps ({len(pack['evidence_gaps'])}): unknown or assumed values, never filled in"):
            st.dataframe(pd.DataFrame(pack["evidence_gaps"]), width="stretch", hide_index=True)
        with st.expander("Build panel (secondary; never added to running costs)"):
            panel = pack["build_panel"]
            for item in panel.get("reasons", []) + panel.get("questions", []):
                st.write("- " + item)
        st.caption(pack["disclaimer"])
    with tabs[4]:
        events = [json.loads(line) for line in svc.trace_text(pack).splitlines() if line.strip()]
        st.markdown("**Every Zetaris query, model request and memory operation, in order**")
        if events:
            st.dataframe(pd.DataFrame([{k: e.get(k) for k in ("seq", "agent_name", "action", "status", "model", "output_summary")}
                                       for e in events]), width="stretch", hide_index=True)
        suffix = "-SAMPLE-OFFLINE" if pack["execution_mode"] == "sample" else ""
        st.download_button("Download decision pack (JSON)", json.dumps(pack, indent=2),
                           file_name=f"{pack['run_id']}{suffix}.pack.json", mime="application/json")
        if events:
            st.download_button("Download trace (JSONL)", svc.trace_text(pack), file_name=f"{pack['run_id']}{suffix}.trace.jsonl")


def main():
    style()
    example, sample, bindings = sidebar()
    hero()
    state = st.session_state
    state.setdefault("run_id", svc.new_run_id())
    stored = svc.load_result(state["run_id"])
    outcome = state.get("outcome") or ({"result": stored, "reused": True} if stored else None)
    banner(outcome["result"] if outcome and "execution_mode" in outcome["result"] else None, sample)

    template, idea, user, features, stages, threshold, ceiling, approved, max_spend, picks, price, fraction = form(example, sample, bindings)
    st.caption(f"Run ID: `{state['run_id']}`. A run ID runs once; use New run for another.")
    request = svc.build_request(template, run_id=state["run_id"], idea=idea, user=user, features=to_feature_rows(features),
                                stages=stages.to_dict("records"), switch_threshold=threshold, monthly_ceiling=ceiling,
                                approved=approved or sample, max_spend=max_spend, candidate_models=picks,
                                subscription_price=price, paying_fraction=fraction)
    parsed, problem = svc.validate(request)
    if problem:
        st.error("Fix the inputs: " + problem)
    left, right, _ = st.columns([1, 1, 8], gap="small")
    if not sample and not approved:
        st.warning("Approval is not ticked: a live run will read prices and pick candidates, then stop before any "
                   "model request (status needs_input). Tick the approval box above to measure.")
    blocked = parsed is None or state.get("busy", False) or (not sample and not bindings)
    run_clicked = left.button("Run", type="primary", disabled=blocked)
    if right.button("New run"):
        state["run_id"], state["outcome"] = svc.new_run_id(), None
        st.rerun()
    if run_clicked and parsed is not None:
        state["busy"] = True
        try:
            with st.status("Running...", expanded=True) as status:
                headline, table = st.empty(), st.empty()

                def show(events):
                    summary, rows = svc.progress_rows(events)
                    headline.markdown(f"**{summary['latest']}** · {summary['steps']} trace steps · "
                                      f"{summary['model_requests']} model requests"
                                      + (f" · {summary['errors']} errors" if summary["errors"] else ""))
                    table.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                    status.update(label=f"Running: {summary['latest']}")

                state["outcome"] = svc.submit_run(request, sample=sample, on_progress=show,
                                                  env_extra={"ZETARIS_BINDINGS_FILE": bindings})
                status.update(label="Run finished", state="complete", expanded=False)
        finally:
            state["busy"] = False
        st.rerun()

    st.divider()
    if outcome is None:
        st.info("Fill in the form and press Run. Sample mode needs no accounts.")
    elif "code" in outcome["result"]:
        st.error(f"{outcome['result']['code']}: {outcome['result']['message']}")
    else:
        if outcome.get("reused"):
            st.caption("Showing the stored result for this run ID; nothing was run again.")
            if outcome["result"].get("status") != "complete":
                st.warning("This run ID already ran. After fixing the setup or inputs, press New run, then Run.")
        results(outcome["result"])


main()
