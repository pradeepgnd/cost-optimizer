"""Streamlit front end for the AI SaaS Cost Advisor.

  python -m streamlit run streamlit_app.py

The UI holds no business rules. It builds a RunRequest, hands it to `run.py` through app/ui_service.py, and renders the
serialized DecisionPack. A run ID owns one stored result: rerenders and double clicks load it and never start a second run.

Visual system: .superdesign/design-system.md and
.superdesign/drafts/cost-advisor-hyper-saturated-fluid.html (Hyper-Saturated Fluid).
Information architecture stays Brief → Run → Results.
"""
from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app import ui_service as svc

st.set_page_config(page_title="Cost.Advisor", layout="wide")
if not os.getenv("COST_ADVISOR_NO_DOTENV"):
    load_dotenv()   # the same settings run.py reads; values are never displayed

# Hyper-Saturated Fluid tokens. Palette is Cyber Yellow, Deep Onyx, Charcoal,
# Deep Gray, and white. Inter is the face. Glass panels and pills replace the
# previous flat Bauhaus seams.
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root {
  --dp-color-ground: #0A0A0A;
  --dp-color-ink: #FFFFFF;
  --dp-color-accent: #FDE047;
  --dp-color-field: #171717;
  --dp-color-field-support: #262626;
  --dp-color-quiet: #171717;
  --dp-color-on-field: #0A0A0A;
  --dp-color-muted: #A3A3A3;
  --dp-typography-face: "Inter", sans-serif;
  --dp-typography-mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  --dp-typography-body: 16px;
  --dp-typography-reading: 16px;
  --dp-typography-label: 12px;
  --dp-typography-caption: 13px;
  --dp-typography-weight-display: 900;
  --dp-typography-weight-action: 700;
  --dp-typography-weight-label: 700;
  --dp-typography-weight-reading: 400;
  --dp-typography-reading-leading: 1.5;
  --dp-spacing-gutter: clamp(22px, 4.45cqi, 72px);
  --dp-radius-panel: 32px;
  --dp-radius-control: 16px;
  --dp-radius-pill: 999px;
  --dp-glass: rgba(255, 255, 255, 0.03);
  --dp-glass-line: rgba(255, 255, 255, 0.2);
  --dp-motion-enter: 0.55s cubic-bezier(0.22, 1, 0.36, 1);
  --dp-motion-press: 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
html, body, .stApp {
  font-family: var(--dp-typography-face);
  font-size: var(--dp-typography-body);
  font-weight: var(--dp-typography-weight-reading);
  color: var(--dp-color-ink);
  background: var(--dp-color-ground) !important;
  -webkit-font-smoothing: antialiased;
}
.stApp { background: var(--dp-color-ground) !important; overflow-x: hidden; }
header[data-testid="stHeader"] { background: #0A0A0A !important; }
h1, h2, h3, .ca-step div, .ca-phase strong {
  font-family: var(--dp-typography-face);
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--dp-color-ink);
}
.ca-mono, code, pre { font-family: var(--dp-typography-mono) !important; font-weight: 500; }
code { background: #262626 !important; color: var(--dp-color-accent) !important; border-radius: 8px; }
.block-container {
  padding-top: 0.75rem;
  padding-left: var(--dp-spacing-gutter);
  padding-right: var(--dp-spacing-gutter);
  max-width: 1280px;
}
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
@keyframes ca-rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}
.st-key-hero {
  --hero-pad: max(22px, calc(50vw - 640px));
  width: 100vw;
  box-sizing: border-box;
  margin-left: calc(50% - 50vw);
  margin-right: calc(50% - 50vw);
  margin-bottom: 1.5rem;
  padding: 1.35rem var(--hero-pad) 0;
  background: var(--dp-color-accent) !important;
  color: var(--dp-color-on-field);
  border-bottom-right-radius: clamp(80px, 11vw, 144px);
  border-bottom-left-radius: clamp(32px, 4vw, 56px);
  overflow: hidden;
  position: relative;
}
.st-key-hero-copy-row { width: 100%; margin-bottom: .25rem; }
.st-key-hero-art { flex: 0 0 112px; width: 112px; margin: 0 !important; }
.st-key-hero-art [data-testid="stImage"] img {
  display: block; width: 100%; height: auto; filter: drop-shadow(0 8px 12px rgba(10,10,10,.16));
}
.st-key-hero-bar {
  width: 100%;
  justify-content: space-between !important;
  align-items: center !important;
  margin-bottom: 2.75rem;
  gap: 1.25rem;
}
.ca-brand-hero {
  font-size: 1.5rem; line-height: 1; font-weight: 900;
  letter-spacing: -0.04em; margin: 0; color: #0A0A0A;
}
.ca-display {
  font-size: clamp(3rem, 8vw, 6rem); line-height: 0.9; font-weight: 900;
  letter-spacing: -0.05em; color: #0A0A0A; max-width: 18ch; margin: 0 0 1.5rem;
}
.ca-lede {
  color: #0A0A0A; font-size: clamp(1.15rem, 2.2vw, 1.5rem); font-weight: 500;
  line-height: 1.5; max-width: 36rem; margin: 0 0 0.75rem; opacity: 0.9;
}
.ca-wave {
  display: block; width: calc(100% + 2 * var(--hero-pad)); max-width: none;
  height: clamp(80px, 11vw, 144px); margin-left: calc(-1 * var(--hero-pad)); margin-bottom: -1px;
}
.st-key-rail {
  background: #0A0A0A !important;
  border-radius: var(--dp-radius-pill) !important;
  padding: 0.4rem 0.9rem 0.4rem 0.4rem !important;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35) !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.st-key-rail [data-testid="stRadio"] [role="radiogroup"] {
  display: flex; gap: 0.15rem; background: #171717; border-radius: var(--dp-radius-pill); padding: 0.2rem;
}
.st-key-rail [data-testid="stRadio"] [role="radiogroup"] > label {
  border-radius: var(--dp-radius-pill); padding: 0.45rem 1rem; margin: 0; cursor: pointer;
  color: #A3A3A3; font-size: 0.875rem; font-weight: 600; transition: color 0.15s ease, background 0.15s ease;
}
.st-key-rail [data-testid="stRadio"] [data-baseweb="radio"] { display: none !important; }
.st-key-rail [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
  background: #FDE047 !important; color: #0A0A0A !important; font-weight: 600;
}
.st-key-rail [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) * {
  color: #0A0A0A !important; font-weight: 600 !important;
}
.st-key-rail [data-testid="stSelectbox"] {
  min-width: 11rem;
}
.st-key-rail [data-baseweb="select"] > div {
  background: transparent !important; border: none !important; box-shadow: none !important;
  min-height: 2.25rem !important;
}
.st-key-rail [data-baseweb="select"] *,
.st-key-rail [data-baseweb="select"] svg {
  color: #D4D4D4 !important; fill: #A3A3A3 !important;
}
.st-key-rail [data-baseweb="select"]:focus-within > div {
  background: rgba(255, 255, 255, 0.06) !important; border-radius: var(--dp-radius-pill) !important;
}
.ca-sample {
  display: flex; align-items: flex-start; gap: 1rem;
  margin: 0 0 1.25rem; padding: 1.35rem 1.5rem;
  background: var(--dp-glass); color: #D4D4D4;
  border: 1px solid rgba(253, 224, 71, 0.3); border-radius: var(--dp-radius-panel);
  backdrop-filter: blur(24px); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  font-size: var(--dp-typography-caption); font-weight: 400;
  animation: ca-rise var(--dp-motion-enter) both;
}
.ca-sample-icon {
  flex: 0 0 auto; width: 2.5rem; height: 2.5rem; border-radius: 999px;
  display: inline-grid; place-items: center;
  background: #FDE047; color: #0A0A0A; font-size: 1.1rem; font-weight: 800;
}
.ca-sample-body { flex: 1; min-width: 0; }
.ca-sample b {
  display: block; margin-bottom: 0.25rem; color: var(--dp-color-accent);
  font-size: var(--dp-typography-label); font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
}
.ca-sample span { color: #D4D4D4; }
.ca-step { display: flex; align-items: flex-start; gap: 0.75rem; margin: 0 0 1rem; border: none; background: transparent; }
.ca-step b {
  display: inline-grid; place-items: center; width: 2rem; height: 2rem; min-width: 2rem; padding: 0;
  background: rgba(255, 255, 255, 0.1); color: #FFFFFF;
  border: none; border-radius: var(--dp-radius-pill);
  font-weight: 700; font-size: 0.85rem;
}
.ca-step div {
  flex: 1; padding: 0.15rem 0 0; background: transparent; color: #FFFFFF;
  font-size: 1.45rem; font-weight: 700; line-height: 1.15; letter-spacing: -0.03em;
}
.ca-step small {
  display: block; margin-top: 0.25rem; color: var(--dp-color-muted);
  font-size: var(--dp-typography-caption); font-weight: 400; letter-spacing: 0; line-height: 1.4;
}
.ca-status {
  display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0 0 1rem; padding: 0.5rem;
  background: #171717; color: #D4D4D4;
  border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 1rem;
  font-family: var(--dp-typography-mono); font-size: 0.72rem; font-weight: 500;
  letter-spacing: 0.08em; text-transform: uppercase;
}
.ca-status .ca-pill {
  padding: 0.3rem 0.75rem; border-radius: var(--dp-radius-pill); background: rgba(255, 255, 255, 0.05);
  color: #D4D4D4;
}
.ca-status .ca-pill-ok {
  background: rgba(34, 197, 94, 0.2); color: #4ade80;
}
.ca-status b { font-weight: 700; color: inherit; }
.ca-pipeline {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem;
  margin: 0.5rem 0 1.25rem; padding: 0.5rem;
  background: var(--dp-glass); border: 1px solid var(--dp-glass-line); border-radius: var(--dp-radius-panel);
  backdrop-filter: blur(24px); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
.ca-phase {
  display: flex; align-items: flex-start; gap: 0.85rem;
  padding: 1rem; background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 1rem; color: #FFFFFF;
}
.ca-phase-mark {
  flex: 0 0 auto; width: 1.75rem; height: 1.75rem; margin-top: 0.1rem;
  border-radius: 999px; display: inline-grid; place-items: center;
  background: rgba(255, 255, 255, 0.1); color: #A3A3A3; font-size: 0.75rem; font-weight: 800;
}
.ca-phase[data-state="pending"] { opacity: 0.45; }
.ca-phase[data-state="active"],
.ca-phase[data-state="done"] {
  background: rgba(253, 224, 71, 0.1); border-color: rgba(253, 224, 71, 0.22);
}
.ca-phase[data-state="active"] .ca-phase-mark,
.ca-phase[data-state="done"] .ca-phase-mark {
  background: #FDE047; color: #0A0A0A;
}
.ca-phase[data-state="active"] strong,
.ca-phase[data-state="done"] strong { color: var(--dp-color-accent); }
.ca-phase strong {
  display: block; font-size: 0.9rem; font-weight: 700; margin-bottom: 0.25rem; color: #FFFFFF;
}
.ca-phase span, .ca-phase em {
  display: block; font-size: var(--dp-typography-caption); font-weight: 400;
  line-height: 1.35; color: var(--dp-color-muted);
}
.ca-phase em { margin-top: 0.4rem; font-style: normal; font-weight: 600; color: #E5E5E5; }
.st-key-eval-run {
  align-items: stretch !important;
}
.st-key-eval-actions {
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  padding-left: 1.5rem;
  margin-left: 0.5rem;
}
.ca-locked {
  margin: 0.75rem 0; padding: 0.85rem 1rem;
  border: 1px solid rgba(253, 224, 71, 0.3); border-radius: 0.75rem;
  background: rgba(253, 224, 71, 0.1); color: var(--dp-color-accent);
  font-size: var(--dp-typography-reading); font-weight: 500;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--dp-radius-panel) !important;
  background: var(--dp-glass) !important;
  border: 1px solid var(--dp-glass-line) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(24px);
  animation: ca-rise var(--dp-motion-enter) both;
}
div[data-testid="stTabs"] {
  background: var(--dp-glass); border: 1px solid var(--dp-glass-line); border-radius: var(--dp-radius-panel);
  backdrop-filter: blur(24px); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); overflow: hidden;
  padding: 0.35rem 0.35rem 0.85rem;
}
.ca-results-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 1.25rem; margin: 0 0 2rem; }
.ca-results-title { display: flex; align-items: center; gap: .85rem; margin: 0 0 .45rem; color: #FFFFFF; font-size: clamp(1.55rem, 2.7vw, 2rem); font-weight: 800; letter-spacing: -.045em; white-space: nowrap; }
.ca-results-number { display: inline-grid; place-items: center; width: 2.5rem; height: 2.5rem; flex: 0 0 2.5rem; color: #FFFFFF; background: rgba(255,255,255,.1); border-radius: 50%; font-size: 1rem; letter-spacing: 0; }
.ca-results-run { margin: 0; color: #A3A3A3 !important; font-size: .9rem; }
.ca-results-run code { padding: 0; color: #D4D4D4; background: transparent; font: 500 .88rem ui-monospace,monospace; }
.ca-status {
  display: inline-flex; flex-wrap: wrap; justify-content: flex-end; gap: .45rem; margin: 0; padding: .5rem;
  width: max-content; max-width: 100%; margin-left: auto; color: #D4D4D4;
  background: #171717; border: 1px solid rgba(255,255,255,.08); border-radius: 18px;
  font: 650 .68rem/1.4 Inter,sans-serif; letter-spacing: .08em; text-transform: uppercase;
}
.ca-status-chip { display: inline-flex; align-items: center; padding: .32rem .7rem; color: #D4D4D4; background: rgba(255,255,255,.055); border-radius: 999px; white-space: nowrap; }
.ca-status-chip[data-status="complete"] { color: #4ADE80; background: rgba(34,197,94,.16); }
.ca-status-chip[data-status="partial"], .ca-status-chip[data-status="needs_input"] { color: #FDE047; background: rgba(253,224,71,.12); }
.ca-status-chip[data-status="failed"], .ca-status-chip[data-status="error"] { color: #F87171; background: rgba(239,68,68,.15); }
.ca-table-wrap { margin: .85rem 0 1.4rem; overflow-x: auto; border: 1px solid rgba(255,255,255,.1); border-radius: 22px; }
.ca-html-table { width: 100%; border-collapse: collapse; color: #D4D4D4; font-size: .9rem; white-space: nowrap; }
.ca-html-table thead { color: #D4D4D4; background: rgba(255,255,255,.055); font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; }
.ca-html-table th { padding: 1rem 1.15rem; text-align: left; font-weight: 700; }
.ca-html-table th.numeric, .ca-html-table td.numeric { text-align: right; }
.ca-html-table th.center, .ca-html-table td.center { text-align: center; }
.ca-html-table td { padding: 1rem 1.15rem; border-top: 1px solid rgba(255,255,255,.055); }
.ca-html-table tbody tr:hover { background: rgba(255,255,255,.035); }
.ca-html-table .primary-value { color: #FDE047; font: 650 .9rem ui-monospace,monospace; }
.ca-html-table .mono-value { color: #D4D4D4; font: 500 .86rem ui-monospace,monospace; }
.ca-html-table .sub-value { display: block; max-width: 30rem; margin-top: .22rem; color: #A3A3A3; font: 400 .7rem/1.4 Inter,sans-serif; white-space: normal; }
.ca-section-title { margin: 0 0 .35rem; color: #FFFFFF; font-size: 1.2rem; font-weight: 800; letter-spacing: -.025em; }
.ca-check-title { margin: 0 0 .9rem; color: #FFFFFF; font-size: 1.2rem; font-weight: 800; letter-spacing: -.025em; }
.ca-pill { display: inline-flex; padding: .28rem .58rem; border-radius: 6px; font-size: .7rem; font-weight: 750; }
.ca-pill[data-tone="green"] { color: #4ADE80; background: rgba(34,197,94,.16); }
.ca-pill[data-tone="red"] { color: #F87171; background: rgba(239,68,68,.16); }
.ca-pill[data-tone="neutral"] { color: #D4D4D4; background: #262626; }
.ca-pill[data-tone="yellow"] { color: #FDE047; background: rgba(253,224,71,.12); }
.ca-pill[data-tone="blue"] { color: #60A5FA; background: rgba(59,130,246,.18); }
.ca-cheapest-tag {
  display: inline-flex; align-items: center; width: fit-content; margin: 0 0 .7rem;
  padding: .32rem .7rem; color: #4ADE80; background: rgba(34,197,94,.16);
  border: 1px solid rgba(74,222,128,.26); border-radius: 999px;
  font-size: .66rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase;
}
.st-key-ca-rec-card-cheapest [data-testid="stVerticalBlockBorderWrapper"] {
  border-color: rgba(74,222,128,.55) !important;
  box-shadow: 0 0 0 1px rgba(74,222,128,.15), 0 8px 32px rgba(0,0,0,.2) !important;
}
.ca-html-table .token-estimate { color: #FDE047; font: 650 .9rem ui-monospace,monospace; }
.ca-html-table .token-actual { color: #4ADE80; font: 650 .9rem ui-monospace,monospace; }
.ca-html-table .token-missing { color: #737373; font: 500 .86rem ui-monospace,monospace; }
.st-key-ca-selector-card { height: 100%; padding: 1rem; background: rgba(255,255,255,.025); border: 1px solid rgba(255,255,255,.08); border-radius: 20px; }
.st-key-ca-selector-card label { color: #737373 !important; font-size: .65rem !important; font-weight: 750 !important; letter-spacing: .13em !important; text-transform: uppercase; }
@media (max-width: 900px) {
  .ca-results-head { align-items: flex-start; flex-direction: column; }
  .ca-status { justify-content: flex-start; width: auto; margin-left: 0; }
  .ca-html-table th, .ca-html-table td { padding: .75rem .8rem; }
}
div[data-testid="stTabs"] [role="tablist"] {
  gap: 0.4rem; padding: 0.4rem; border-radius: 0;
  background: transparent; border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  width: 100%; margin-bottom: 0.5rem;
}
div[data-testid="stTab"] {
  border-radius: 0.75rem; padding: 0.7rem 1.35rem; background: transparent; border: none;
  transition: background 0.2s ease, color 0.2s ease;
}
div[data-testid="stTab"] p { color: #A3A3A3 !important; font-weight: 500; font-size: 0.875rem; }
div[data-testid="stTab"]:hover { background: rgba(255, 255, 255, 0.05); }
div[data-testid="stTab"]:hover p { color: #FFFFFF !important; }
/* tab-active: yellow fill, onyx type — matches Hyper-Saturated HTML */
div[data-testid="stTab"][aria-selected="true"],
div[data-testid="stTab"].tab-active {
  background: #FDE047 !important; border: none !important;
}
div[data-testid="stTab"][aria-selected="true"] p,
div[data-testid="stTab"].tab-active p {
  color: #0A0A0A !important; font-weight: 600 !important;
}
[data-testid="stTextInput"] [data-testid="stWidgetLabel"] p,
[data-testid="stTextArea"] [data-testid="stWidgetLabel"] p,
[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p,
[data-testid="stMultiSelect"] [data-testid="stWidgetLabel"] p {
  color: #A3A3A3 !important; font-size: 0.72rem !important; font-weight: 700 !important;
  letter-spacing: 0.12em !important; text-transform: uppercase !important;
}
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: var(--dp-radius-control) !important;
  box-shadow: none !important;
}
.st-key-rail [data-baseweb="select"] > div {
  background: transparent !important; border-color: transparent !important;
}
[data-baseweb="input"]:focus-within > div,
[data-baseweb="textarea"]:focus-within > div,
[data-baseweb="select"]:focus-within > div {
  border-color: #FDE047 !important; background: rgba(255, 255, 255, 0.08) !important;
}
input, textarea { color: #FFFFFF !important; caret-color: #FDE047; }
/* Dropdown menus: dark glass + yellow selected row (not default Streamlit chrome) */
[data-baseweb="popover"] [data-baseweb="menu"],
ul[role="listbox"] {
  background: #171717 !important;
  border: 1px solid rgba(255, 255, 255, 0.16) !important;
  border-radius: 1rem !important;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55) !important;
  padding: 0.35rem !important;
}
[data-baseweb="menu"] li,
ul[role="listbox"] li,
[role="option"] {
  border-radius: 0.65rem !important;
  color: #E5E5E5 !important;
}
[data-baseweb="menu"] li[aria-selected="true"],
ul[role="listbox"] li[aria-selected="true"],
[role="option"][aria-selected="true"],
[data-baseweb="menu"] li:hover,
ul[role="listbox"] li:hover,
[role="option"]:hover {
  background: #FDE047 !important;
  color: #0A0A0A !important;
}
[data-baseweb="menu"] li[aria-selected="true"] *,
ul[role="listbox"] li[aria-selected="true"] *,
[role="option"][aria-selected="true"] * {
  color: #0A0A0A !important;
}
div[data-testid="stAlert"] {
  background: #171717 !important; color: #FFFFFF !important;
  border: 1px solid rgba(253, 224, 71, 0.45) !important; border-radius: var(--dp-radius-control) !important;
}
div[data-testid="stAlert"] p, div[data-testid="stAlert"] div { color: #FFFFFF !important; }
div[data-testid="stMetricValue"] { color: var(--dp-color-accent) !important; }
div[data-testid="stExpander"] details, [data-testid="stExpander"] {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: var(--dp-radius-control) !important;
}
[data-testid="stDataFrame"] { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 1rem; overflow: hidden; }
hr, [data-testid="stDivider"] { border-color: rgba(255, 255, 255, 0.1) !important; }
button[data-testid="stBaseButton-primary"] {
  border-radius: var(--dp-radius-pill) !important;
  min-width: 0 !important; min-height: 0 !important;
  padding: 0.75rem 1.75rem !important;
  background: var(--dp-color-accent) !important;
  border: none !important;
  box-shadow: 0 0 20px rgba(253, 224, 71, 0.3) !important;
  transition: transform var(--dp-motion-press), box-shadow 0.2s ease !important;
}
button[data-testid="stBaseButton-primary"]:hover {
  box-shadow: 0 0 30px rgba(253, 224, 71, 0.5) !important; transform: none;
}
button[data-testid="stBaseButton-primary"]:active { transform: scale(0.95); }
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] span {
  color: #0A0A0A !important; font-weight: 700 !important;
}
button[data-testid="stBaseButton-secondary"],
button[kind="secondary"] {
  border-radius: var(--dp-radius-pill) !important;
  background: rgba(255, 255, 255, 0.1) !important;
  color: #FFFFFF !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  box-shadow: none !important;
  transition: transform var(--dp-motion-press), background 0.2s ease !important;
}
button[data-testid="stBaseButton-secondary"]:hover { background: rgba(255, 255, 255, 0.18) !important; }
button[data-testid="stBaseButton-secondary"]:active { transform: scale(0.95); }
button[data-testid="stBaseButton-secondary"] p { color: #FFFFFF !important; font-weight: 600 !important; }
*:focus-visible {
  outline: 2px solid var(--dp-color-accent) !important;
  outline-offset: 2px !important;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important; transition: none !important; scroll-behavior: auto !important;
  }
  button[data-testid="stBaseButton-primary"]:active,
  button[data-testid="stBaseButton-secondary"]:active { transform: none; }
}
@media (max-width: 720px) {
  .ca-pipeline { grid-template-columns: 1fr; }
  .st-key-hero-bar { align-items: flex-start !important; }
  .st-key-hero-art { display: none !important; }
  .ca-display { font-size: clamp(2.4rem, 12vw, 3.4rem); }
  .st-key-eval-actions {
    border-left: none; border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-left: 0; padding-top: 1.25rem; margin-left: 0; margin-top: 0.5rem;
  }
}
</style>
"""

CHART_COLORS = ["#FDE047", "#FFFFFF", "#A3A3A3", "#525252"]
CALCULATOR_ART = Path(__file__).resolve().parent / "assets" / "cost-advisor-calculator.svg"


def style():
    st.markdown(STYLE, unsafe_allow_html=True)


WAVE = """<svg class="ca-wave" viewBox="0 0 1440 120" preserveAspectRatio="none" aria-hidden="true">
<path fill="#0A0A0A" d="M0,120 C320,0 720,150 1440,40 L1440,120 L0,120 Z"></path>
</svg>"""

def step(number: int, title: str, hint: str = ""):
    st.markdown(
        f'<div class="ca-step"><b>{number}</b><div>{title}'
        + (f"<small>{hint}</small>" if hint else "")
        + "</div></div>",
        unsafe_allow_html=True,
    )


def stage_chart(frame: pd.DataFrame, series: str, value: str):
    """Show a polished cost trajectory and mark the lowest priced option per stage."""
    data = frame.copy()
    data[value] = pd.to_numeric(data[value], errors="coerce")
    data = data.dropna(subset=[value])
    if data.empty:
        st.info("No priced options to chart for these stages.")
        return

    order = list(dict.fromkeys(data["stage"]))
    data["_selection"] = data[value].eq(data.groupby("stage")[value].transform("min"))
    data["_selection_label"] = data["_selection"].map(
        {True: "Lowest shown", False: "Other priced option"}
    )
    base = alt.Chart(data)
    x = alt.X(
        "stage:N",
        sort=order,
        title=None,
        axis=alt.Axis(labelAngle=0, labelPadding=12, tickSize=0, domain=False),
    )
    y = alt.Y(
        f"{value}:Q",
        title=None,
        scale=alt.Scale(zero=True),
        axis=alt.Axis(format="$,.0f", grid=True, gridDash=[2, 4], tickCount=5, domain=False, labelPadding=8),
    )
    color = alt.Color(
        f"{series}:N",
        title=None,
        scale=alt.Scale(range=CHART_COLORS),
        legend=alt.Legend(
            orient="top",
            direction="horizontal",
            columns=3,
            labelLimit=220,
            symbolType="stroke",
            symbolStrokeWidth=3,
            symbolSize=120,
            padding=10,
        ),
    )
    tooltip = [
        alt.Tooltip("stage:N", title="Growth stage"),
        alt.Tooltip(f"{series}:N", title="Model"),
        alt.Tooltip(f"{value}:Q", title="Monthly cost", format="$,.2f"),
        alt.Tooltip("_selection_label:N", title="Selection"),
    ]
    area = base.mark_area(opacity=0.065, interpolate="monotone", clip=True).encode(
        x=x, y=y, color=color
    )
    line = base.mark_line(
        interpolate="monotone", strokeWidth=3, strokeCap="round", clip=True
    ).encode(x=x, y=y, color=color)
    points = base.mark_point(
        filled=True, size=78, stroke="#0A0A0A", strokeWidth=2, clip=True
    ).encode(x=x, y=y, color=color, tooltip=tooltip)
    lowest_points = (
        base.transform_filter(alt.datum._selection)
        .mark_point(filled=True, size=150, color="#4ADE80", stroke="#0A0A0A", strokeWidth=2, clip=True)
        .encode(x=x, y=y, tooltip=tooltip)
    )
    chart = (
        alt.layer(area, line, points, lowest_points)
        .resolve_scale(color="shared")
        .properties(height=300, padding={"left": 12, "right": 14, "top": 4, "bottom": 8})
        .configure(background="transparent")
        .configure_view(stroke="transparent")
        .configure_axis(
            labelColor="#A3A3A3",
            labelFont="Inter",
            labelFontSize=11,
            titleColor="#D4D4D4",
            titleFont="Inter",
            titleFontSize=11,
            gridColor="rgba(255,255,255,0.09)",
            gridOpacity=0.8,
            tickColor="transparent",
        )
        .configure_legend(
            labelColor="#D4D4D4",
            labelFont="Inter",
            labelFontSize=11,
            titleColor="#FFFFFF",
        )
    )
    with st.container(border=True):
        st.caption("Monthly AI cost · USD")
        st.altair_chart(chart, width="stretch")

def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def banner(pack: dict | None, sample: bool):
    if (pack or {}).get("execution_mode") == "sample" or (pack is None and sample):
        st.markdown(
            '<div class="ca-sample" role="status">'
            '<div class="ca-sample-icon" aria-hidden="true">i</div>'
            '<div class="ca-sample-body"><b>SAMPLE/OFFLINE</b>'
            "<span>No network calls, no model executed. Tokens are estimated and nothing here is measured.</span>"
            "</div></div>",
            unsafe_allow_html=True,
        )


def start_new_run():
    """A different mode or idea is a different run: give it a fresh run ID and drop the previous result."""
    st.session_state["run_id"], st.session_state["outcome"] = svc.new_run_id(), None


def controls() -> tuple[str, bool]:
    """Yellow liquid hero: Cost.Advisor wordmark, controls, headline, and calculator art."""
    with st.container(key="hero"):
        with st.container(key="hero-bar", horizontal=True, vertical_alignment="center"):
            st.markdown('<div class="ca-brand-hero">Cost<span>.</span>Advisor</div>', unsafe_allow_html=True)
            with st.container(key="rail"):
                with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                    mode = st.radio(
                        "Mode",
                        ["Sample (offline)", "Live"],
                        key="mode",
                        horizontal=True,
                        on_change=start_new_run,
                        label_visibility="collapsed",
                    )
                    example = st.selectbox(
                        "Start from example",
                        svc.list_examples(),
                        format_func=svc.example_label,
                        key="example",
                        on_change=start_new_run,
                        label_visibility="collapsed",
                    )
        with st.container(key="hero-copy-row"):
            copy_col, art_col = st.columns([4.5, 1], vertical_alignment="center", gap="small")
            with copy_col:
                st.markdown(
                    '<div class="ca-display">Know what your AI features cost as you grow.</div>'
                    '<p class="ca-lede">Measured where a model ran, labeled estimated otherwise. '
                    "No invented savings, just transparent operating costs.</p>",
                    unsafe_allow_html=True,
                )
            with art_col:
                with st.container(key="hero-art"):
                    st.image(CALCULATOR_ART, width=112, alt="Cost Advisor calculator")
        st.markdown(WAVE, unsafe_allow_html=True)
    return example, mode.startswith("Sample")

def price_data(sample: bool) -> str:
    if sample:
        return ""
    st.caption("Live needs Zetaris, Nightshift and `.env`. Spend is capped by the approved limit below.")
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
        return found["path"]
    st.error("Price data not found: " + found["problem"] + (f" ({found['path']})" if found["path"] else ""))
    return ""

def form(example: str, sample: bool, bindings: str):
    template = svc.load_template(example)
    brief = template["brief"]
    key = lambda name: f"{example}:{name}"

    with st.container(border=True):
        step(1, "Brief", "Idea, features, and growth assumptions")
        st.caption("Every number is an editable assumption.")
        idea = st.text_area("Product idea", brief["product_concept"], key=key("idea"), height=90)
        user = st.text_input("Target user", brief["target_user"], key=key("user"))

        st.caption(
            "2 to 5 AI features. Modality: any of "
            + ", ".join(svc.MODALITIES)
            + " (comma-separated). Usage values are assumptions. Audio and image features are priced, not executed."
        )
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
            column_config={"feature_id": None, "mode": st.column_config.SelectboxColumn(options=["interactive", "background"])},
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

    return template, idea, user, features, stages, threshold, ceiling, picks, price, fraction


def evaluation_spend(example: str, sample: bool) -> tuple[bool, str]:
    """Glass card 2: Evaluation Spend controls (Run / New run sit beside this in main)."""
    key = lambda name: f"{example}:{name}"
    step(
        2,
        "Evaluation Spend",
        "Approve measured runs and cap what they may spend"
        if not sample
        else "Sample mode runs nothing measurable.",
    )
    approved = st.checkbox(
        "I approve measured evaluation runs (live mode only; sample mode runs nothing)",
        value=False,
        key=key("approved"),
    )
    max_spend = st.text_input("Maximum evaluation spend (USD)", "0.50", key=key("spend"))
    return approved, max_spend


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
            "model": display_model_id(r["model_id"], r.get("tier")),
            "tokens": r["token_basis"],
            "monthly USD": num(r["gross_monthly_usd"]),
            "lower bound": r["lower_bound"],
        }
        for t in tables
        for r in t["rows"]
    ], label


def html_table(
    headers: list[str], rows: list[list[str]], *, numeric: set[int] | None = None, center: set[int] | None = None
) -> str:
    """Compact, semantic table for the static result views; cell markup is prepared and escaped by each caller."""
    numeric = numeric or set()
    center = center or set()
    head_cells = []
    for i, label in enumerate(headers):
        class_name = ' class="numeric"' if i in numeric else ' class="center"' if i in center else ""
        head_cells.append(f'<th scope="col"{class_name}>{escape(label)}</th>')
    body_rows = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            class_name = ' class="numeric"' if i in numeric else ' class="center"' if i in center else ""
            cells.append(f"<td{class_name}>{cell}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    head, body = "".join(head_cells), "".join(body_rows)
    return (
        '<div class="ca-table-wrap" role="region" aria-label="Scrollable results table" tabindex="0">'
        '<table class="ca-html-table"><thead><tr>' + head + "</tr></thead><tbody>" + body + "</tbody></table></div>"
    )


def display_number(value, *, currency: bool = False) -> str:
    amount = num(value)
    if amount is None or pd.isna(amount):
        return "—"
    return f"${amount:,.2f}" if currency else f"{amount:,.0f}"


def display_model_id(model_id: str, tier: str | None = None) -> str:
    normalized = str(model_id).removeprefix("openrouter/")
    if normalized.startswith("sample/") and normalized.endswith("-placeholder"):
        label = normalized.removeprefix("sample/").removesuffix("-placeholder").replace("-", " ").title()
        return f"{label} sample"
    return normalized


def feature_label_map(pack: dict) -> dict[str, str]:
    """Use saved brief descriptions as readable feature names; never render internal IDs."""
    feature_ids = list(dict.fromkeys(
        [str(run.get("feature_id")) for run in pack.get("feature_runs") or [] if run.get("feature_id")]
        + [str(table.get("feature_id")) for table in pack.get("stage_tables") or [] if table.get("feature_id")]
        + [str(table.get("feature_id")) for table in pack.get("openrouter_projection_tables") or []
           if table.get("feature_id")]
    ))
    descriptions = {}
    try:
        request_path = svc.result_path(str(pack["run_id"])).with_name(f"{pack['run_id']}.request.json")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        descriptions = {
            str(item.get("feature_id")): str(item.get("description") or "")
            for item in request.get("brief", {}).get("ai_features", [])
        }
    except (KeyError, OSError, ValueError):
        pass

    labels, counts = {}, {}
    for index, feature_id in enumerate(feature_ids, start=1):
        description = descriptions.get(feature_id, "")
        label = description.split("(", 1)[0].split(".", 1)[0].strip(" .–—")
        if not label:
            suffix = feature_id.partition("_")[2].replace("_", " ").strip()
            label = suffix.title() if suffix else f"Feature {index}"
        counts[label.casefold()] = counts.get(label.casefold(), 0) + 1
        if counts[label.casefold()] > 1:
            label = f"{label} {counts[label.casefold()]}"
        labels[feature_id] = label
    return labels


def humanize_feature_text(text: str, labels: dict[str, str]) -> str:
    for feature_id, label in sorted(labels.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(feature_id, label)
    return text


def cost_comparison_table(frame: pd.DataFrame) -> str:
    """Show the lowest priced model at each stage without overstating unknown prices."""
    lowest_rows = set()
    for _, group in frame.groupby("stage", sort=False):
        priced = [(index, num(row.get("monthly USD"))) for index, row in group.iterrows()]
        priced = [(index, price) for index, price in priced if price is not None]
        if len(priced) < 2:
            continue
        lowest = min(price for _, price in priced)
        lowest_rows.update(index for index, price in priced if price == lowest)

    rows = []
    for index, row in frame.iterrows():
        amount = display_number(row.get("monthly USD"), currency=True)
        if bool(row.get("lower bound")) and amount != "—":
            amount = "≥ " + amount
        selection = (
            '<span class="ca-cheapest-tag">Lowest shown</span>'
            if index in lowest_rows
            else '<span class="ca-pill" data-tone="neutral">—</span>'
        )
        rows.append([
            escape(str(row.get("stage") or "—")),
            display_number(row.get("users")),
            escape(str(row.get("model") or "—")),
            f'<span class="mono-value">{amount}</span>',
            selection,
        ])
    return html_table(
        ["Growth stage", "Users", "Model", "Monthly AI cost", "Selection"],
        rows,
        numeric={1, 3},
        center={4},
    )


SCENARIO_LABEL = {
    "cheapest_per_feature": "Lowest cost per feature",
    "recommended": "Quality-qualified stack",
}


def pipeline_view(events: list[dict], summary: dict, *, complete: bool = False):
    """Founder-facing Planner → Analyst → Critic highlight strip; raw steps stay under an expander."""
    phases = svc.pipeline_phases(events)
    copy = {"Planner": "Design tests", "Analyst": "Run models", "Critic": "Review outputs"}
    cells = []
    for phase in phases:
        state = "done" if complete else phase["state"]
        detail = "" if complete else (phase.get("detail") or ("in progress" if state == "active" else ""))
        mark = "✓" if state in ("active", "done") else "·"
        name = str(phase.get("name", ""))
        cells.append(
            f'<div class="ca-phase" data-state="{escape(state)}">'
            f'<span class="ca-phase-mark" aria-hidden="true">{mark}</span>'
            f'<div><strong>{escape(name)}</strong><span>{escape(copy.get(name, str(phase.get("copy", ""))))}</span>'
            + (f"<em>{escape(str(detail))}</em>" if detail else "")
            + "</div></div>"
        )
    st.markdown('<div class="ca-pipeline">' + "".join(cells) + "</div>", unsafe_allow_html=True)
    if not complete:
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
    heading, picker = st.columns([3.4, 1.2], vertical_alignment="center")
    with heading:
        st.markdown('<h3 class="ca-section-title">Monthly AI cost by growth stage</h3>', unsafe_allow_html=True)
        st.caption("AI costs only · build costs shown separately")
    label = lambda o: (
        "Lowest cost per feature"
        if o[0] == "cheapest_per_feature"
        else SCENARIO_LABEL.get(o[0]) or f"Same model for every feature: {o[1].removeprefix('openrouter/')}"
    )
    options = {label(key): key for key in dict.fromkeys((t["scenario"], t["model_id"]) for t in scoped)}
    option_labels = list(options)
    default_key = next(
        (
            key
            for key in options.values()
            if any(
                (t["scenario"], t["model_id"]) == key and num(t.get("monthly_usd")) is not None
                for t in scoped
            )
        ),
        next(iter(options.values())),
    )
    default_index = next(i for i, option in enumerate(option_labels) if options[option] == default_key)
    with picker:
        with st.container(key="ca-selector-card"):
            selected = st.selectbox("Model selection", option_labels, index=default_index, key="total_scenario")
    choice = options[selected]
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
    summary_rows = []
    for row in frame.to_dict("records"):
        budget = str(row["budget"] or "unknown")
        budget_key = budget.lower().replace(" ", "_")
        tone = "green" if budget_key == "under" else "red" if budget_key == "over" else "yellow" if budget_key == "unknown" else "neutral"
        cost = display_number(row["monthly AI cost USD"], currency=True)
        lead = "≥ " if bool(row["lower bound"]) and cost != "—" else ""
        summary_rows.append(
            [
                escape(str(row["stage"])),
                display_number(row["users"]),
                f'<span class="primary-value" title="Lower bound" >{lead}{cost}</span>',
                f'<span class="mono-value">{display_number(row["revenue USD"], currency=True)}</span>',
                f'<span class="mono-value">{escape(str(row["AI margin"] or "—"))}</span>',
                f'<span class="ca-pill" data-tone="{tone}">{escape(budget.title())}</span>',
            ]
        )
    st.markdown(
        html_table(
            ["Stage", "Users", "AI cost (USD)", "Revenue (USD)", "Margin", "Budget fit"],
            summary_rows,
            numeric={2, 3, 4},
            center={5},
        ),
        unsafe_allow_html=True,
    )
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
    st.caption(f"Price source: {price}. Unknown items make totals a lower bound. "
               + " ".join(n[0].upper() + n[1:] + "." for n in notes))
    compare = pd.DataFrame(
        [
            {"stage": t["stage"], "choice": label((t["scenario"], t["model_id"])), "USD": num(t["monthly_usd"])}
            for t in scoped
            if t["scenario"] != "recommended"
        ]
    )
    if not compare.empty:
        with st.expander("Compare cost scenarios", expanded=False):
            stage_chart(compare, "choice", "USD")
    st.divider()


def status_line(pack: dict) -> str:
    status = str(pack["status"])
    mode = str(pack["execution_mode"])
    return (
        '<div class="ca-status" aria-label="Run status">'
        f'<span class="ca-status-chip" data-status="{escape(status.lower())}">Status: {escape(status)}</span>'
        f'<span class="ca-status-chip">Mode: {escape(mode)}</span>'
        f'<span class="ca-status-chip">Spend: {display_number(pack["spend_usd"], currency=True)}</span>'
        f'<span class="ca-status-chip">Reqs: {escape(str(pack["dispatch_count"]))}</span>'
        '</div>'
    )


def recommendation_view(pack: dict, labels: dict[str, str]):
    """Show the cost comparison across the two tier picks."""
    picks = svc.tier_recommendations(pack)
    if not picks:
        return
    picks = [pick for pick in picks if pick.get("model_id")]
    if not picks:
        return
    stage_values = {pick.get("stage") for pick in picks}
    user_values = {pick.get("active_users") for pick in picks}
    comparable = len(picks) > 1 and len(stage_values) == 1 and len(user_values) == 1
    lowest_model_id = None
    if comparable:
        priced = [(pick, num(pick.get("monthly_usd"))) for pick in picks]
        priced = [(pick, price) for pick, price in priced if price is not None]
        if len(priced) == len(picks):
            lowest_model_id = min(priced, key=lambda item: item[1])[0]["model_id"]

    st.markdown("**Recommendation**")
    budget = pack.get("monthly_ai_budget_usd")
    has_budget = budget not in (None, "", "0", "0.0", "0.00", 0)
    st.caption(
        "Lowest-cost fit per tier at the furthest stage."
        if has_budget
        else "Lowest cost per tier at the largest stage."
    )
    if comparable:
        st.caption("The green tag compares these cards at the same stage.")
    titles = {"frontier": "Frontier", "open_source": "Open source"}
    fit_label = {"within": "Within budget", "over": "Over budget", "unknown": "Fit unknown",
                 "no_budget": "No budget"}
    basis_label = {"measured": "Actual tokens", "estimated": "Estimated tokens",
                   "mixed": "Mixed token counts", "unknown": "Token count unknown"}
    cols = st.columns(2)
    for col, pick in zip(cols, picks):
        with col:
            is_lowest = (
                lowest_model_id is not None
                and str(pick["model_id"]).removeprefix("openrouter/")
                == str(lowest_model_id).removeprefix("openrouter/")
            )
            card_key = "ca-rec-card-cheapest" if is_lowest else f"ca-rec-card-{pick['tier']}"
            with st.container(border=True, key=card_key):
                if is_lowest:
                    st.markdown('<span class="ca-cheapest-tag">Lowest shown</span>', unsafe_allow_html=True)
                st.markdown(f"**{titles[pick['tier']]}**")
                model_id = display_model_id(pick["model_id"], pick["tier"])
                st.markdown(f"**{escape(model_id)}**")
                st.metric("Monthly AI cost", display_number(pick["monthly_usd"], currency=True))
                st.caption(
                    f"{pick['stage']} · {display_number(pick['active_users'])} users · "
                    f"{basis_label.get(pick['token_basis'], 'Token count unknown')} · "
                    f"{fit_label.get(pick['budget_fit'], 'Fit unknown')}"
                )
                reason = str(pick.get("reason") or "")
                note = []
                lower_reason = reason.lower()
                marker = "cost unknown for "
                missing_start = lower_reason.find(marker)
                missing = ""
                if missing_start >= 0:
                    missing_start += len(marker)
                    missing_end = lower_reason.find(", so the total", missing_start)
                    if missing_end < 0:
                        missing_end = reason.find(".", missing_start)
                    missing = reason[missing_start:missing_end].strip()
                if missing:
                    note.append("No price: " + humanize_feature_text(missing, labels))
                lower_reason = reason.lower()
                if "quality-qualified for" in lower_reason:
                    note.append("Critical checks passed")
                elif "quality was not measured" in lower_reason:
                    note.append("Quality not checked")
                else:
                    note.append("Quality review pending")
                st.caption(" · ".join(note))


def results(pack: dict):
    labels = feature_label_map(pack)
    st.markdown(
        '<header class="ca-results-head"><div><h2 class="ca-results-title">'
        '<span class="ca-results-number">3</span>DecisionPack Results</h2>'
        '</div>'
        + status_line(pack)
        + '</header>',
        unsafe_allow_html=True,
    )
    status = pack["status"]
    events = [json.loads(line) for line in svc.trace_text(pack).splitlines() if line.strip()]
    summary, _ = svc.progress_rows(events)
    pipeline_view(events, summary, complete=status == "complete")
    if status != "complete":
        st.info("This result is " + status + ". Missing or unknown evidence is listed below, not filled in.")
        if svc.outbox_hint(pack):
            st.warning(svc.outbox_hint(pack))
        why = svc.stop_reason(pack)
        if why:
            st.error("Why it stopped: " + why)
            if svc.setup_hint(why):
                st.warning(svc.setup_hint(why))
    recommendation_view(pack, labels)
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
        st.markdown('<h3 class="ca-section-title">Estimated vs actual token counts</h3>', unsafe_allow_html=True)
        st.caption("Actual counts appear only after a model runs live.")
        token_rows = []
        for run in runs:
            executed = bool(run.get("executed"))
            state_label = "Actual run" if executed else "Estimate only"
            state_tone = "green" if executed else "yellow"
            estimated = run.get("estimated") or {}
            actual = run.get("measured_mean") or {}
            estimated_value = display_number(estimated.get("output_tokens"))
            actual_value = display_number(actual.get("output_tokens"))
            token_rows.append(
                [
                    escape(labels.get(str(run["feature_id"]), "Feature")),
                    f'<span class="ca-pill" data-tone="{state_tone}">{state_label}</span>',
                    f'<span class="{"token-estimate" if estimated_value != "—" else "token-missing"}">{estimated_value}</span>',
                    f'<span class="{"token-actual" if actual_value != "—" else "token-missing"}">{actual_value}</span>',
                ]
            )
        st.markdown(
            html_table(["Feature", "Run status", "Estimated tokens", "Actual tokens"], token_rows, numeric={2, 3}),
            unsafe_allow_html=True,
        )
        st.markdown('<h3 class="ca-section-title">Feature cost by growth stage</h3>', unsafe_allow_html=True)
        if not rows:
            st.write("No cost rows in this pack.")
        else:
            frame = pd.DataFrame(rows)
            feature_ids = list(dict.fromkeys(frame["feature"]))
            feature_options = {}
            for index, feature_id in enumerate(feature_ids, start=1):
                label = labels.get(str(feature_id), f"Feature {index}")
                if label in feature_options:
                    label = f"{label} {index}"
                feature_options[label] = feature_id
            selected_label = st.selectbox("Feature", list(feature_options), key="cost_feature")
            subset = frame[frame["feature"] == feature_options[selected_label]]
            stage_chart(subset, "model", "monthly USD")
            st.markdown(cost_comparison_table(subset), unsafe_allow_html=True)
            st.caption("Green markers and tags show the lowest priced option per stage.")

    with tabs[1]:
        st.markdown('<h3 class="ca-check-title">Deterministic checks decide quality. The Critic only flags.</h3>', unsafe_allow_html=True)
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
            check_rows = []
            for check in checks:
                result = str(check["result"])
                tone = "green" if result == "pass" else "red" if result == "fail" else "blue"
                check_rows.append(
                    [
                        escape(labels.get(str(check["feature"]), "Feature")),
                        escape(str(check["model"])),
                        escape(str(check["check"])),
                        f'<span class="ca-pill" data-tone="{tone}">{escape(result.title())}</span>',
                    ]
                )
            st.markdown(
                html_table(["Feature", "Model", "Check", "Result"], check_rows, center={3}),
                unsafe_allow_html=True,
            )
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
            flag_rows = [
                {"kind": f.get("kind"), "severity": f.get("severity"),
                 "feature": labels.get(str(f.get("feature_id")), "Feature"),
                 "model": display_model_id(f.get("model_id") or ""),
                 "claim": humanize_feature_text(str(f.get("claim") or ""), labels)}
                for f in findings
            ]
            st.dataframe(pd.DataFrame(flag_rows), width="stretch", hide_index=True)

    with tabs[2]:
        if pack.get("questions"):
            st.markdown("**Questions to resolve**")
            for item in pack["questions"]:
                st.write("- " + humanize_feature_text(str(item), labels))
        if pack["risks"]:
            st.dataframe(
                pd.DataFrame([{k: r.get(k) for k in ("severity", "description", "origin")} for r in pack["risks"]]),
                width="stretch",
                hide_index=True,
            )
        for item in pack["limitations"]:
            st.write("- " + humanize_feature_text(str(item), labels))
        with st.expander(f"Evidence gaps ({len(pack['evidence_gaps'])}): unknown or assumed values, never filled in"):
            st.dataframe(pd.DataFrame(pack["evidence_gaps"]), width="stretch", hide_index=True)
        with st.expander("Build panel (secondary; never added to running costs)"):
            panel = pack["build_panel"]
            for item in panel.get("reasons", []) + panel.get("questions", []):
                st.write("- " + humanize_feature_text(str(item), labels))
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
            file_name=f"decision-pack{suffix}.pack.json",
            mime="application/json",
        )
        if events:
            st.download_button(
                "Download trace (JSONL)",
                svc.trace_text(pack),
                file_name=f"decision-pack{suffix}.trace.jsonl",
            )


def main():
    style()
    example, sample = controls()
    bindings = price_data(sample)
    state = st.session_state
    state.setdefault("run_id", svc.new_run_id())
    stored = svc.load_result(state["run_id"])
    outcome = state.get("outcome") or ({"result": stored, "reused": True} if stored else None)
    banner(outcome["result"] if outcome and "execution_mode" in outcome["result"] else None, sample)

    template, idea, user, features, stages, threshold, ceiling, picks, price, fraction = form(
        example, sample, bindings
    )
    with st.container(border=True, key="eval-run"):
        with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
            with st.container():
                approved, max_spend = evaluation_spend(example, sample)
            with st.container(key="eval-actions"):
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
                blocked = parsed is None or state.get("busy", False) or (not sample and not bindings)
                with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                    run_clicked = st.button("Run", type="primary", disabled=blocked)
                    if st.button("New run", type="secondary"):
                        state["run_id"], state["outcome"] = svc.new_run_id(), None
                        st.rerun()
    if problem:
        st.error("Fix the inputs: " + problem)
    if not sample and not approved:
        st.warning(
            "Approval is not ticked: a live run will read prices and pick candidates, then stop before any "
            "model request (status needs_input). Tick the approval box above to measure."
        )
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
