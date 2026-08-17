"""Shared visual system for every Streamlit entry point."""
from __future__ import annotations

import streamlit as st


PRIMARY = "#0B5F6B"
PRIMARY_STRONG = "#084C57"
ACCENT = "#175CD3"
# Safety colours are used semantically: red for danger/failure, amber for
# caution, blue for active processing, and green for safe/ready conditions.
FIRE_RED = "#B42318"
CAUTION_AMBER = "#B54708"
ESCAPE_GREEN = "#147A50"
RISK_COLORS = {
    "low": "#147A50",
    "medium": "#8A4B08",
    "high": "#B42318",
}
STATUS_COLORS = {
    "pass": "#147A50",
    "fail": "#B42318",
    "warn": "#8A4B08",
    "review": "#0E7490",
    "insufficient": "#6941C6",
    "unknown": "#475467",
}


APP_CSS = """
<style>
    :root {
        --app-brand: #0B5F6B;
        --app-brand-strong: #084C57;
        --app-accent: #175CD3;
        --app-background: var(--background-color, #ffffff);
        --app-panel: var(--secondary-background-color, #f1f5f7);
        --app-panel-strong: var(--background-color, #ffffff);
        --app-text: var(--text-color, #172033);
        --app-heading: var(--text-color, #172033);
        --app-muted: color-mix(in srgb, var(--app-text) 70%, var(--app-background));
        --app-border: color-mix(in srgb, var(--app-text) 18%, var(--app-background));
        --app-border-strong: color-mix(in srgb, var(--app-text) 30%, var(--app-background));
        --app-info: color-mix(in srgb, #175CD3 10%, var(--app-background));
        --app-warning: color-mix(in srgb, #B54708 11%, var(--app-background));
        --app-danger: color-mix(in srgb, #B42318 10%, var(--app-background));
        --app-success: color-mix(in srgb, #147A50 10%, var(--app-background));
        --app-status-pass: #147A50;
        --app-status-fail: #B42318;
        --app-status-warn: #8A4B08;
        --app-fire-red: #B42318;
        --app-caution: #B54708;
        --app-escape-green: #147A50;
        --app-processing-blue: #175CD3;
        --app-shadow: 0 10px 30px rgba(16, 42, 67, .08);
        --app-shadow-hover: 0 16px 40px rgba(16, 42, 67, .14);
    }

    .stApp,
    [data-testid="stAppViewContainer"] {
        background: var(--app-background);
        color: var(--app-text);
    }
    .stApp *,
    .stApp *::before,
    .stApp *::after {
        box-sizing: border-box;
    }
    [data-testid="stAppViewContainer"] > .main {
        background-image:
            radial-gradient(circle at 92% 0%, rgba(11, 95, 107, .07), transparent 22rem),
            radial-gradient(circle at 5% 35%, rgba(23, 92, 211, .045), transparent 26rem);
    }
    .block-container {
        width: min(100%, 1480px);
        max-width: 1480px;
        padding: clamp(1rem, 2vw, 1.75rem) clamp(.85rem, 2vw, 2rem) 4rem;
    }
    .stApp p,
    .stApp li,
    .stApp label,
    .stApp .stMarkdown {
        color: var(--app-text);
    }
    .stApp a {
        color: color-mix(in srgb, var(--app-text) 40%, var(--app-accent));
        text-decoration-thickness: .08em;
        text-underline-offset: .16em;
    }
    .stApp a:hover {
        color: color-mix(in srgb, var(--app-text) 25%, var(--app-brand));
    }

    .app-hero {
        position: relative;
        overflow: hidden;
        min-height: 100%;
        padding: 1.35rem 1.5rem;
        border: 1px solid var(--app-border);
        border-radius: 18px;
        background:
            linear-gradient(135deg, color-mix(in srgb, var(--app-brand) 9%, var(--app-panel-strong)), var(--app-panel-strong) 68%);
        box-shadow: var(--app-shadow);
    }
    .st-key-app-header [data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }
    .app-hero::after {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        top: -150px;
        right: -80px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(23, 92, 211, .2), transparent 70%);
        pointer-events: none;
    }
    .app-kicker,
    .scenario-kicker,
    .welcome-kicker {
        color: color-mix(in srgb, var(--app-text) 35%, var(--app-brand));
        font-size: .76rem;
        font-weight: 800;
        letter-spacing: .09em;
        text-transform: uppercase;
    }
    .main-title {
        max-width: 1050px;
        margin: .35rem 0 .35rem;
        color: var(--app-heading);
        font-size: clamp(1.7rem, 3vw, 2.45rem);
        font-weight: 780;
        letter-spacing: -.035em;
        line-height: 1.12;
    }
    .sub-title {
        max-width: 920px;
        margin: 0;
        color: var(--app-muted) !important;
        font-size: 1rem;
        line-height: 1.55;
    }
    .hero-author {
        min-height: 100%;
        padding: 1.15rem 1.2rem;
        border: 1px solid var(--app-border);
        border-top: 4px solid var(--app-brand);
        border-radius: 18px;
        background: var(--app-panel-strong);
        box-shadow: var(--app-shadow);
        color: var(--app-text);
    }
    .hero-author .author-label {
        display: block;
        margin-bottom: .55rem;
        color: var(--app-muted);
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .08em;
        text-transform: uppercase;
    }
    .hero-author strong {
        display: block;
        margin-bottom: .45rem;
        color: var(--app-heading);
        font-size: 1.04rem;
    }
    .hero-author a {
        display: inline-block;
        margin-top: .22rem;
        font-size: .86rem;
    }

    .section-header {
        margin: .6rem 0 1.25rem;
        padding: 0 0 .75rem;
        border-bottom: 1px solid var(--app-border);
        color: var(--app-heading);
        font-size: clamp(1.25rem, 2vw, 1.55rem);
        font-weight: 760;
        letter-spacing: -.025em;
    }
    .metric-container {
        padding: 1rem;
        border-radius: 14px;
        background: linear-gradient(135deg, var(--app-brand), var(--app-accent));
        color: #ffffff;
    }
    .metric-card {
        min-height: 136px;
        margin-bottom: 1rem;
        padding: 1rem;
        border: 1px solid var(--app-border);
        border-top: 4px solid var(--metric-accent, var(--app-brand));
        border-radius: 14px;
        background: var(--app-panel-strong);
        box-shadow: var(--app-shadow);
    }
    .metric-card__label {
        margin: 0;
        color: var(--app-muted) !important;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .055em;
        text-transform: uppercase;
    }
    .metric-card__value {
        margin: .2rem 0 .12rem;
        color: var(--app-heading) !important;
        font-size: 1.85rem;
        font-weight: 780;
        letter-spacing: -.035em;
        line-height: 1.15;
    }
    .metric-card__subtitle {
        margin: 0;
        color: var(--app-muted) !important;
        font-size: .78rem;
        line-height: 1.35;
    }

    .status-pass { color: color-mix(in srgb, var(--app-text) 35%, var(--app-status-pass)); font-weight: 700; }
    .status-fail { color: color-mix(in srgb, var(--app-text) 35%, var(--app-status-fail)); font-weight: 700; }
    .status-warn { color: color-mix(in srgb, var(--app-text) 35%, var(--app-status-warn)); font-weight: 700; }
    .info-box,
    .warning-box,
    .danger-box,
    .success-box {
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid var(--app-border);
        border-left-width: 4px;
        border-radius: 10px;
        color: var(--app-text);
    }
    .info-box { background: var(--app-info); border-left-color: #175CD3; }
    .warning-box { background: var(--app-warning); border-left-color: #B54708; }
    .danger-box { background: var(--app-danger); border-left-color: #B42318; }
    .success-box { background: var(--app-success); border-left-color: #147A50; }
    [data-testid="stAlert"] {
        border: 1px solid var(--app-border);
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: .25rem;
        overflow-x: auto;
        padding: .35rem;
        border: 1px solid var(--app-border);
        border-radius: 14px;
        background: var(--app-panel);
        scrollbar-width: thin;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 0 0 auto;
        min-height: 2.55rem;
        padding: .55rem .9rem;
        border-radius: 10px;
        background: transparent;
        color: var(--app-text);
        font-size: .88rem;
        font-weight: 650;
        transition: background-color .15s ease, color .15s ease, transform .15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: color-mix(in srgb, var(--app-brand) 9%, var(--app-panel));
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: var(--app-brand) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(11, 95, 107, .22);
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] p {
        color: #ffffff !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        min-height: 2.55rem;
        border: 1px solid var(--app-border-strong);
        border-radius: 10px;
        font-weight: 700;
        transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        border-color: var(--app-brand);
        box-shadow: 0 7px 18px rgba(11, 95, 107, .16);
    }
    [data-testid="stBaseButton-primary"] {
        border-color: var(--app-brand) !important;
        background: var(--app-brand) !important;
        color: #ffffff !important;
    }
    [data-testid="stBaseButton-primary"]:hover {
        border-color: var(--app-brand-strong) !important;
        background: var(--app-brand-strong) !important;
    }
    .st-key-analysis-action-ready [data-testid="stBaseButton-primary"] {
        border-color: var(--app-escape-green) !important;
        background: var(--app-escape-green) !important;
        box-shadow: 0 7px 18px color-mix(in srgb, var(--app-escape-green) 24%, transparent);
    }
    .st-key-analysis-action-ready [data-testid="stBaseButton-primary"]:hover {
        border-color: color-mix(in srgb, var(--app-escape-green) 78%, #000000) !important;
        background: color-mix(in srgb, var(--app-escape-green) 86%, #000000) !important;
    }
    .st-key-analysis-action-processing button:disabled {
        border-color: var(--app-processing-blue) !important;
        background: var(--app-processing-blue) !important;
        color: #ffffff !important;
        opacity: 1 !important;
    }
    :where(button, a, input, textarea, [role="tab"], [role="checkbox"], [role="radio"]):focus-visible {
        outline: 3px solid color-mix(in srgb, #2E90FA 75%, var(--app-background));
        outline-offset: 2px;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid var(--app-border);
        background:
            linear-gradient(180deg, color-mix(in srgb, var(--app-brand) 7%, var(--app-panel)), var(--app-panel) 18rem);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--app-heading);
        letter-spacing: -.025em;
    }
    [data-testid="stSidebar"] hr {
        border-color: var(--app-border);
    }
    .system-status-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: .75rem;
        padding: .45rem 0;
        border-bottom: 1px solid var(--app-border);
        font-size: .8rem;
    }
    .system-status-row:last-child { border-bottom: 0; }
    .system-status-row span:last-child { color: var(--app-muted); font-weight: 700; text-align: right; }
    [data-testid="stFileUploaderDropzone"] {
        border: 1.5px dashed color-mix(in srgb, var(--app-brand) 62%, var(--app-border));
        border-radius: 14px;
        background: color-mix(in srgb, var(--app-brand) 6%, var(--app-panel-strong));
        transition: border-color .15s ease, background-color .15s ease, box-shadow .15s ease;
    }
    [data-testid="stFileUploaderDropzone"]:hover,
    [data-testid="stFileUploaderDropzone"]:focus-within {
        border-color: var(--app-brand);
        background: color-mix(in srgb, var(--app-brand) 10%, var(--app-panel-strong));
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--app-brand) 14%, transparent);
    }
    [data-testid="stFileUploaderDropzone"] small {
        color: var(--app-muted) !important;
    }
    .upload-receipt {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: .65rem;
        align-items: center;
        margin: .55rem 0 .15rem;
        padding: .7rem .75rem;
        border: 1px solid color-mix(in srgb, var(--upload-accent) 42%, var(--app-border));
        border-left: 4px solid var(--upload-accent);
        border-radius: 11px;
        background: color-mix(in srgb, var(--upload-accent) 8%, var(--app-panel-strong));
    }
    .upload-receipt--ready { --upload-accent: var(--app-escape-green); }
    .upload-receipt--evidence { --upload-accent: var(--app-processing-blue); }
    .upload-receipt__mark {
        display: grid;
        width: 1.65rem;
        height: 1.65rem;
        place-items: center;
        border-radius: 50%;
        background: var(--upload-accent);
        color: #ffffff;
        font-size: .78rem;
        font-weight: 900;
    }
    .upload-receipt strong,
    .upload-receipt small {
        display: block;
        min-width: 0;
        overflow-wrap: anywhere;
    }
    .upload-receipt strong { color: var(--app-heading); font-size: .82rem; }
    .upload-receipt small { margin-top: .08rem; color: var(--app-muted); font-size: .72rem; }

    .analysis-state {
        --analysis-accent: var(--app-caution);
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: .7rem;
        align-items: start;
        margin: .45rem 0 .7rem;
        padding: .78rem;
        border: 1px solid color-mix(in srgb, var(--analysis-accent) 45%, var(--app-border));
        border-radius: 12px;
        background: color-mix(in srgb, var(--analysis-accent) 9%, var(--app-panel-strong));
    }
    .analysis-state--waiting { --analysis-accent: var(--app-caution); }
    .analysis-state--ready,
    .analysis-state--complete { --analysis-accent: var(--app-escape-green); }
    .analysis-state--processing { --analysis-accent: var(--app-processing-blue); }
    .analysis-state--error { --analysis-accent: var(--app-fire-red); }
    .analysis-state__indicator {
        width: .78rem;
        height: .78rem;
        margin-top: .22rem;
        border: 3px solid var(--analysis-accent);
        border-radius: 50%;
        background: var(--app-panel-strong);
    }
    .analysis-state--ready .analysis-state__indicator,
    .analysis-state--complete .analysis-state__indicator {
        background: var(--analysis-accent);
        box-shadow: 0 0 0 4px color-mix(in srgb, var(--analysis-accent) 14%, transparent);
    }
    .analysis-state--processing .analysis-state__indicator {
        border-top-color: transparent;
        animation: analysis-spin .8s linear infinite;
    }
    .analysis-state--error .analysis-state__indicator {
        background: var(--analysis-accent);
    }
    .analysis-state strong {
        display: block;
        color: var(--app-heading);
        font-size: .84rem;
        line-height: 1.3;
    }
    .analysis-state p {
        margin: .15rem 0 0;
        color: var(--app-muted) !important;
        font-size: .75rem;
        line-height: 1.4;
    }
    @keyframes analysis-spin { to { transform: rotate(360deg); } }

    [data-testid="stMetric"] {
        min-height: 106px;
        padding: .8rem .9rem;
        border: 1px solid var(--app-border);
        border-radius: 13px;
        background: var(--app-panel-strong);
        box-shadow: 0 5px 16px rgba(16, 42, 67, .055);
    }
    [data-testid="stMetricLabel"] { color: var(--app-muted); }
    [data-testid="stMetricValue"] { color: var(--app-heading); letter-spacing: -.03em; }
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    [data-testid="stExpander"] {
        overflow: hidden;
        border-color: var(--app-border);
        border-radius: 12px;
    }

    .scenario-card,
    .scenario-detail-card {
        position: relative;
        overflow: hidden;
        margin: .75rem 0;
        padding: 1.05rem 1.15rem;
        border: 1px solid var(--app-border);
        border-left: 6px solid var(--scenario-accent, var(--app-brand));
        border-radius: 15px;
        background: var(--app-panel-strong);
        box-shadow: var(--app-shadow);
    }
    .scenario-card {
        background:
            linear-gradient(135deg, color-mix(in srgb, var(--scenario-accent, var(--app-brand)) 7%, var(--app-panel-strong)), var(--app-panel-strong) 64%);
    }
    .scenario-card:hover {
        border-color: color-mix(in srgb, var(--scenario-accent, var(--app-brand)) 65%, var(--app-border));
        box-shadow: var(--app-shadow-hover);
    }
    .scenario-card h3,
    .scenario-detail-card h4 {
        margin: .25rem 0;
        color: var(--app-heading);
        letter-spacing: -.02em;
    }
    .scenario-card__meta {
        margin: .2rem 0 0 !important;
        color: var(--app-muted) !important;
        font-size: .8rem;
    }
    .scenario-detail-card {
        border-left-color: var(--app-accent);
        line-height: 1.65;
    }

    .welcome-hero {
        max-width: 980px;
        margin: .75rem auto 1.35rem;
        padding: 1.6rem;
        border: 1px solid var(--app-border);
        border-radius: 18px;
        background: linear-gradient(135deg, color-mix(in srgb, var(--app-brand) 8%, var(--app-panel-strong)), var(--app-panel-strong));
        box-shadow: var(--app-shadow);
        text-align: left;
    }
    .welcome-hero h2 {
        margin: .35rem 0 .55rem;
        color: var(--app-heading);
        font-size: clamp(1.45rem, 2.5vw, 2rem);
        letter-spacing: -.03em;
    }
    .welcome-hero p { margin: 0; color: var(--app-muted) !important; line-height: 1.6; }
    .workflow-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .85rem;
        margin: 0 auto 1.2rem;
    }
    .workflow-step {
        min-height: 150px;
        padding: 1rem;
        border: 1px solid var(--app-border);
        border-radius: 14px;
        background: var(--app-panel-strong);
    }
    .workflow-step__number {
        display: inline-grid;
        width: 2rem;
        height: 2rem;
        place-items: center;
        border-radius: 9px;
        background: var(--app-brand);
        color: #ffffff;
        font-size: .74rem;
        font-weight: 800;
    }
    .workflow-step h3 { margin: .7rem 0 .3rem; color: var(--app-heading); font-size: 1rem; }
    .workflow-step p { margin: 0; color: var(--app-muted) !important; font-size: .85rem; line-height: 1.5; }
    .technology-strip {
        margin: .8rem auto 0;
        padding: .8rem 1rem;
        border: 1px solid var(--app-border);
        border-radius: 12px;
        background: var(--app-panel);
        color: var(--app-muted);
        font-size: .82rem;
        line-height: 1.55;
        text-align: center;
    }

    @media (max-width: 1000px) {
        .workflow-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .hero-author { margin-top: .35rem; }
    }
    @media (max-width: 900px) {
        .st-key-app-header [data-testid="stHorizontalBlock"] {
            flex-direction: column;
        }
        .st-key-app-header [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 auto !important;
        }
        .stTabs [data-baseweb="tab"] {
            min-height: 2.35rem;
            padding: .48rem .7rem;
            font-size: .82rem;
        }
    }
    @media (max-width: 700px) {
        .block-container { width: 100%; padding: 1rem .7rem 3rem; }
        .app-hero, .hero-author, .welcome-hero { border-radius: 14px; }
        .app-hero { padding: 1.1rem; }
        .main-title { font-size: clamp(1.45rem, 7vw, 1.85rem); }
        .workflow-grid { grid-template-columns: 1fr; }
        .workflow-step { min-height: auto; }
        .stTabs [data-baseweb="tab"] { padding: .5rem .72rem; font-size: .82rem; }
        .scenario-card, .scenario-detail-card { padding: .9rem; }
        [data-testid="stMetricValue"] { font-size: 1.55rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            transition-duration: .01ms !important;
            animation-duration: .01ms !important;
            animation-iteration-count: 1 !important;
        }
        .stButton > button,
        .stDownloadButton > button,
        [data-baseweb="tab"],
        .scenario-card {
            transform: none !important;
        }
    }
</style>
"""


def apply_app_theme() -> None:
    """Inject the shared accessible theme after ``st.set_page_config``."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
