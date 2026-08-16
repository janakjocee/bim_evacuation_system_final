"""
Professional Streamlit UI for BIM Evacuation System.

An evacuation-screening decision-support system with:
- Human-in-the-Loop (HITL)
- Explainability and decision trace
- Multi-tab engineering workflow
- Interactive visualizations

MSc Data Science Dissertation - University of Greenwich
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import copy
import hashlib
import html
import json
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import time
from typing import List, Dict, Any, Optional

import src as project_package
from src.pipeline.evacuation_pipeline import EvacuationPipeline, PipelineResult
from src.pipeline.manual_corrections import apply_manual_corrections
from src.bim_processing.ifc_validation import SUPPORTED_SCHEMA_LABEL
from src.nlp.document_loader import RegulationDocumentError, extract_regulation_text
from src.scenario.ifc_dataset_exporter import building_to_worst_case_dataset
from src.utils.logger import get_logger
from src.utils.helpers import RiskLevel, ComplianceStatus
from src.ui.ui_components import (
    render_metric_card, get_risk_color, get_risk_badge, get_compliance_badge,
    create_risk_pie_chart, create_scenario_bar_chart, create_route_comparison_chart,
    create_network_graph_viz, create_risk_heatmap, render_scenario_card,
    render_explanation_panel, render_expert_review_controls, create_export_summary
)
from src.ui.visualization_3d import create_ifc_3d_figure, create_ifc_plan_figure
from src.ui.export_helpers import build_scenarios_csv, build_scenarios_xml, safe_uploaded_filename
from src.evaluation.expert_review import RATING_FIELDS, build_preliminary_domain_review
from src.evaluation.space_classification import (
    build_blinded_label_review_pack,
    load_records as load_space_label_records,
    parse_label_review_pack_csv,
    serialise_label_review_pack,
    validate_label_review_pack,
)
from src.ui.accessibility import MANUAL_ACCESSIBILITY_CHECKS, build_manual_accessibility_record
from src.utils.model_transparency import (
    ACADEMIC_USE_NOTICE,
    screening_index_semantics,
    standard_assumption_registry,
)

# Streamlit Cloud can keep the already-imported package object during a hot
# redeploy. Fall back to the approved title when that object predates the
# metadata constants added to src/__init__.py.
PROJECT_TITLE = getattr(
    project_package,
    "PROJECT_TITLE",
    "AI-Driven Generation of Evacuation Scenarios from Building Information Models",
)
PROJECT_SUBTITLE = getattr(
    project_package,
    "PROJECT_SUBTITLE",
    "AI-Assisted Research Prototype: Deterministic IFC/Graph Analysis + NLP Evidence Retrieval",
)

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title=PROJECT_TITLE,
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CUSTOM CSS STYLING
# ==============================================================================
st.markdown("""
<style>
    :root {
        --app-text: #172033;
        --app-muted: #536174;
        --app-panel: #f7f9fc;
        --app-panel-strong: #ffffff;
        --app-border: #d9e1ec;
        --app-heading: #13213c;
        --app-info: #e8f3ff;
        --app-warning: #fff6db;
        --app-danger: #ffe9ec;
        --app-success: #e7f6ed;
        --app-status-pass: #176b35;
        --app-status-fail: #b42318;
        --app-status-warn: #765500;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --app-text: #edf3fb;
            --app-muted: #bdc9d8;
            --app-panel: #172033;
            --app-panel-strong: #202b3d;
            --app-border: #3a4a61;
            --app-heading: #f7fbff;
            --app-info: #153653;
            --app-warning: #4a3c13;
            --app-danger: #4a2028;
            --app-success: #153d2b;
            --app-status-pass: #7ee2a8;
            --app-status-fail: #ff9b9b;
            --app-status-warn: #ffd166;
        }
        div[style*="background-color: #f8f9fa"],
        div[style*="background-color: white"] {
            background-color: var(--app-panel-strong) !important;
            color: var(--app-text) !important;
        }
        div[style*="color: #555"],
        p[style*="color: #666"],
        p[style*="color: #999"],
        span[style*="color: #555"] {
            color: var(--app-muted) !important;
        }
        strong[style*="color: #1a1a2e"],
        h4[style*="color: #333"] {
            color: var(--app-heading) !important;
        }
    }
    .stApp, [data-testid="stAppViewContainer"] { color: var(--app-text); }
    p, li, label, .stMarkdown { color: var(--app-text); }
    /* Main title */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--app-heading);
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: var(--app-muted);
        margin-bottom: 1.5rem;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--app-heading);
        border-bottom: 2px solid var(--app-border);
        padding-bottom: 0.5rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Cards */
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    
    /* Status indicators */
    .status-pass {
        color: var(--app-status-pass);
        font-weight: bold;
    }
    .status-fail {
        color: var(--app-status-fail);
        font-weight: bold;
    }
    .status-warn {
        color: var(--app-status-warn);
        font-weight: bold;
    }
    
    /* Info boxes */
    .info-box {
        background-color: var(--app-info);
        color: var(--app-text);
        border-left: 4px solid #2196F3;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 4px 4px 0;
    }
    
    .warning-box {
        background-color: var(--app-warning);
        color: var(--app-text);
        border-left: 4px solid #FFC107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 4px 4px 0;
    }
    
    .danger-box {
        background-color: var(--app-danger);
        color: var(--app-text);
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 4px 4px 0;
    }
    
    .success-box {
        background-color: var(--app-success);
        color: var(--app-text);
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 4px 4px 0;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--app-panel);
        color: var(--app-text);
        border-radius: 4px 4px 0 0;
        padding: 10px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a1a2e !important;
        color: white !important;
    }
    
    /* Dataframe styling */
    .dataframe {
        font-size: 0.85rem;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 5px 16px rgba(27, 94, 170, 0.22);
    }
    @media (prefers-reduced-motion: reduce) {
        .stButton>button, [data-baseweb="tab"], .scenario-card {
            transition: none !important;
            transform: none !important;
        }
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid var(--app-border);
        background-image: linear-gradient(180deg, rgba(63, 101, 220, .07), transparent 28%);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        letter-spacing: -.02em;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, var(--app-panel-strong), var(--app-panel));
        border: 1px solid var(--app-border);
        border-radius: 12px;
        padding: .65rem .8rem;
        box-shadow: 0 5px 16px rgba(20, 42, 80, .06);
    }
    [data-baseweb="tab-list"] {
        background: var(--app-panel);
        padding: 5px;
        border-radius: 12px;
        border: 1px solid var(--app-border);
    }
    [data-baseweb="tab"] {
        transition: transform .15s ease, background-color .15s ease;
    }
    [data-baseweb="tab"]:hover {
        transform: translateY(-1px);
    }
    [data-testid="stFileUploaderDropzone"] {
        border-radius: 14px;
        border: 1px dashed #6d91ef;
        background: linear-gradient(135deg, rgba(74, 116, 225, .08), transparent);
    }
    .scenario-detail-card {
        background: var(--app-panel-strong);
        color: var(--app-text);
        border: 1px solid var(--app-border);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.75rem 0;
        box-shadow: 0 8px 24px rgba(15, 33, 57, 0.08);
    }
    .scenario-detail-card strong, .scenario-detail-card h4 {
        color: var(--app-heading);
    }
    .scenario-card {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, color-mix(in srgb, var(--app-panel-strong) 92%, #4f8cff 8%), var(--app-panel-strong));
        border: 1px solid var(--app-border);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        margin-top: 0.5rem;
        box-shadow: 0 8px 28px rgba(15, 33, 57, 0.09);
    }
    .scenario-card::after {
        content: "";
        position: absolute;
        width: 140px;
        height: 140px;
        right: -80px;
        top: -85px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(85, 132, 255, .28), transparent 70%);
        pointer-events: none;
    }
    .scenario-card:hover {
        border-color: #5b8cff;
        box-shadow: 0 14px 38px rgba(56, 103, 214, 0.16);
    }
    .hero-author {
        background: linear-gradient(135deg, rgba(50, 92, 210, .12), rgba(126, 80, 220, .12));
        border: 1px solid var(--app-border);
        border-radius: 12px;
        padding: .7rem .9rem;
        text-align: right;
        color: var(--app-text);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        'pipeline_result': None,
        'baseline_pipeline_result': None,
        'processing_done': False,
        'selected_scenario_index': 0,
        'expert_reviews': {},
        'regulation_text': None,
        'rag_enabled': True,
        'active_tab': 0,
        'selected_scenario_id': None,
        'graph_viz_enabled': True,
        'show_explanations': True,
        'domain_review_records': [],
        'accessibility_audit_records': [],
        'space_label_review_validation': None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()


def create_selected_route_figure(result, scenario):
    """Create an interactive route diagram with the selected route highlighted."""
    building = result.building
    positions = {}
    for index, (space_id, space) in enumerate(building.spaces.items()):
        if space.bounding_box:
            minimum, maximum = space.bounding_box
            positions[space_id] = ((minimum.x + maximum.x) / 2, (minimum.y + maximum.y) / 2)
        else:
            positions[space_id] = (index, 0)
    for door_id, door in building.doors.items():
        positions[door_id] = (door.location.x, door.location.y)

    route = scenario.evacuation_route.path
    edge_x, edge_y = [], []
    for first, second in zip(route, route[1:]):
        if first in positions and second in positions:
            edge_x.extend([positions[first][0], positions[second][0], None])
            edge_y.extend([positions[first][1], positions[second][1], None])

    figure = go.Figure()
    if edge_x:
        figure.add_trace(go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(color="#ff8f00", width=7), name="Selected evacuation route",
        ))
    visible_nodes = [node for node in route if node in positions]
    colors = [
        "#d32f2f" if node == scenario.origin_space_id
        else "#00c853" if node == scenario.evacuation_route.destination
        else "#1565c0"
        for node in visible_nodes
    ]
    figure.add_trace(go.Scatter(
        x=[positions[node][0] for node in visible_nodes],
        y=[positions[node][1] for node in visible_nodes],
        mode="markers+text",
        marker=dict(size=18, color=colors, line=dict(color="white", width=2)),
        text=[building.spaces[node].name if node in building.spaces else building.doors[node].name for node in visible_nodes],
        textposition="top center",
        hovertext=visible_nodes,
        hoverinfo="text",
        name="Route nodes",
    ))
    figure.update_layout(
        title="Selected Evacuation Route",
        height=500,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="#f7f9fc",
        xaxis=dict(visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return figure


def render_selected_scenario_details(result, scenario):
    """Render a practical inspection workspace for one evacuation scenario."""
    building = result.building
    geometry_mode = result.source_mode == "geometry_derived"
    alternative_exits = max(0, len(building.exits) - 1)
    route_evidence = scenario.to_dict()["evacuation_route"]
    route_reliability = route_evidence["route_reliability"]
    verified_edges = route_evidence["verified_edge_count"]
    inferred_edges = route_evidence["inferred_edge_count"]
    edge_sources = getattr(scenario.evacuation_route, "edge_sources", []) or []
    scenario_id = html.escape(str(scenario.scenario_id))
    scenario_name = html.escape(str(scenario.name))
    origin_name = html.escape(str(scenario.origin_space_name))
    destination = html.escape(str(scenario.evacuation_route.destination))
    route_nodes = " &rarr; ".join(html.escape(str(node)) for node in scenario.evacuation_route.path)
    route_reliability_text = html.escape(str(route_reliability))
    edge_source_text = ", ".join(html.escape(str(source)) for source in edge_sources)
    st.markdown(
        f"""
        <div class="scenario-detail-card">
            <h4>Selected Scenario Inspection Workspace</h4>
            <strong>Scenario ID:</strong> {scenario_id}<br>
            <strong>Name:</strong> {scenario_name}<br>
            <strong>Origin:</strong> {origin_name}<br>
            <strong>Destination:</strong> {destination}<br>
            <strong>Route nodes:</strong> {route_nodes}<br>
            <strong>Screening priority:</strong> {scenario.risk_level.value.upper()} |
            <strong>Implemented checks passed:</strong> {scenario.compliance_score * 100:.0f}% |
            <strong>Evidence confidence:</strong> {scenario.confidence_score * 100:.0f}%<br>
            <strong>Route reliability:</strong> {route_reliability_text}<br>
            <strong>Edge evidence:</strong> verified={verified_edges}, inferred={inferred_edges}<br>
            <strong>Edge sources:</strong> {edge_source_text or 'No route-edge source metadata'}<br>
            <strong>Analysis basis:</strong> {'Geometry-derived structural screening' if geometry_mode else 'Semantic IFC space and door data'}
        </div>
        """,
        unsafe_allow_html=True,
    )
    metrics = st.columns(5)
    metrics[0].metric("Travel Distance", f"{scenario.evacuation_route.distance:.1f} m")
    metrics[1].metric("Estimated Time", f"{scenario.evacuation_route.estimated_time:.1f} s")
    metrics[2].metric("Alternative Exits", alternative_exits)
    metrics[3].metric("Checks Passed", f"{scenario.compliance_score * 100:.0f}%")
    metrics[4].metric("Evidence Confidence", f"{scenario.confidence_score * 100:.0f}%")

    detail_route, detail_actions, detail_evidence = st.tabs([
        "Route Diagram", "Operational Actions", "Evidence & Export"
    ])
    with detail_route:
        st.plotly_chart(create_selected_route_figure(result, scenario), key=f"selected_route_{scenario.scenario_id}")
        st.caption("Red = origin, orange = selected route, green = destination egress.")
    with detail_actions:
        st.markdown("#### Practical Readiness Checklist")
        checks = [
            ("Alternative escape direction available", alternative_exits > 0),
            ("Route within default 45 m screening threshold", scenario.evacuation_route.distance <= 45),
            ("No conflicts detected by active prototype checks", not scenario.violated_regulations),
            ("Evidence confidence above 70%", scenario.confidence_score >= 0.7),
            ("Accessibility/refuge arrangements confirmed", False),
            ("Exit signage, emergency lighting and door operation confirmed", False),
        ]
        for label, passed in checks:
            (st.success if passed else st.warning)(f"{'PASS' if passed else 'REVIEW'}: {label}")
        st.markdown("#### Recommendations")
        for recommendation in scenario.recommendations or ["Confirm assumptions with a qualified fire-safety professional."]:
            st.info(recommendation)
    with detail_evidence:
        st.write(scenario.explanation)
        st.markdown("#### Anti-Black-Box Decision Trace")
        st.caption("The scenario score is deterministic and traceable; it is not an opaque AI prediction.")
        for item in scenario.decision_trace:
            with st.expander(item["step"], expanded=False):
                st.json(item)
        if scenario.data_quality_notes:
            st.markdown("#### Data Quality Notes")
            for note in scenario.data_quality_notes:
                st.warning(note)
        st.json(scenario.to_dict())
        st.download_button(
            "Download selected scenario evidence",
            json.dumps(scenario.to_dict(), indent=2),
            f"{scenario.scenario_id}_evidence.json",
            "application/json",
            key=f"download_scenario_{scenario.scenario_id}",
        )


def build_complete_export_payload(result):
    """Create a complete, traceable export payload for reviewer handoff."""
    building = result.building
    return {
        "export_version": "submission-evidence-v2",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "academic_use_notice": ACADEMIC_USE_NOTICE,
        "score_semantics": screening_index_semantics(),
        "assumption_registry": standard_assumption_registry(),
        "source_file": {
            "name": result.source_file_name,
            "sha256": result.source_file_sha256,
            "ifc_schema": result.ifc_schema,
            "source_mode": result.source_mode,
        },
        "building": {
            "id": building.id if building else None,
            "name": building.name if building else "Unknown",
            "spaces": len(building.spaces) if building else 0,
            "doors": len(building.doors) if building else 0,
            "stairs": len(building.stairs) if building else 0,
            "exits": len(building.exits) if building else 0,
            "geometry_source_types": building.geometry_source_types if building else [],
            "geometry_elements_available": building.geometry_elements_available if building else 0,
            "geometry_elements_used": building.geometry_elements_used if building else 0,
            "extraction_mode": building.extraction_mode if building else "unknown",
        },
        "ifc_readiness": result.readiness,
        "graph_stats": result.graph_stats,
        "regulations": {
            "source": result.regulation_source,
            "document": result.regulation_document,
            "clause_count": result.regulation_clause_count,
            "rule_count": result.regulation_rule_count,
            "application": result.regulation_application,
            "rag_enabled": result.rag_enabled,
            "retrieval_mode": result.retrieval_mode,
        },
        "manual_corrections": st.session_state.get("manual_corrections"),
        "research_review_records": [
            review
            for review in st.session_state.get("expert_reviews", {}).values()
            if isinstance(review, dict)
        ],
        "preliminary_domain_review_records": st.session_state.get("domain_review_records", []),
        "manual_accessibility_audit_records": st.session_state.get("accessibility_audit_records", []),
        "space_label_review_validation": st.session_state.get("space_label_review_validation"),
        "scenarios": [scenario.to_dict() for scenario in result.scenarios],
        "errors": result.errors,
        "processing_time_seconds": result.processing_time,
    }

# ==============================================================================
# HEADER
# ==============================================================================
def render_header():
    """Render professional application header."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(
            f'<p class="main-title">🏗️ {PROJECT_TITLE}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="sub-title">{PROJECT_SUBTITLE}</p>',
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown(f"""
        <div class="hero-author">
            <strong>Janak Raj Joshi</strong><br>
            <a href="mailto:janakjocee@gmail.com">janakjocee@gmail.com</a><br>
            <a href="https://github.com/janakjocee/bim_evacuation_system_final" target="_blank">GitHub Repository</a>
        </div>
        """, unsafe_allow_html=True)
    
    # Disclaimer
    st.info("""
    🎓 **Research Prototype** | This system uses deterministic graph/rule calculations, spaCy regulation parsing, and optional FAISS/SentenceTransformers retrieval.
    Outputs are **screening scenarios for expert review**, not legal compliance approval and not a replacement for professional fire engineering judgement.
    """)

# ==============================================================================
# SIDEBAR
# ==============================================================================
def render_sidebar():
    """Render professional sidebar with file uploads and controls."""
    with st.sidebar:
        st.markdown("## 📁 Project Data")
        st.markdown("---")
        
        # IFC Upload Section
        st.markdown("### 1. BIM Model (IFC/IFCZIP)")
        st.markdown("<p style='font-size:0.8rem;color:var(--app-muted);'>Upload Building Information Model</p>", unsafe_allow_html=True)
        
        ifc_file = st.file_uploader(
            "Select IFC or IFCZIP file",
            type=['ifc', 'ifczip'],
            help=(
                "Industry Foundation Classes model. IFCZIP must contain exactly one .ifc file; "
                "compressed uploads help large text-based IFC models stay within the cloud limit."
            ),
            label_visibility="collapsed"
        )
        
        if ifc_file:
            st.success(f"✓ {ifc_file.name}")
        
        st.markdown("---")
        
        # Regulation Upload Section
        st.markdown("### 2. Safety Regulations")
        st.markdown("<p style='font-size:0.8rem;color:var(--app-muted);'>Upload building safety codes</p>", unsafe_allow_html=True)
        
        regulation_file = st.file_uploader(
            "Select regulation document",
            type=['txt', 'md', 'pdf', 'docx'],
            help="Building safety regulations (TXT, MD, PDF or DOCX, e.g., Approved Document B)",
            label_visibility="collapsed"
        )
        
        if regulation_file:
            st.success(f"✓ {regulation_file.name}")

        with st.expander("Regulation source provenance"):
            st.caption(
                "Optional user-declared citation fields. They improve research traceability but "
                "do not establish legal applicability or professional approval."
            )
            regulation_source_url = st.text_input(
                "Official source URL",
                placeholder="https://www.gov.uk/government/publications/fire-safety-approved-document-b",
            )
            regulation_jurisdiction = st.text_input(
                "Jurisdiction / applicability",
                placeholder="England; building type and effective date to be verified",
            )
            regulation_edition = st.text_input(
                "Edition / amendment status",
                placeholder="2019 edition incorporating applicable amendments",
            )
        
        st.markdown("---")
        
        # Settings Section
        st.markdown("### 3. Analysis Settings")
        
        max_scenarios = st.slider(
            "Max Scenarios",
            min_value=1,
            max_value=20,
            value=10,
            help="Maximum evacuation scenarios to generate"
        )
        
        enable_rag = st.toggle(
            "Enable Regulation Evidence Retrieval",
            value=True,
            help="Attach ranked source clauses to supported checks; this does not interpret law or generate compliance decisions."
        )

        st.markdown("---")
        
        # Process Button
        st.markdown("### 4. Run Analysis")
        
        process_disabled = ifc_file is None
        process_button = st.button(
            "🚀 Generate Screening Scenarios",
            type="primary",
            width='stretch',
            disabled=process_disabled
        )
        
        if process_disabled:
            st.warning("⚠️ Upload an IFC file to begin")

        with st.expander("IFC version support"):
            st.write(f"Documented schema targets: **{SUPPORTED_SCHEMA_LABEL}**.")
            st.caption(
                "Not every file in these schema families is suitable. Results depend on "
                "available spaces/doors or usable element geometry."
            )
            st.caption(
                "Both the uploaded file and the IFC model inside an IFCZIP are limited to 200 MB. "
                "Larger models require local testing or a deployment with measured memory capacity."
            )
        
        st.markdown("---")
        
        # System Status
        st.markdown("### System Status")
        
        status_items = [
            ("IFC Parser", "✅ Ready" if ifc_file else "⏳ Waiting"),
            ("NLP Engine", "✅ Ready"),
            ("Evidence Retrieval", "✅ TF-IDF ready" if enable_rag else "⏹️ Disabled"),
            ("Graph Builder", "✅ Ready"),
        ]
        
        for label, status in status_items:
            st.markdown(f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;'><span>{label}</span><span>{status}</span></div>", unsafe_allow_html=True)
        
        regulation_metadata = {
            "source_url": regulation_source_url.strip(),
            "jurisdiction": regulation_jurisdiction.strip(),
            "edition": regulation_edition.strip(),
            "metadata_scope": "user_declared_not_legally_validated",
        }
        return ifc_file, regulation_file, regulation_metadata, max_scenarios, enable_rag, process_button

# ==============================================================================
# FILE PROCESSING
# ==============================================================================
def save_uploaded_file(uploaded_file, directory: str) -> str:
    """Save an upload under a collision-safe local name and return its path."""
    save_dir = Path(directory)
    save_dir.mkdir(parents=True, exist_ok=True)
    payload = uploaded_file.getbuffer()
    digest = hashlib.sha256(payload).hexdigest()[:12]
    safe_name = safe_uploaded_filename(uploaded_file.name)
    file_path = save_dir / f"{digest}_{safe_name}"
    with open(file_path, "wb") as f:
        f.write(payload)
    return str(file_path)

def process_files(ifc_file, regulation_file, regulation_metadata, max_scenarios, enable_rag):
    """Process uploaded files through the pipeline."""
    progress_bar = st.progress(0, text="Initializing pipeline...")
    
    try:
        st.session_state.rag_enabled = enable_rag
        regulation_document = {}
        temp_root = Path("./data/temp")
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="analysis_", dir=temp_root) as upload_dir:
            progress_bar.progress(10, text="Loading IFC model...")
            ifc_path = save_uploaded_file(ifc_file, upload_dir)

            regulation_text = None
            if regulation_file:
                progress_bar.progress(20, text="Loading regulations...")
                regulation_path = save_uploaded_file(regulation_file, upload_dir)
                regulation_text = extract_regulation_text(regulation_path, regulation_file.name)
                st.session_state['regulation_text'] = regulation_text
                regulation_document = {
                    "name": safe_uploaded_filename(regulation_file.name, "regulation_document"),
                    "sha256": hashlib.sha256(regulation_file.getbuffer()).hexdigest(),
                    "file_type": Path(regulation_file.name).suffix.lower().lstrip("."),
                    **(regulation_metadata or {}),
                }

            progress_bar.progress(30, text="Parsing BIM model...")
            pipeline = EvacuationPipeline()

            progress_bar.progress(50, text="Extracting features...")
            progress_bar.progress(70, text="Building spatial graph...")
            progress_bar.progress(85, text="Generating scenarios...")

            result = pipeline.run(
                ifc_path,
                regulation_text,
                max_scenarios=max_scenarios,
                enable_rag=enable_rag,
            )
        result.source_file_name = safe_uploaded_filename(ifc_file.name, "uploaded.ifc")
        result.regulation_document = regulation_document
        
        progress_bar.progress(100, text="Complete!")
        time.sleep(0.5)
        progress_bar.empty()
        
        # Store result
        st.session_state.pipeline_result = result
        st.session_state.baseline_pipeline_result = copy.deepcopy(result)
        st.session_state.processing_done = True
        st.session_state.selected_scenario_id = result.scenarios[0].scenario_id if result.scenarios else None
        st.session_state.manual_corrections = None
        
        if result.source_mode == "geometry_derived":
            st.success(
                f"✅ Geometry screening complete! Generated **{len(result.scenarios)}** exploratory route scenarios."
            )
            st.info(
                "The uploaded IFC was analyzed directly in geometry-derived mode. "
                "Connectivity and boundary egress points were inferred only from the "
                "file's actual elements, geometry, and properties."
            )
            st.warning(
                f"Operational processing readiness: "
                f"{result.readiness.get('processing_readiness_score', 0)}/100. "
                f"Engineering evidence quality: "
                f"{result.readiness.get('engineering_evidence_score', 0)}/100. "
                "The second score controls whether outputs may be treated as verified evacuation evidence."
            )
        elif result.source_mode == "semantic_spaces_inferred_topology":
            st.success(
                f"✅ Analysis Complete! Generated **{len(result.scenarios)}** evacuation scenarios."
            )
            st.info(
                "The uploaded IFC supplied real IfcSpace room geometry, but did not provide "
                "usable door/exit route semantics. The route graph was inferred from those "
                "actual room bounds and should be reviewed by the fire-safety expert."
            )
        elif result.success:
            st.success(f"✅ Analysis Complete! Generated **{len(result.scenarios)}** evacuation scenarios.")
        else:
            st.error("❌ Analysis could not generate evacuation scenarios.")
            if result.errors:
                for error in result.errors:
                    st.error(error)
            if result.readiness:
                st.info(
                    f"IFC readiness: **{result.readiness['readiness_label']}** "
                    f"({result.readiness['model_readiness_score']}/100)"
                )
        
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ Processing Error: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

# ==============================================================================
# TAB 1: PROJECT OVERVIEW DASHBOARD
# ==============================================================================
def render_dashboard(result):
    """Render Project Overview Dashboard with KPIs and visualizations."""
    st.markdown('<div class="section-header">📊 Project Overview Dashboard</div>', unsafe_allow_html=True)

    st.info(
        f"DATA PROVENANCE: analyzed uploaded file **{result.source_file_name or 'unknown'}** | "
        f"schema **{result.ifc_schema}** | mode **{result.source_mode}** | "
        f"SHA-256 `{result.source_file_sha256[:16]}...`"
    )

    if result.source_mode == "geometry_derived":
        st.warning(
            "GEOMETRY-DERIVED STRUCTURAL SCREENING: elements and connectivity come from "
            "the uploaded IFC only. These are not verified rooms, doors, or evacuation routes."
        )
    elif result.source_mode == "semantic_spaces_inferred_topology":
        st.warning(
            "IFCSPACE-INFERRED ROUTE SCREENING: room geometry comes from uploaded IfcSpace "
            "entities, while route links and boundary exits are inferred because semantic "
            "IfcDoor/exit connectivity was not available."
        )
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available. Run analysis to generate data.")
        return
    
    # KPI Cards Row
    st.markdown("### Key Performance Indicators")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    scenarios = result.scenarios
    risk_counts = {'low': 0, 'medium': 0, 'high': 0}
    for s in scenarios:
        risk_counts[s.risk_level.value] = risk_counts.get(s.risk_level.value, 0) + 1
    
    total_violations = sum(len(s.violated_regulations) for s in scenarios)
    avg_compliance = sum(s.compliance_score for s in scenarios) / len(scenarios) if scenarios else 0
    
    with col1:
        render_metric_card(
            "TOTAL SCENARIOS",
            str(len(scenarios)),
            "Evacuation routes analyzed",
            "#1a1a2e"
        )
    
    with col2:
        render_metric_card(
            "HIGH PRIORITY",
            str(risk_counts.get('high', 0)),
            "Require immediate attention",
            "#dc3545"
        )
    
    with col3:
        render_metric_card(
            "MEDIUM PRIORITY",
            str(risk_counts.get('medium', 0)),
            "Recommend improvements",
            "#ffc107"
        )
    
    with col4:
        render_metric_card(
            "LOW PRIORITY",
            str(risk_counts.get('low', 0)),
            "Fewer issues in implemented checks",
            "#28a745"
        )
    
    with col5:
        compliance_pct = avg_compliance * 100
        color = "#28a745" if compliance_pct >= 80 else "#ffc107" if compliance_pct >= 50 else "#dc3545"
        render_metric_card(
            "AVG CHECKS PASSED",
            f"{compliance_pct:.0f}%",
            f"{total_violations} prototype check findings",
            color
        )
    
    st.markdown("---")
    
    # Charts Row
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### Screening Priority Distribution")
        fig_risk = create_risk_pie_chart(scenarios)
        st.plotly_chart(fig_risk, key="dashboard_risk_pie")
    
    with col_right:
        st.markdown("### Scenario Performance")
        fig_perf = create_scenario_bar_chart(scenarios)
        st.plotly_chart(fig_perf, key="dashboard_perf_bar")
    
    # Summary Table
    st.markdown("---")
    st.markdown("### Scenario Summary")
    
    summary_data = []
    for i, s in enumerate(scenarios):
        summary_data.append({
            'Rank': i + 1,
            'Scenario': s.name,
            'Screening Priority': s.risk_level.value.upper(),
            'Distance (m)': round(s.evacuation_route.distance, 1),
            'Time (s)': round(s.evacuation_route.estimated_time, 1),
            'Checks Passed': f"{s.compliance_score * 100:.0f}%",
            'Evidence Confidence': f"{s.confidence_score * 100:.0f}%",
            'Check Findings': len(s.violated_regulations),
        })
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, height=300, width='stretch')

# ==============================================================================
# TAB 2: BIM MODEL INSIGHTS
# ==============================================================================
def render_bim_insights(result):
    """Render BIM Model Insights with graph visualization."""
    st.markdown('<div class="section-header">🏢 BIM Model Insights</div>', unsafe_allow_html=True)
    
    if not result or not result.building:
        st.info("📋 No building data available. Upload and process an IFC file.")
        return
    
    building = result.building
    geometry_mode = result.source_mode == "geometry_derived"

    if result.readiness:
        readiness = result.readiness
        st.markdown("### Uploaded IFC Readiness")
        st.write(f"**Detected schema:** {readiness['schema']}")
        st.caption(readiness["target_compatibility"])
        readiness_columns = st.columns(2)
        readiness_columns[0].metric(
            "Processing Readiness",
            f"{readiness.get('processing_readiness_score', readiness['model_readiness_score'])}/100",
            help="Whether the application can parse, graph and screen the available IFC-derived data.",
        )
        readiness_columns[1].metric(
            "Engineering Evidence Quality",
            f"{readiness.get('engineering_evidence_score', readiness['model_readiness_score'])}/100",
            help="Quality of semantic rooms, doors, exits, dimensions and verified route connectivity.",
        )
        st.write(f"**{readiness['readiness_label']}**")
        st.caption(f"Permitted analysis scope: `{readiness.get('analysis_scope', 'screening')}`")
        for issue in readiness["critical_issues"]:
            if geometry_mode:
                st.warning(f"Geometry-derived analysis: {issue}")
            else:
                st.error(issue)
        for warning in readiness["warnings"]:
            st.warning(warning)
    
    # Building Overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Building Name", building.name)
    with col2:
        st.metric("IFC Elements" if geometry_mode else "Total Spaces", len(building.spaces))
    with col3:
        st.metric("Geometry Connections" if geometry_mode else "Total Doors", len(building.doors))
    with col4:
        st.metric("Inferred Egress Points" if geometry_mode else "Total Exits", len(building.exits))

    if geometry_mode:
        st.caption(
            f"Screened {building.geometry_elements_used} of "
            f"{building.geometry_elements_available} candidate file elements from "
            f"{', '.join(building.geometry_source_types) or 'available geometry'}. "
            "A bounded sample keeps large structural IFCs responsive."
        )
    
    st.markdown("---")
    
    # Tabs for different views
    bim_tab1, bim_tab2, bim_tab3, bim_tab4, bim_tab5, bim_tab6 = st.tabs([
        "🔍 Extracted IFC Elements" if geometry_mode else "🔍 Extracted Spaces",
        "🚪 Connections & Egress" if geometry_mode else "🚪 Doors & Exits",
        "🕸️ Connectivity Graph",
        "🗺️ Floor Plan Diagram",
        "🏙️ 3D Model & Egress",
        "🧾 Diagnostics Export",
    ])
    
    with bim_tab1:
        st.markdown("### Extracted IFC Elements" if geometry_mode else "### Extracted Spaces from IFC")
        
        if building.spaces:
            space_data = []
            for space_id, space in building.spaces.items():
                space_data.append({
                    'ID': space_id,
                    'Name': space.name,
                    'Type': space.space_type,
                    'Area (m²)': round(space.area, 1),
                    'Level': space.level or 'N/A',
                    'Connected Doors': len(space.connected_doors)
                })
            
            df_spaces = pd.DataFrame(space_data)
            st.dataframe(df_spaces, height=400)
            
            # Space type distribution
            st.markdown("### Space Type Distribution")
            type_counts = df_spaces['Type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Count']
            fig = px.bar(type_counts, x='Type', y='Count', color='Type', title="Space Types")
            st.plotly_chart(fig, key="bim_space_types")
        else:
            st.warning("No spaces extracted from IFC model")
    
    with bim_tab2:
        st.markdown("### Geometry Connections and Egress Points" if geometry_mode else "### Doors and Exits")
        
        col_doors, col_exits = st.columns(2)
        
        with col_doors:
            st.markdown("**Geometry Connections**" if geometry_mode else "**All Doors**")
            door_data = []
            for door_id, door in building.doors.items():
                door_data.append({
                    'ID': door_id,
                    'Name': door.name,
                    'Width (m)': door.width,
                    'Is Exit': '✓' if door.is_exit else '✗',
                    'External': '✓' if door.is_external else '✗'
                })
            
            if door_data:
                st.dataframe(pd.DataFrame(door_data), height=300)
            else:
                st.info("No doors found")
        
        with col_exits:
            st.markdown("**Inferred Egress Analysis**" if geometry_mode else "**Exit Analysis**")
            if building.exits:
                exit_data = []
                for exit_id, exit_door in building.exits.items():
                    capacity = exit_door.width * 90  # persons/min
                    exit_data.append({
                        'ID': exit_id,
                        'Name': exit_door.name,
                        'Width (m)': exit_door.width,
                        'Capacity (p/min)': round(capacity, 0)
                    })
                st.dataframe(pd.DataFrame(exit_data), height=300)
            else:
                st.info("No exits identified")
    
    with bim_tab3:
        st.markdown("### Building Connectivity Graph")
        st.markdown("*Interactive visualization of building topology*")
        
        if st.session_state.graph_viz_enabled:
            fig_graph = create_network_graph_viz(building)
            st.plotly_chart(fig_graph, key="bim_graph_viz")
        else:
            st.info("Graph visualization disabled in settings")
        
        # Graph statistics
        if result.features:
            st.markdown("### Graph Statistics")
            col_g1, col_g2, col_g3 = st.columns(3)
            with col_g1:
                st.metric(
                    "Screened Footprint Sum" if geometry_mode else "Total Area",
                    f"{result.features.total_area:,.0f} m²",
                )
            with col_g2:
                if geometry_mode:
                    st.metric("Occupancy", "Not inferred")
                else:
                    st.metric("Estimated Occupancy", f"{result.features.total_occupancy:,}")
            with col_g3:
                st.metric(
                    "Assumed Egress Capacity" if geometry_mode else "Exit Capacity",
                    f"{result.features.total_exit_capacity:,.0f} p/min",
                )

    with bim_tab4:
        st.markdown("### Interactive Top-Down IFC Diagram")
        st.info(
            "Colored footprints come from uploaded IFC bounding geometry. Yellow lines "
            "show connectivity and green diamonds show exits or inferred egress points."
        )
        if any(space.bounding_box for space in building.spaces.values()):
            st.plotly_chart(create_ifc_plan_figure(building), key="bim_floor_plan")
            st.caption("Hover for IFC element details; drag and zoom to inspect the diagram.")
        else:
            st.warning("No renderable uploaded IFC geometry is available for a floor-plan diagram.")

    with bim_tab5:
        st.markdown("### Interactive 3D Model and Egress View")
        if geometry_mode:
            st.warning(
                "This view uses actual uploaded IFC element bounding boxes. Yellow lines "
                "and green egress markers are inferred screening aids and require expert review."
            )
        else:
            st.info(
                "This view uses available uploaded IFC space geometry, connections and exits."
            )
        if any(space.bounding_box for space in building.spaces.values()):
            st.plotly_chart(create_ifc_3d_figure(building), key="bim_3d_model")
            st.caption(
                "Drag to rotate, scroll to zoom, and hover over a volume or exit for details."
            )
        else:
            st.warning(
                "The uploaded IFC contains no renderable space/element geometry for the 3D view. "
                "The connectivity graph remains available."
            )

    with bim_tab6:
        st.markdown("### IFC Diagnostic Report")
        graph_stats = getattr(result, "graph_stats", {}) or {}
        diagnostic = {
            "source_file_name": result.source_file_name,
            "source_file_sha256": result.source_file_sha256,
            "ifc_schema": result.ifc_schema,
            "source_mode": result.source_mode,
            "readiness": result.readiness,
            "graph_stats": graph_stats,
            "entity_counts": {
                "spaces": len(building.spaces),
                "doors": len(building.doors),
                "stairs": len(building.stairs),
                "exits": len(building.exits),
                "geometry_elements_available": building.geometry_elements_available,
                "geometry_elements_used": building.geometry_elements_used,
                "geometry_source_types": building.geometry_source_types,
            },
            "data_quality_flags": {
                "building": building.data_quality_flags,
                "spaces": {
                    space_id: {
                        "flags": space.data_quality_flags,
                        "assumptions": space.assumptions,
                        "area_confidence": space.area_confidence,
                    }
                    for space_id, space in building.spaces.items()
                    if space.data_quality_flags or space.assumptions or space.area_confidence < 1
                },
                "doors": {
                    door_id: {
                        "flags": door.data_quality_flags,
                        "assumptions": door.assumptions,
                        "width_confidence": door.width_confidence,
                        "connection_source": door.connection_source,
                        "connected_spaces": door.connected_spaces,
                        "is_exit": door.is_exit,
                    }
                    for door_id, door in building.doors.items()
                    if door.data_quality_flags or door.assumptions or door.connection_source != "IfcRelSpaceBoundary"
                },
            },
            "regulation_application": getattr(result, "regulation_application", {}),
        }
        cols = st.columns(4)
        cols[0].metric("Graph Confidence", f"{graph_stats.get('graph_confidence_score', 0):.2f}")
        cols[1].metric("Verified Edges", graph_stats.get("verified_edges_count", 0))
        cols[2].metric("Inferred Edges", graph_stats.get("inferred_edges_count", 0))
        cols[3].metric("Spaces Without Route", len(graph_stats.get("spaces_without_exit_route", [])))
        if graph_stats.get("disconnected_spaces"):
            st.warning(f"Disconnected spaces: {', '.join(graph_stats['disconnected_spaces'][:10])}")
        if graph_stats.get("spaces_without_exit_route"):
            st.warning(f"Spaces without exit route: {', '.join(graph_stats['spaces_without_exit_route'][:10])}")
        st.json(diagnostic)
        st.download_button(
            "Download IFC diagnostic report",
            json.dumps(diagnostic, indent=2),
            file_name=f"ifc_diagnostic_{result.source_file_name or 'analysis'}.json",
            mime="application/json",
            width='stretch',
        )

        st.markdown("---")
        st.markdown("### Manual IFC Review & Correction")
        st.caption(
            "Use this when IFC door widths, exits or connectivity are missing/incorrect. "
            "Corrections are marked as manual review and the graph/scenarios are regenerated."
        )
        correction_rows = []
        for door_id, door in building.doors.items():
            correction_rows.append({
                "id": door_id,
                "name": door.name,
                "width": float(door.width),
                "is_exit": bool(door.is_exit),
                "connected_spaces": ", ".join(door.connected_spaces),
                "connection_source": door.connection_source,
                "width_confidence": door.width_confidence,
                "flags": ", ".join(door.data_quality_flags),
            })
        if correction_rows:
            edited = st.data_editor(
                pd.DataFrame(correction_rows),
                disabled=["id", "name", "connection_source", "width_confidence", "flags"],
                width='stretch',
                height=300,
                key=f"manual_corrections_{result.source_file_sha256}",
            )
            col_apply, col_reset, col_export = st.columns(3)
            with col_apply:
                if st.button("Apply manual corrections and rerun", type="primary", width='stretch'):
                    corrections = {"doors": edited.to_dict(orient="records")}
                    st.session_state.manual_corrections = corrections
                    correction_base = copy.deepcopy(
                        st.session_state.get("baseline_pipeline_result") or result
                    )
                    st.session_state.pipeline_result = apply_manual_corrections(
                        correction_base,
                        corrections,
                        max_scenarios=max(10, len(result.scenarios)),
                    )
                    st.success("Manual corrections applied. Graph and scenarios regenerated.")
                    st.rerun()
            with col_reset:
                if st.button("Reset manual corrections", width='stretch'):
                    st.session_state.manual_corrections = None
                    baseline_result = st.session_state.get("baseline_pipeline_result")
                    st.session_state.pipeline_result = copy.deepcopy(baseline_result) if baseline_result else result
                    st.success("Manual corrections cleared for this session.")
                    st.rerun()
            with col_export:
                corrections_payload = {
                    "source_file_name": result.source_file_name,
                    "source_file_sha256": result.source_file_sha256,
                    "corrections": edited.to_dict(orient="records"),
                }
                st.download_button(
                    "Download manual corrections JSON",
                    json.dumps(corrections_payload, indent=2),
                    file_name=f"manual_corrections_{result.source_file_name or 'ifc'}.json",
                    mime="application/json",
                    width='stretch',
                )
        else:
            st.info("No doors/connections are available for manual correction.")

        st.markdown("---")
        st.markdown("### Fire/Worst-Case Dataset Bridge")
        st.caption(
            "Exports the uploaded IFC-derived graph into the JSON schema used by the "
            "Worst Case Testing page. Inferred data remains labelled for review."
        )
        fire_dataset = building_to_worst_case_dataset(
            building,
            graph_builder=None,
            features=result.features,
            source_file_name=result.source_file_name,
            ifc_schema=result.ifc_schema,
        )
        bridge_cols = st.columns(3)
        bridge_cols[0].metric("Dataset Spaces", len(fire_dataset.get("spaces", [])))
        bridge_cols[1].metric("Dataset Connections", len(fire_dataset.get("connections", [])))
        bridge_cols[2].metric("Hazard Scenarios", len(fire_dataset.get("hazard_scenarios", [])))
        st.download_button(
            "Export IFC-derived graph as fire scenario dataset",
            json.dumps(fire_dataset, indent=2),
            file_name=f"ifc_fire_dataset_{result.source_file_name or 'analysis'}.json",
            mime="application/json",
            width='stretch',
        )

# ==============================================================================
# TAB 3: REGULATION INTELLIGENCE
# ==============================================================================
def render_regulation_intelligence(result):
    """Render Regulation Intelligence panel."""
    st.markdown('<div class="section-header">📜 Regulation Intelligence</div>', unsafe_allow_html=True)
    
    # Show loaded regulations
    regulation_text = st.session_state.get('regulation_text')
    
    if regulation_text:
        st.markdown("### Uploaded Regulations")
        regulation_document = getattr(result, "regulation_document", {}) or {}
        if regulation_document:
            st.markdown("#### Uploaded Regulation Evidence")
            evidence_columns = st.columns(3)
            evidence_columns[0].write(f"**File:** {regulation_document.get('name', 'Unknown')}")
            evidence_columns[1].write(
                f"**Type:** {str(regulation_document.get('file_type', 'unknown')).upper()}"
            )
            evidence_columns[2].write(
                f"**Jurisdiction:** {regulation_document.get('jurisdiction') or 'Not declared'}"
            )
            st.code(regulation_document.get("sha256", "Hash unavailable"), language=None)
            if regulation_document.get("source_url"):
                st.write(f"**Declared source:** {regulation_document['source_url']}")
            if regulation_document.get("edition"):
                st.write(f"**Declared edition:** {regulation_document['edition']}")
            st.caption(
                "Source URL, jurisdiction and edition are user-declared metadata. The prototype "
                "does not determine legal applicability, commencement dates or transitional provisions."
            )
        with st.expander("View Raw Regulation Text", expanded=False):
            st.text_area("Regulation Content", regulation_text[:5000], height=300, disabled=True)
    else:
        st.info("📋 No regulations uploaded. Using default constraints from configuration.")
    
    st.markdown("---")
    
    # Active Constraints
    st.markdown("### Active Screening Constraints")
    st.caption(
        "This table shows which thresholds came from uploaded regulation parsing "
        "and which remain prototype defaults. All thresholds require professional verification."
    )
    application = getattr(result, "regulation_application", {}) if result else {}
    if application:
        cols = st.columns(4)
        cols[0].metric("Extracted Clauses", getattr(result, "regulation_clause_count", 0))
        cols[1].metric("Numeric Rules", getattr(result, "regulation_rule_count", 0))
        cols[2].metric("Applied Uploaded Thresholds", application.get("active_uploaded_threshold_count", 0))
        cols[3].metric("Unsupported Rules", application.get("unsupported_rule_count", 0))
        st.caption(
            f"Supported uploaded candidates: {application.get('supported_uploaded_rule_candidate_count', application.get('uploaded_rule_count', 0))}. "
            "Conditional candidates use a conservative screening value and remain subject to expert applicability review."
        )

        active_rows = application.get("active_thresholds", [])
        if active_rows:
            st.dataframe(pd.DataFrame(active_rows), height=260, width='stretch')

        unsupported_rows = application.get("unsupported_rules", [])
        if unsupported_rows:
            with st.expander("Extracted but not currently enforceable", expanded=False):
                st.dataframe(pd.DataFrame(unsupported_rows), height=220, width='stretch')
    else:
        st.info("No pipeline result is available yet.")
    
    constraints_data = [
        {'Parameter': 'Maximum Travel Distance', 'Value': '45.0 m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
        {'Parameter': 'Minimum Door Width', 'Value': '0.75 m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
        {'Parameter': 'Minimum Exit Width', 'Value': '1.05 m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
        {'Parameter': 'Minimum Corridor Width', 'Value': '1.20 m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
        {'Parameter': 'Minimum Stair Width', 'Value': '1.00 m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
        {'Parameter': 'Max Riser Height', 'Value': '0.19 m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
        {'Parameter': 'Min Tread Length', 'Value': '0.25 m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
        {'Parameter': 'Exit Capacity', 'Value': '90 p/min/m', 'Source': 'Prototype configuration', 'Status': 'Default only'},
    ]
    
    df_constraints = pd.DataFrame(constraints_data)
    with st.expander("Built-in default reference values", expanded=False):
        st.dataframe(df_constraints, height=250, width='stretch')
    
    # Search regulations
    st.markdown("---")
    st.markdown("### 🔍 Regulation Search")
    
    search_query = st.text_input("Search regulations by keyword", placeholder="e.g., door width, travel distance")
    
    if search_query:
        st.info(f"Searching for: **{search_query}**")
        # Show matching constraints
        matches = [c for c in constraints_data if search_query.lower() in c['Parameter'].lower()]
        if matches:
            st.success(f"Found {len(matches)} matching regulation(s)")
            st.dataframe(pd.DataFrame(matches))
        else:
            st.warning("No matching regulations found")
    
    # Evidence retrieval status
    st.markdown("---")
    st.markdown("### Evidence Retrieval Status")
    rag_status = (
        "Active for uploaded regulation text"
        if st.session_state.get("rag_enabled", True) and regulation_text
        else "Not active for this analysis"
    )
    
    rag_col1, rag_col2 = st.columns(2)
    with rag_col1:
        st.markdown(f"""
        <div class="success-box">
            <strong>Default Retrieval:</strong> evaluated TF-IDF lexical ranking<br>
            <strong>Optional Vector Mode:</strong> SentenceTransformers + FAISS when enabled in config<br>
            <strong>Reason:</strong> stable deployment first; native vector libraries are opt-in<br>
            <strong>Status:</strong> {rag_status}
        </div>
        """, unsafe_allow_html=True)
    
    with rag_col2:
        st.markdown("""
        <div class="info-box">
            <strong>Grounding Pipeline:</strong><br>
            1. Document chunking (size=512, overlap=50)<br>
            2. TF-IDF lexical retrieval by compliance-check query<br>
            3. Optional vector retrieval if enabled<br>
            4. Evidence snippets attached to each check<br>
            5. Expert review and source verification
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# TAB 4: EVACUATION SCENARIOS
# ==============================================================================
def toggle_scenario_details(scenario_id: str) -> None:
    """Open one scenario workspace, or close it when already selected."""
    current_id = st.session_state.get("selected_scenario_id")
    st.session_state.selected_scenario_id = None if current_id == scenario_id else scenario_id


def render_evacuation_scenarios(result):
    """Render Evacuation Scenarios panel."""
    st.markdown('<div class="section-header">🚨 Evacuation Scenarios</div>', unsafe_allow_html=True)
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available. Run analysis to generate evacuation scenarios.")
        return
    
    scenarios = result.scenarios
    
    # Filter controls
    st.markdown("### Filter & Sort")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        risk_filter = st.multiselect(
            "Screening Priority",
            options=['low', 'medium', 'high'],
            default=['low', 'medium', 'high'],
            format_func=lambda x: x.upper()
        )
    
    with col_f2:
        sort_by = st.selectbox(
            "Sort By",
            options=['confidence', 'compliance', 'distance', 'time'],
            format_func=lambda x: {
                "confidence": "Evidence confidence",
                "compliance": "Checks passed",
                "distance": "Route distance",
                "time": "Estimated time",
            }.get(x, str(x)),
        )
    
    with col_f3:
        show_top = st.number_input("Show Top N", min_value=1, max_value=len(scenarios), value=min(5, len(scenarios)))
    
    # Filter and sort
    filtered = [s for s in scenarios if s.risk_level.value in risk_filter]
    
    sort_key = {
        'confidence': lambda s: s.confidence_score,
        'compliance': lambda s: s.compliance_score,
        'distance': lambda s: s.evacuation_route.distance,
        'time': lambda s: s.evacuation_route.estimated_time
    }.get(sort_by, lambda s: s.confidence_score)
    
    filtered.sort(key=sort_key, reverse=True)
    filtered = filtered[:show_top]
    
    st.markdown("---")
    
    # Display scenarios
    st.markdown(f"### Showing {len(filtered)} of {len(scenarios)} Scenarios")
    selected_id = st.session_state.get("selected_scenario_id")
    visible_scenario_ids = {scenario.scenario_id for scenario in filtered}
    if selected_id and selected_id not in visible_scenario_ids:
        st.session_state.selected_scenario_id = None
    
    for i, scenario in enumerate(filtered):
        # Determine border color based on risk
        risk_color = get_risk_color(scenario.risk_level)
        
        with st.container():
            st.markdown(
                f'<div class="scenario-card" style="border-left:6px solid {risk_color};">'
                f'<strong>Scenario #{i + 1}</strong> · {scenario.risk_level.value.upper()} screening priority'
                f'</div>',
                unsafe_allow_html=True,
            )
            # Scenario header
            col_h1, col_h2, col_h3 = st.columns([3, 2, 1])
            
            with col_h1:
                st.markdown(f"""
                <div style="border-left: 5px solid {risk_color}; padding-left: 10px;">
                    <h4 style="margin:0;">#{i+1} {html.escape(str(scenario.name))}</h4>
                    <p style="margin:0;color:var(--app-muted);font-size:0.8rem;">ID: {html.escape(str(scenario.scenario_id))}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_h2:
                st.markdown(
                    get_risk_badge(scenario.risk_level)
                    + "&nbsp;"
                    + get_compliance_badge(scenario.compliance_status),
                    unsafe_allow_html=True,
                )
            
            with col_h3:
                is_selected = st.session_state.selected_scenario_id == scenario.scenario_id
                st.button(
                    "Close Details" if is_selected else "View Details",
                    key=f"details_btn_{scenario.scenario_id}",
                    type="primary" if is_selected else "secondary",
                    on_click=toggle_scenario_details,
                    args=(scenario.scenario_id,),
                )
            
            # Metrics
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            with col_m1:
                st.metric("Distance", f"{scenario.evacuation_route.distance:.1f}m")
            with col_m2:
                st.metric("Evac. Time", f"{scenario.evacuation_route.estimated_time:.1f}s")
            with col_m3:
                st.metric("Checks Passed", f"{scenario.compliance_score*100:.0f}%")
            with col_m4:
                st.metric("Evidence Confidence", f"{scenario.confidence_score*100:.0f}%")
            with col_m5:
                st.metric("Check Findings", len(scenario.violated_regulations))
            
            # Violations and recommendations
            if scenario.violated_regulations:
                with st.expander("⚠️ Check Findings & Recommendations"):
                    st.markdown("**Prototype Check Findings:**")
                    for v in scenario.violated_regulations:
                        st.error(f"❌ {v}")
                    
                    st.markdown("**Engineering Review Recommendations:**")
                    for r in scenario.recommendations:
                        st.info(f"💡 {r}")

            if st.session_state.selected_scenario_id == scenario.scenario_id:
                render_selected_scenario_details(result, scenario)

            st.markdown("---")

    # Route comparison chart
    st.markdown("### Route Comparison")
    fig_comp = create_route_comparison_chart(scenarios)
    st.plotly_chart(fig_comp, key="scenario_route_comp")

# ==============================================================================
# TAB 5: EXPLAINABILITY / DECISION TRACE
# ==============================================================================
def render_explainability(result):
    """Render Explainability panel."""
    st.markdown('<div class="section-header">🧠 Explainability & Decision Trace</div>', unsafe_allow_html=True)
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available. Run analysis first.")
        return
    
    scenarios = result.scenarios
    
    # Scenario selector
    st.markdown("### Select Scenario to Explain")
    
    scenario_options = [f"#{i+1}: {s.name} ({s.risk_level.value.upper()})" for i, s in enumerate(scenarios)]
    selected = st.selectbox("Scenario", options=range(len(scenarios)), format_func=lambda i: scenario_options[i])
    
    scenario = scenarios[selected]
    regulation_phrase = (
        f"Parsed {result.regulation_clause_count} uploaded regulation clause(s) "
        f"and {getattr(result, 'regulation_rule_count', 0)} structured numeric rule(s)"
        if result.regulation_source == "uploaded_regulations"
        else "Used built-in default screening constraints because no regulation file was uploaded"
    )
    rag_phrase = (
        f"Regulation evidence retrieval was enabled using {result.retrieval_mode}."
        if result.rag_enabled
        else "Regulation evidence retrieval was not used for this run."
    )
    
    st.markdown("---")
    
    # Explanation sections
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### Deterministic Decision Trace")
        geometry_mode = result.source_mode == "geometry_derived"
        analysis_subject = "screened IFC elements" if geometry_mode else "spaces"
        occupancy_phrase = (
            "Occupancy was not inferred from structural elements."
            if geometry_mode
            else "Extracted geometry, connectivity, and estimated occupancy."
        )
        route_phrase = (
            "inferred geometry-screening path"
            if geometry_mode
            else "possible evacuation route"
        )
        
        # Step-by-step reasoning
        steps = [
            ("1. Building Analysis", f"Analyzed **{len(result.building.spaces)} {analysis_subject}**. {occupancy_phrase}"),
            ("2. Spatial Graph Construction", f"Built a NetworkX graph representing building topology and each {route_phrase}."),
            ("3. Route Calculation", f"Applied Dijkstra's shortest path algorithm from **{scenario.origin_space_name}** to the nearest {'inferred egress point' if geometry_mode else 'exit'}. Route length: **{scenario.evacuation_route.distance:.1f}m**."),
            ("4. Regulation Evidence", f"{regulation_phrase}. {rag_phrase}"),
            ("5. Implemented Constraint Checks", f"Evaluated {len(scenario.violated_regulations) + 2} prototype constraints. **{len(scenario.violated_regulations)} findings** identified."),
            ("6. Screening Priority", f"Classified as **{scenario.risk_level.value.upper()} PRIORITY** using deterministic, uncalibrated factors. Screening index: **{scenario.screening_index:.3f}** (higher means lower priority, not proven safety)."),
            ("7. Explanation Generation", f"Generated natural language explanation with traceable regulation references and improvement recommendations."),
        ]
        
        for title, desc in steps:
            safe_title = html.escape(str(title))
            safe_desc = html.escape(str(desc).replace("**", ""))
            with st.container():
                st.markdown(f"""
                <div style="background-color: var(--app-panel); color: var(--app-text); padding: 12px; border: 1px solid var(--app-border); border-radius: 6px; margin-bottom: 8px;">
                    <strong style="color: var(--app-heading);">{safe_title}</strong><br>
                    <span style="color: var(--app-muted); font-size: 0.9rem;">{safe_desc}</span>
                </div>
                """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### Traceability")
        
        # IFC Data Used
        st.markdown("""
        <div class="info-box">
            <strong>📊 IFC Data Used</strong><br>
            <small>
            • Origin: {}<br>
            • Destination: {}<br>
            • Path Nodes: {}<br>
            • Distance: {:.1f}m<br>
            • Est. Time: {:.1f}s
            </small>
        </div>
        """.format(
            html.escape(str(scenario.origin_space_name)),
            html.escape(str(scenario.evacuation_route.destination)),
            len(scenario.evacuation_route.path),
            scenario.evacuation_route.distance,
            scenario.evacuation_route.estimated_time
        ), unsafe_allow_html=True)
        
        # Regulation Triggers
        st.markdown("""
        <div class="warning-box">
            <strong>📜 Regulation Triggers</strong><br>
            <small>
            {}
            </small>
        </div>
        """.format(
            "<br>".join([f"• {html.escape(str(v))}" for v in scenario.violated_regulations]) if scenario.violated_regulations else "• No violations detected"
        ), unsafe_allow_html=True)
        
        # Model Confidence
        st.markdown("""
        <div class="success-box">
            <strong>🎯 Confidence & Transparency</strong><br>
            <small>
            • Evidence confidence: {:.1f}%<br>
            • Based on: route-source quality and IFC measurement completeness<br>
            • Method: deterministic weighted score, not a hidden black-box model
            </small>
        </div>
        """.format(scenario.confidence_score * 100), unsafe_allow_html=True)

        st.markdown("### Screening Factors")
        st.json(scenario.risk_factors)
    
    # Natural Language Explanation
    st.markdown("---")
    st.markdown("### Natural Language Explanation")
    
    st.markdown(f"""
    <div style="background-color: var(--app-panel-strong); border: 1px solid var(--app-border); border-radius: 8px; padding: 1.5rem;">
        <p style="font-size: 1.05rem; line-height: 1.6; color: var(--app-text);">
            {html.escape(str(scenario.explanation))}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Anti-Black-Box Decision Trace")
    st.caption("This is the audit trail used to explain how the scenario was generated and classified.")
    for item in scenario.decision_trace:
        with st.expander(item["step"], expanded=False):
            st.json(item)
    if scenario.data_quality_notes:
        st.markdown("### Data Quality Notes")
        for note in scenario.data_quality_notes:
            st.warning(note)
    
    with st.expander("Model assumptions and score semantics", expanded=False):
        st.warning(ACADEMIC_USE_NOTICE)
        st.json({
            "score_semantics": screening_index_semantics(),
            "assumption_registry": standard_assumption_registry(),
        })

# ==============================================================================
# TAB 6: RISK & SAFETY ANALYSIS
# ==============================================================================
def render_risk_analysis(result):
    """Render deterministic screening-indicator analysis."""
    st.markdown('<div class="section-header">⚠️ Screening Indicator Analysis</div>', unsafe_allow_html=True)
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available. Run analysis first.")
        return
    
    scenarios = result.scenarios
    
    st.markdown("### Standard Screening Scope")
    st.info(
        "This tab compares deterministic route-screening indicators. It does not calculate physical ASET. "
        "Use Fire Scenario Testing for the separate graph-based ASET/RSET-inspired model, which is also uncalibrated."
    )
    
    st.markdown("---")
    
    # Risk heatmap
    col_hm, col_stats = st.columns([2, 1])
    
    with col_hm:
        st.markdown("### Screening Indicator Heatmap")
        fig_heatmap = create_risk_heatmap(scenarios)
        st.plotly_chart(fig_heatmap, key="risk_heatmap")
    
    with col_stats:
        st.markdown("### Screening Statistics")
        
        # Calculate risk metrics
        risk_counts = {'low': 0, 'medium': 0, 'high': 0}
        total_violations = 0
        avg_distance = 0
        avg_time = 0
        
        if scenarios:
            for s in scenarios:
                risk_counts[s.risk_level.value] = risk_counts.get(s.risk_level.value, 0) + 1
                total_violations += len(s.violated_regulations)
                avg_distance += s.evacuation_route.distance
                avg_time += s.evacuation_route.estimated_time
            
            avg_distance /= len(scenarios)
            avg_time /= len(scenarios)
        
        st.metric("Avg Evacuation Distance", f"{avg_distance:.1f}m")
        st.metric("Avg Evacuation Time", f"{avg_time:.1f}s")
        st.metric("Prototype Check Findings", total_violations)
        st.metric("High-Priority Scenarios", risk_counts.get('high', 0))
        avg_index = sum(s.screening_index for s in scenarios) / len(scenarios)
        avg_evidence = sum(s.confidence_score for s in scenarios) / len(scenarios)
        st.metric("Avg Screening Index", f"{avg_index:.3f}", help="Higher means lower screening priority, not proven safety.")
        st.metric("Avg Evidence Confidence", f"{avg_evidence * 100:.0f}%")
    
    st.markdown("---")
    
    # Bottleneck analysis
    st.markdown("### Route Bottleneck Indicators")
    
    bottleneck_data = []
    for i, s in enumerate(scenarios):
        bottleneck_count = int(s.risk_factors.get("bottleneck_count", 0))
        bottleneck_data.append({
            'Scenario': f"#{i+1}: " + s.name[:15],
            'Route Bottlenecks': bottleneck_count,
            'Evacuation Time (s)': round(s.evacuation_route.estimated_time, 1),
            'Screening Priority': s.risk_level.value,
        })
    
    if bottleneck_data:
        df_bottleneck = pd.DataFrame(bottleneck_data)
        
        fig_bottleneck = px.scatter(
            df_bottleneck,
            x='Evacuation Time (s)',
            y='Route Bottlenecks',
            color='Screening Priority',
            size=[max(8, row['Route Bottlenecks'] * 8) for row in bottleneck_data],
            title="Detected Route Bottlenecks vs Estimated Travel Time",
            color_discrete_map={'low': '#28a745', 'medium': '#ffc107', 'high': '#dc3545'}
        )
        st.plotly_chart(fig_bottleneck, key="risk_bottleneck")
    
    # Route comparison
    st.markdown("---")
    st.markdown("### Route Comparison Matrix")
    
    comparison_data = []
    for i, s in enumerate(scenarios[:5]):  # Top 5
        comparison_data.append({
            'Scenario': f"#{i+1}: " + s.name[:12],
            'Distance (m)': round(s.evacuation_route.distance, 1),
            'Time (s)': round(s.evacuation_route.estimated_time, 1),
            'Checks Passed (%)': round(s.compliance_score * 100, 0),
            'Evidence Confidence (%)': round(s.confidence_score * 100, 0),
            'Screening Priority': s.risk_level.value.upper(),
        })
    
    df_comp = pd.DataFrame(comparison_data)
    st.dataframe(df_comp)

# ==============================================================================
# TAB 7: EXPERT REVIEW PANEL (HITL)
# ==============================================================================
def render_structured_domain_review(result, scenarios):
    """Collect a protocol-shaped record without asserting reviewer credentials."""
    with st.expander("Structured Preliminary Domain Review", expanded=False):
        st.warning(
            "Governance gate: obtain written supervisor or ethics confirmation before collecting "
            "participant data. The software does not verify reviewer identity or qualifications."
        )
        st.caption(
            "Use competence scope and a sign-off reference rather than unnecessary personal details. "
            "A completed form is preliminary evidence, not professional approval."
        )

        ethics_reference = st.text_input(
            "Ethics or supervisor confirmation reference",
            key="domain_ethics_reference",
            placeholder="Email/date/reference confirming this review activity is permitted",
        )
        competence_scope = st.text_input(
            "Reviewer competence scope",
            key="domain_competence_scope",
            placeholder="For example: chartered fire engineer reviewing early-stage route evidence",
        )
        review_date = st.text_input(
            "Domain review date (YYYY-MM-DD)",
            value=time.strftime("%Y-%m-%d"),
            key="domain_review_date",
        )

        case_labels = {
            scenario.scenario_id: f"{scenario.name} ({scenario.scenario_id})"
            for scenario in scenarios
        }
        cases_reviewed = st.multiselect(
            "Cases reviewed for preliminary domain review",
            options=list(case_labels),
            default=[scenarios[0].scenario_id] if scenarios else [],
            format_func=lambda scenario_id: case_labels[scenario_id],
            key="domain_cases_reviewed",
        )

        st.markdown("#### Reviewer ratings")
        st.caption("1 = poor, 5 = strong. Select Not rated when the reviewer did not assess a criterion.")
        ratings = {}
        rating_options = ["Not rated", 1, 2, 3, 4, 5]
        for field, label in RATING_FIELDS.items():
            ratings[field] = st.selectbox(
                label,
                rating_options,
                key=f"domain_rating_{field}",
            )

        safety_findings = st.text_area(
            "Safety-critical findings (one per line)",
            key="domain_safety_findings",
        )
        other_findings = st.text_area(
            "Other domain-review findings (one per line)",
            key="domain_other_findings",
        )
        required_corrections = st.text_area(
            "Required corrections (one per line)",
            key="domain_required_corrections",
        )
        author_disposition = st.text_area(
            "Project-author correction disposition (one per line)",
            key="domain_author_disposition",
            help="Required when the reviewer records corrections.",
        )
        signoff_reference = st.text_input(
            "Reviewer sign-off or consent reference",
            key="domain_signoff_reference",
            placeholder="Signed review filename, email reference, or approved consent record",
        )

        if st.button("Save preliminary domain-review record", key="save_domain_review"):
            record = build_preliminary_domain_review(
                source_file_sha256=result.source_file_sha256,
                ifc_schema=result.ifc_schema,
                ethics_confirmation_reference=ethics_reference,
                reviewer_competence_scope=competence_scope,
                cases_reviewed=cases_reviewed,
                ratings=ratings,
                safety_critical_findings=safety_findings,
                other_findings=other_findings,
                required_corrections=required_corrections,
                reviewer_signoff_reference=signoff_reference,
                project_author_disposition=author_disposition,
                review_date=review_date,
            )
            st.session_state.domain_review_records.append(record)
            if record["missing_fields"]:
                st.warning(
                    f"Record saved as {record['execution_status']}; missing: "
                    + ", ".join(record["missing_fields"])
                )
            else:
                st.success(f"Record saved as {record['execution_status']}.")

        if st.session_state.domain_review_records:
            latest = st.session_state.domain_review_records[-1]
            st.markdown("#### Latest preliminary domain-review record")
            st.json(latest)
            st.download_button(
                "Download preliminary domain-review records JSON",
                json.dumps(st.session_state.domain_review_records, indent=2),
                "preliminary_domain_review_records.json",
                "application/json",
                key="download_domain_reviews",
            )


def render_manual_accessibility_review():
    """Collect the manual browser checks that automation cannot establish."""
    with st.expander("Manual Accessibility Verification", expanded=False):
        st.info(
            "Perform these checks in the actual demo browser. A completed record documents bounded "
            "manual testing; it is not a WCAG conformance certificate."
        )
        browser = st.text_input(
            "Accessibility test browser and version",
            key="accessibility_browser",
            placeholder="For example: Chrome 140",
        )
        operating_system = st.text_input(
            "Accessibility test operating system",
            key="accessibility_operating_system",
            placeholder="For example: macOS 15",
        )
        evidence_reference = st.text_input(
            "Accessibility evidence reference",
            key="accessibility_evidence_reference",
            placeholder="Screenshot folder, screen recording, or dated test note",
        )
        outcomes = {}
        for check, label in MANUAL_ACCESSIBILITY_CHECKS.items():
            outcomes[check] = st.selectbox(
                f"Accessibility check: {label}",
                ["Not tested", "Pass", "Fail", "Not applicable"],
                key=f"accessibility_outcome_{check}",
            )
        notes = st.text_area(
            "Accessibility test notes",
            key="accessibility_notes",
            placeholder="Record defects, reproduction steps and corrective actions.",
        )

        if st.button("Save manual accessibility record", key="save_accessibility_record"):
            record = build_manual_accessibility_record(
                browser=browser,
                operating_system=operating_system,
                outcomes=outcomes,
                notes=notes,
                evidence_reference=evidence_reference,
            )
            st.session_state.accessibility_audit_records.append(record)
            if record["execution_status"] == "completed_author_accessibility_check":
                st.success("Bounded manual accessibility check recorded as complete.")
            else:
                st.warning(f"Accessibility record saved as {record['execution_status']}.")

        if st.session_state.accessibility_audit_records:
            latest = st.session_state.accessibility_audit_records[-1]
            st.markdown("#### Latest manual accessibility record")
            st.json(latest)
            st.download_button(
                "Download manual accessibility records JSON",
                json.dumps(st.session_state.accessibility_audit_records, indent=2),
                "manual_accessibility_records.json",
                "application/json",
                key="download_accessibility_records",
            )


def render_independent_label_review():
    """Provide a blinded human-labelling handoff for the ML experiment."""
    with st.expander("Independent ML Label Review", expanded=False):
        st.info(
            "The current ML metrics use rule-seeded silver labels. This pack removes those answers "
            "so an authorised reviewer can label space use independently. Do not reveal the silver "
            "labels before the reviewer completes the pack."
        )
        dataset_path = Path(__file__).resolve().parents[2] / "evaluation" / "space_classification" / "silver_labels.csv"
        source_rows = load_space_label_records(dataset_path)
        blinded_pack = build_blinded_label_review_pack(source_rows)
        st.download_button(
            "Download blinded independent-label review pack CSV",
            serialise_label_review_pack(blinded_pack),
            "independent_space_label_review.csv",
            "text/csv",
            key="download_independent_label_pack",
        )
        st.caption(
            "Allowed labels: circulation, residential, sanitary, kitchen, service_storage, "
            "clinical, assembly and workplace. Set review_status to reviewer_confirmed and "
            "provide confidence 1-5 plus a confirmation reference for every row."
        )
        completed_pack = st.file_uploader(
            "Upload completed independent-label review pack",
            type=["csv"],
            key="completed_independent_label_pack",
        )
        if completed_pack is not None:
            try:
                rows = parse_label_review_pack_csv(completed_pack.getvalue().decode("utf-8-sig"))
                validation = validate_label_review_pack(rows)
                st.session_state.space_label_review_validation = validation
                if validation["eligible_for_grouped_model_evaluation"]:
                    st.success("Review pack is structurally complete and eligible for grouped model evaluation.")
                else:
                    st.warning(
                        f"Review pack is incomplete: {validation['invalid_record_count']} invalid record(s)."
                    )
                st.json(validation)
            except (UnicodeDecodeError, ValueError) as exc:
                st.session_state.space_label_review_validation = {
                    "status": "invalid_upload",
                    "error": str(exc),
                    "eligible_for_grouped_model_evaluation": False,
                }
                st.error(f"Independent-label review pack could not be validated: {exc}")


def render_expert_review(result):
    """Render a session-scoped research review record."""
    st.markdown('<div class="section-header">👤 Research Review Record</div>', unsafe_allow_html=True)
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available for review. Run analysis first.")
        return
    
    scenarios = result.scenarios
    
    # Introduction
    st.markdown("""
    <div class="warning-box">
        <strong>Human-in-the-Loop Research Protocol</strong><br>
        <small>
        Record a researcher/reviewer disposition for each screening scenario. This session record is not
        authenticated professional approval, a durable regulatory audit log or validation of fire safety.
        </small>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Formal Evaluation Evidence")
    render_structured_domain_review(result, scenarios)
    render_manual_accessibility_review()
    render_independent_label_review()
    
    st.markdown("---")
    
    # Scenario selector
    st.markdown("### Select Scenario for Review")
    
    scenario_options = [f"#{i+1}: {s.name}" for i, s in enumerate(scenarios)]
    selected_idx = st.selectbox("Scenario", options=range(len(scenarios)), format_func=lambda i: scenario_options[i])
    
    scenario = scenarios[selected_idx]
    scenario_id = scenario.scenario_id
    
    st.markdown("---")
    
    # Scenario details
    col_detail, col_review = st.columns([3, 2])
    
    with col_detail:
        st.markdown("### Scenario Details")
        
        # Risk badge
        risk_color = get_risk_color(scenario.risk_level)
        st.markdown(f"""
        <div style="display: flex; gap: 10px; margin-bottom: 1rem;">
            {get_risk_badge(scenario.risk_level)}
            {get_compliance_badge(scenario.compliance_status)}
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Distance", f"{scenario.evacuation_route.distance:.1f}m")
        with col_m2:
            st.metric("Time", f"{scenario.evacuation_route.estimated_time:.1f}s")
        with col_m3:
            st.metric("Evidence Confidence", f"{scenario.confidence_score*100:.0f}%")
        
        # Route path
        st.markdown("**Evacuation Path:**")
        path_str = " → ".join(scenario.evacuation_route.path[:5])
        st.code(path_str)
        
        # Violations
        if scenario.violated_regulations:
            st.markdown("**Prototype Check Findings:**")
            for v in scenario.violated_regulations:
                st.error(f"❌ {v}")
        
        # Recommendations
        if scenario.recommendations:
            st.markdown("**System Recommendations:**")
            for r in scenario.recommendations:
                st.info(f"💡 {r}")
    
    with col_review:
        st.markdown("### Research Assessment")
        
        # Review form
        review_key = f"expert_review_{scenario_id}"
        comments_key = f"expert_comments_{scenario_id}"
        
        if review_key not in st.session_state.expert_reviews:
            st.session_state.expert_reviews[review_key] = "Not Reviewed"
        
        acknowledgement = st.checkbox(
            "I understand this review status is not professional approval or statutory sign-off.",
            key=f"review_ack_{scenario_id}",
        )
        decision = st.radio(
            "Research Review Status",
            options=["Not Reviewed", "✅ Accepted for research follow-up", "⚠️ Needs Revision", "❌ Rejected"],
            key=f"decision_radio_{scenario_id}",
            index=0,
        )
        
        # Comments
        comments = st.text_area(
            "Review Comments",
            placeholder="Record evidence concerns, required corrections, or research follow-up rationale...",
            key=f"comments_area_{scenario_id}",
            height=150
        )
        
        # Save button
        if st.button(
            "💾 Save Research Review",
            key=f"save_review_btn_{scenario_id}",
            disabled=not acknowledgement,
        ):
            st.session_state.expert_reviews[review_key] = {
                'decision': decision,
                'comments': comments,
                'scenario_id': scenario_id,
                'scenario_name': scenario.name,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'record_scope': 'session_scoped_research_review_not_professional_approval',
                'limitations_acknowledged': True,
            }
            st.success(f"✅ Review saved: {decision}")
    
    # Review history
    st.markdown("---")
    st.markdown("### Review History")
    
    reviews = [v for k, v in st.session_state.expert_reviews.items() if isinstance(v, dict)]
    
    if reviews:
        review_df = pd.DataFrame([
            {
                'Scenario': r['scenario_name'],
                'Decision': r['decision'],
                'Comments': r['comments'][:50] + '...' if len(r['comments']) > 50 else r['comments'],
                'Timestamp': r['timestamp']
            }
            for r in reviews
        ])
        st.dataframe(review_df)
    else:
        st.info("No reviews recorded yet. Use the panel above to review scenarios.")
    
    # Audit trail
    st.markdown("---")
    st.markdown("### Audit Trail")
    st.markdown("""
    <div class="info-box">
        <strong>Review Tracking:</strong><br>
        <small>
        • Saved research dispositions are timestamped in the current Streamlit session<br>
        • Records can be included in the evidence export<br>
        • This supports research traceability, not regulatory compliance verification
        </small>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# TAB 8: EXPORT & REPORTING
# ==============================================================================
def render_export(result):
    """Render Export & Reporting panel."""
    st.markdown('<div class="section-header">📤 Export & Reporting</div>', unsafe_allow_html=True)
    
    if not result:
        st.info("📋 No data available for export. Run analysis first.")
        return
    
    # Report preview
    st.markdown("### Screening Evidence Report Preview")
    
    st.markdown("""
    <div class="success-box">
        <strong>Report Ready for Export</strong><br>
        <small>
        The complete JSON evidence report contains scenarios, implemented checks, decision traces,
        assumptions, provenance and session review records. It is a research-review package,
        not fire-strategy approval or statutory sign-off.
        </small>
    </div>
    """, unsafe_allow_html=True)
    
    # Executive summary
    st.markdown("---")
    st.markdown("### Executive Summary")
    
    if result.scenarios:
        scenarios = result.scenarios
        risk_counts = {'low': 0, 'medium': 0, 'high': 0}
        for s in scenarios:
            risk_counts[s.risk_level.value] = risk_counts.get(s.risk_level.value, 0) + 1
        
        avg_compliance = sum(s.compliance_score for s in scenarios) / len(scenarios)
        total_violations = sum(len(s.violated_regulations) for s in scenarios)
        
        st.markdown(f"""
        <div style="background-color: var(--app-panel-strong); color: var(--app-text); border: 1px solid var(--app-border); border-radius: 8px; padding: 1.5rem;">
            <h4>Building: {html.escape(str(result.building.name)) if result.building else 'N/A'}</h4>
            <p><strong>Total Scenarios Analyzed:</strong> {len(scenarios)}</p>
            <p><strong>Screening-Priority Distribution:</strong> {risk_counts.get('low', 0)} Low, {risk_counts.get('medium', 0)} Medium, {risk_counts.get('high', 0)} High</p>
            <p><strong>Average Implemented Checks Passed:</strong> {avg_compliance * 100:.1f}%</p>
            <p><strong>Total Prototype Check Findings:</strong> {total_violations}</p>
            <p><strong>Analysis Date:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Export controls
    st.markdown("---")
    st.markdown("### Export Data")
    
    col_json, col_csv, col_xml = st.columns(3)
    
    with col_json:
        st.markdown("**JSON Export**")
        st.markdown("<small>Complete machine-readable evidence package</small>", unsafe_allow_html=True)
        
        export_data = build_complete_export_payload(result)
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name=f"screening_evidence_{safe_uploaded_filename(result.building.name if result.building else 'report')}_{time.strftime('%Y%m%d')}.json",
            mime="application/json",
            width='stretch',
        )
    
    with col_csv:
        st.markdown("**CSV Export**")
        st.markdown("<small>Summary-only spreadsheet with score direction metadata</small>", unsafe_allow_html=True)
        
        csv_data = build_scenarios_csv(result.scenarios)
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name=f"screening_summary_{safe_uploaded_filename(result.building.name if result.building else 'report')}_{time.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width='stretch',
            disabled=not bool(result.scenarios),
        )
    
    with col_xml:
        st.markdown("**XML Export**")
        st.markdown("<small>Summary-only XML; not an IFC/BIM exchange file</small>", unsafe_allow_html=True)
        
        xml_content = build_scenarios_xml(result, time.strftime('%Y-%m-%dT%H:%M:%S'))
        st.download_button(
            label="⬇️ Download XML",
            data=xml_content,
            file_name=f"screening_summary_{safe_uploaded_filename(result.building.name if result.building else 'report')}_{time.strftime('%Y%m%d')}.xml",
            mime="application/xml",
            width='stretch',
        )
    
    # Full report generation
    st.markdown("---")
    st.markdown("### Complete Screening Evidence Report")
    
    if st.button("📑 Generate Complete Evidence Report", key="generate_full_report", type="primary"):
        with st.spinner("Generating the screening evidence report..."):
            try:
                report = build_complete_export_payload(result)
                report['executive_summary'] = create_export_summary(
                    result.scenarios,
                    result.building.name if result.building else 'Unknown',
                )
                
                json_str = json.dumps(report, indent=2)
                
                st.success("✅ Report generated successfully!")
                
                st.download_button(
                    label="⬇️ Download Complete Report (JSON)",
                    data=json_str,
                    file_name=f"screening_evidence_complete_{time.strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    width='stretch'
                )
                
            except Exception as e:
                st.error(f"Report generation error: {e}")

# ==============================================================================
# MAIN APP
# ==============================================================================
def main():
    """Main application entry point."""
    render_header()
    
    # Sidebar
    (
        ifc_file,
        regulation_file,
        regulation_metadata,
        max_scenarios,
        enable_rag,
        process_button,
    ) = render_sidebar()
    
    # Process if button clicked
    if process_button and ifc_file:
        process_files(
            ifc_file,
            regulation_file,
            regulation_metadata,
            max_scenarios,
            enable_rag,
        )
    
    # Main content area with tabs
    if st.session_state.processing_done and st.session_state.pipeline_result:
        result = st.session_state.pipeline_result
        
        # Create tabs
        tabs = st.tabs([
            "📊 Dashboard",
            "🏢 BIM Insights",
            "📜 Regulations",
            "🚨 Scenarios",
            "🧠 Explainability",
            "⚠️ Screening Analysis",
            "👤 Research Review",
            "📤 Export"
        ])
        
        with tabs[0]:
            render_dashboard(result)
        
        with tabs[1]:
            render_bim_insights(result)
        
        with tabs[2]:
            render_regulation_intelligence(result)
        
        with tabs[3]:
            render_evacuation_scenarios(result)
        
        with tabs[4]:
            render_explainability(result)
        
        with tabs[5]:
            render_risk_analysis(result)
        
        with tabs[6]:
            render_expert_review(result)
        
        with tabs[7]:
            render_export(result)
    
    else:
        # Welcome screen
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 3rem;">
            <h2>👋 Welcome to AI-Driven Generation of Evacuation Scenarios from Building Information Models</h2>
            <p style="color: var(--app-muted); font-size: 1.1rem;">
                This AI-assisted, deterministic decision-support system generates evacuation screening scenarios from BIM models,<br>
                checks them against parsed/default safety constraints, and provides explainable recommendations<br>
                for fire safety engineering review.
            </p>
            <br>
            <div style="background-color: var(--app-panel); color: var(--app-text); border: 1px solid var(--app-border); border-radius: 8px; padding: 2rem; display: inline-block;">
                <h4 style="margin-top: 0;">🚀 Getting Started</h4>
                <ol style="text-align: left; color: var(--app-text);">
                    <li>Upload your <strong>IFC building model</strong> in the sidebar</li>
                    <li>Optionally upload <strong>safety regulations</strong> (e.g., Approved Document B)</li>
                    <li>Configure analysis settings</li>
                    <li>Click <strong>"Generate Screening Scenarios"</strong></li>
                    <li>Review system-generated screening scenarios across all tabs</li>
                    <li>Record a <strong>session-scoped research review</strong> in the HITL panel</li>
                    <li>Export the complete screening evidence report</li>
                </ol>
            </div>
            <br><br>
            <p style="color: var(--app-muted); font-size: 0.9rem;">
                <strong>Documented IFC targets:</strong> IFC2X3, IFC4, IFC4X3, IFC4X3_ADD2 | <strong>NLP:</strong> spaCy | <strong>Evidence retrieval:</strong> TF-IDF + optional embeddings | <strong>Graph:</strong> NetworkX
            </p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
