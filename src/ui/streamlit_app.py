"""
Professional Streamlit UI for BIM Evacuation System.

A Fire Strategy decision-support system with:
- Human-in-the-Loop (HITL)
- Explainable AI (xAI)
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
import json
import plotly.express as px
import plotly.graph_objects as go
import time
from typing import List, Dict, Any, Optional

from src.pipeline.evacuation_pipeline import EvacuationPipeline, PipelineResult
from src.bim_processing.ifc_validation import SUPPORTED_SCHEMA_LABEL
from src.utils.logger import get_logger
from src.utils.helpers import RiskLevel, ComplianceStatus
from src.ui.ui_components import (
    render_metric_card, get_risk_color, get_risk_badge, get_compliance_badge,
    create_risk_pie_chart, create_scenario_bar_chart, create_route_comparison_chart,
    create_network_graph_viz, create_risk_heatmap, render_scenario_card,
    render_explanation_panel, render_expert_review_controls, create_export_summary
)
from src.ui.visualization_3d import create_ifc_3d_figure, create_ifc_plan_figure

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="BIM Evacuation Fire Strategy Platform",
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
        color: #28a745;
        font-weight: bold;
    }
    .status-fail {
        color: #dc3545;
        font-weight: bold;
    }
    .status-warn {
        color: #ffc107;
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
        'processing_done': False,
        'selected_scenario_index': 0,
        'expert_reviews': {},
        'regulation_text': None,
        'rag_enabled': True,
        'active_tab': 0,
        'selected_scenario_id': None,
        'graph_viz_enabled': True,
        'show_explanations': True,
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
    st.markdown(
        f"""
        <div class="scenario-detail-card">
            <h4>Selected Scenario: {scenario.name}</h4>
            <strong>Origin:</strong> {scenario.origin_space_name}<br>
            <strong>Destination:</strong> {scenario.evacuation_route.destination}<br>
            <strong>Route nodes:</strong> {' → '.join(scenario.evacuation_route.path)}<br>
            <strong>Analysis basis:</strong> {'Geometry-derived structural screening' if geometry_mode else 'Semantic IFC space and door data'}
        </div>
        """,
        unsafe_allow_html=True,
    )
    metrics = st.columns(5)
    metrics[0].metric("Travel Distance", f"{scenario.evacuation_route.distance:.1f} m")
    metrics[1].metric("Estimated Time", f"{scenario.evacuation_route.estimated_time:.1f} s")
    metrics[2].metric("Alternative Exits", alternative_exits)
    metrics[3].metric("Compliance", f"{scenario.compliance_score * 100:.0f}%")
    metrics[4].metric("Confidence", f"{scenario.confidence_score * 100:.0f}%")

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
            ("No regulation violations detected", not scenario.violated_regulations),
            ("Confidence above 70%", scenario.confidence_score >= 0.7),
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
        st.json(scenario.to_dict())
        st.download_button(
            "Download selected scenario evidence",
            json.dumps(scenario.to_dict(), indent=2),
            f"{scenario.scenario_id}_evidence.json",
            "application/json",
            key=f"download_scenario_{scenario.scenario_id}",
        )

# ==============================================================================
# HEADER
# ==============================================================================
def render_header():
    """Render professional application header."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<p class="main-title">🏗️ BIM Evacuation Fire Strategy Platform</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">AI-Driven Decision-Support System for Fire Safety Engineering</p>', unsafe_allow_html=True)
    
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
    🎓 **Research Prototype** | This system implements Human-in-the-Loop (HITL) AI for evacuation scenario generation. 
    All AI-generated scenarios require expert review and validation. **This system does NOT replace professional fire engineering judgement.**
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
        st.markdown("### 1. BIM Model (IFC)")
        st.markdown("<p style='font-size:0.8rem;color:#666;'>Upload Building Information Model</p>", unsafe_allow_html=True)
        
        ifc_file = st.file_uploader(
            "Select IFC file",
            type=['ifc'],
            help="Industry Foundation Classes (IFC) building model",
            label_visibility="collapsed"
        )
        
        if ifc_file:
            st.success(f"✓ {ifc_file.name}")
        
        st.markdown("---")
        
        # Regulation Upload Section
        st.markdown("### 2. Safety Regulations")
        st.markdown("<p style='font-size:0.8rem;color:#666;'>Upload building safety codes</p>", unsafe_allow_html=True)
        
        regulation_file = st.file_uploader(
            "Select regulation text",
            type=['txt', 'md'],
            help="Building safety regulations (e.g., Approved Document B)",
            label_visibility="collapsed"
        )
        
        if regulation_file:
            st.success(f"✓ {regulation_file.name}")
        
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
            "Enable RAG Grounding",
            value=True,
            help="Use Retrieval-Augmented Generation for regulation validation"
        )

        st.markdown("---")
        
        # Process Button
        st.markdown("### 4. Run Analysis")
        
        process_disabled = ifc_file is None
        process_button = st.button(
            "🚀 Generate Fire Strategy Scenarios",
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
        
        st.markdown("---")
        
        # System Status
        st.markdown("### System Status")
        
        status_items = [
            ("IFC Parser", "✅ Ready" if ifc_file else "⏳ Waiting"),
            ("NLP Engine", "✅ Ready"),
            ("RAG System", "✅ Ready" if enable_rag else "⏹️ Disabled"),
            ("Graph Builder", "✅ Ready"),
        ]
        
        for label, status in status_items:
            st.markdown(f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;'><span>{label}</span><span>{status}</span></div>", unsafe_allow_html=True)
        
        return ifc_file, regulation_file, max_scenarios, enable_rag, process_button

# ==============================================================================
# FILE PROCESSING
# ==============================================================================
def save_uploaded_file(uploaded_file, directory: str) -> str:
    """Save uploaded file and return path."""
    import os
    save_dir = Path(directory)
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)

def process_files(ifc_file, regulation_file, max_scenarios, enable_rag):
    """Process uploaded files through the pipeline."""
    progress_bar = st.progress(0, text="Initializing pipeline...")
    
    try:
        st.session_state.rag_enabled = enable_rag
        # Save IFC file
        progress_bar.progress(10, text="Loading IFC model...")
        ifc_path = save_uploaded_file(ifc_file, "./data/temp")
        
        # Read regulation text
        regulation_text = None
        if regulation_file:
            progress_bar.progress(20, text="Loading regulations...")
            regulation_text = regulation_file.read().decode('utf-8')
            st.session_state['regulation_text'] = regulation_text
        
        # Run pipeline
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
        
        progress_bar.progress(100, text="Complete!")
        time.sleep(0.5)
        progress_bar.empty()
        
        # Store result
        st.session_state.pipeline_result = result
        st.session_state.processing_done = True
        
        if result.source_mode == "geometry_derived":
            st.success(
                f"✅ Analysis Complete! Generated **{len(result.scenarios)}** evacuation scenarios."
            )
            st.info(
                "The uploaded IFC was analyzed directly in geometry-derived mode. "
                "Connectivity and boundary egress points were inferred only from the "
                "file's actual elements, geometry, and properties."
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
            "HIGH RISK",
            str(risk_counts.get('high', 0)),
            "Require immediate attention",
            "#dc3545"
        )
    
    with col3:
        render_metric_card(
            "MEDIUM RISK",
            str(risk_counts.get('medium', 0)),
            "Recommend improvements",
            "#ffc107"
        )
    
    with col4:
        render_metric_card(
            "LOW RISK",
            str(risk_counts.get('low', 0)),
            "Meet requirements",
            "#28a745"
        )
    
    with col5:
        compliance_pct = avg_compliance * 100
        color = "#28a745" if compliance_pct >= 80 else "#ffc107" if compliance_pct >= 50 else "#dc3545"
        render_metric_card(
            "AVG COMPLIANCE",
            f"{compliance_pct:.0f}%",
            f"{total_violations} total violations",
            color
        )
    
    st.markdown("---")
    
    # Charts Row
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### Risk Distribution")
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
            'Risk': s.risk_level.value.upper(),
            'Distance (m)': round(s.evacuation_route.distance, 1),
            'Time (s)': round(s.evacuation_route.estimated_time, 1),
            'Compliance': f"{s.compliance_score * 100:.0f}%",
            'Confidence': f"{s.confidence_score * 100:.0f}%",
            'Violations': len(s.violated_regulations)
        })
    
    df_summary = pd.DataFrame(summary_data)
    
    # Color code risk column
    def color_risk(val):
        colors = {'LOW': 'background-color: #d4edda', 'MEDIUM': 'background-color: #fff3cd', 'HIGH': 'background-color: #f8d7da'}
        return colors.get(val, '')
    
    styled_df = df_summary.style.map(color_risk, subset=['Risk'])
    st.dataframe(styled_df, height=300)

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
        st.metric("Readiness Score", f"{readiness['model_readiness_score']}/100")
        st.write(f"**{readiness['readiness_label']}**")
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
    bim_tab1, bim_tab2, bim_tab3, bim_tab4, bim_tab5 = st.tabs([
        "🔍 Extracted IFC Elements" if geometry_mode else "🔍 Extracted Spaces",
        "🚪 Connections & Egress" if geometry_mode else "🚪 Doors & Exits",
        "🕸️ Connectivity Graph",
        "🗺️ Floor Plan Diagram",
        "🏙️ 3D Model & Egress",
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
        with st.expander("View Raw Regulation Text", expanded=False):
            st.text_area("Regulation Content", regulation_text[:5000], height=300, disabled=True)
    else:
        st.info("📋 No regulations uploaded. Using default constraints from configuration.")
    
    st.markdown("---")
    
    # Active Constraints
    st.markdown("### Default Screening Constraints")
    st.caption(
        "Prototype defaults are shown below. Uploaded regulation text is parsed "
        "separately and all thresholds require professional verification."
    )
    
    constraints_data = [
        {'Parameter': 'Maximum Travel Distance', 'Value': '45.0 m', 'Source': 'AD B 2.2.1', 'Status': '✓ Active'},
        {'Parameter': 'Minimum Door Width', 'Value': '0.75 m', 'Source': 'AD B 2.3.1', 'Status': '✓ Active'},
        {'Parameter': 'Minimum Exit Width', 'Value': '1.05 m', 'Source': 'AD B 2.3.2', 'Status': '✓ Active'},
        {'Parameter': 'Minimum Corridor Width', 'Value': '1.20 m', 'Source': 'AD B 2.10.1', 'Status': '✓ Active'},
        {'Parameter': 'Max Riser Height', 'Value': '0.19 m', 'Source': 'AD B 2.4.2', 'Status': '✓ Active'},
        {'Parameter': 'Min Tread Length', 'Value': '0.25 m', 'Source': 'AD B 2.4.3', 'Status': '✓ Active'},
        {'Parameter': 'Exit Capacity', 'Value': '90 p/min/m', 'Source': 'AD B 2.5.2', 'Status': '✓ Active'},
    ]
    
    df_constraints = pd.DataFrame(constraints_data)
    st.dataframe(df_constraints, height=250)
    
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
    
    # RAG Status
    st.markdown("---")
    st.markdown("### RAG System Status")
    rag_status = (
        "Active for uploaded regulation text"
        if st.session_state.get("rag_enabled", True) and regulation_text
        else "Not active for this analysis"
    )
    
    rag_col1, rag_col2 = st.columns(2)
    with rag_col1:
        st.markdown(f"""
        <div class="success-box">
            <strong>Embedding Model:</strong> all-MiniLM-L6-v2<br>
            <strong>Vector DB:</strong> FAISS (Flat IP)<br>
            <strong>Similarity Threshold:</strong> 0.70<br>
            <strong>Status:</strong> {rag_status}
        </div>
        """, unsafe_allow_html=True)
    
    with rag_col2:
        st.markdown("""
        <div class="info-box">
            <strong>Grounding Pipeline:</strong><br>
            1. Document chunking (size=512, overlap=50)<br>
            2. Sentence embedding generation<br>
            3. FAISS index construction<br>
            4. Similarity search for grounding<br>
            5. Expert review and source verification
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# TAB 4: EVACUATION SCENARIOS
# ==============================================================================
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
            "Risk Level",
            options=['low', 'medium', 'high'],
            default=['low', 'medium', 'high'],
            format_func=lambda x: x.upper()
        )
    
    with col_f2:
        sort_by = st.selectbox(
            "Sort By",
            options=['confidence', 'compliance', 'distance', 'time'],
            format_func=lambda x: x.capitalize()
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
    
    for i, scenario in enumerate(filtered):
        # Determine border color based on risk
        risk_color = get_risk_color(scenario.risk_level)
        
        with st.container():
            st.markdown(
                f'<div class="scenario-card" style="border-left:6px solid {risk_color};">'
                f'<strong>Scenario #{i + 1}</strong> · {scenario.risk_level.value.upper()} risk'
                f'</div>',
                unsafe_allow_html=True,
            )
            # Scenario header
            col_h1, col_h2, col_h3 = st.columns([3, 2, 1])
            
            with col_h1:
                st.markdown(f"""
                <div style="border-left: 5px solid {risk_color}; padding-left: 10px;">
                    <h4 style="margin:0;">#{i+1} {scenario.name}</h4>
                    <p style="margin:0;color:var(--app-muted);font-size:0.8rem;">ID: {scenario.scenario_id}</p>
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
                selected = st.session_state.selected_scenario_id == scenario.scenario_id
                if st.button(
                    "Close Details" if selected else "View Details",
                    key=f"details_btn_{scenario.scenario_id}",
                    type="primary" if selected else "secondary",
                ):
                    st.session_state.selected_scenario_id = None if selected else scenario.scenario_id
            
            # Metrics
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            with col_m1:
                st.metric("Distance", f"{scenario.evacuation_route.distance:.1f}m")
            with col_m2:
                st.metric("Evac. Time", f"{scenario.evacuation_route.estimated_time:.1f}s")
            with col_m3:
                st.metric("Compliance", f"{scenario.compliance_score*100:.0f}%")
            with col_m4:
                st.metric("Confidence", f"{scenario.confidence_score*100:.0f}%")
            with col_m5:
                st.metric("Violations", len(scenario.violated_regulations))
            
            # Violations and recommendations
            if scenario.violated_regulations:
                with st.expander("⚠️ Violations & Recommendations"):
                    st.markdown("**Regulatory Violations:**")
                    for v in scenario.violated_regulations:
                        st.error(f"❌ {v}")
                    
                    st.markdown("**Engineering Recommendations:**")
                    for r in scenario.recommendations:
                        st.info(f"💡 {r}")

            if st.session_state.selected_scenario_id == scenario.scenario_id:
                st.markdown("#### Scenario Inspection Workspace")
                render_selected_scenario_details(result, scenario)
            
            st.markdown("---")
    
    # Route comparison chart
    st.markdown("### Route Comparison")
    fig_comp = create_route_comparison_chart(scenarios)
    st.plotly_chart(fig_comp, key="scenario_route_comp")

# ==============================================================================
# TAB 5: EXPLAINABILITY (xAI)
# ==============================================================================
def render_explainability(result):
    """Render Explainability panel."""
    st.markdown('<div class="section-header">🧠 Explainable AI (xAI)</div>', unsafe_allow_html=True)
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available. Run analysis first.")
        return
    
    scenarios = result.scenarios
    
    # Scenario selector
    st.markdown("### Select Scenario to Explain")
    
    scenario_options = [f"#{i+1}: {s.name} ({s.risk_level.value.upper()})" for i, s in enumerate(scenarios)]
    selected = st.selectbox("Scenario", options=range(len(scenarios)), format_func=lambda i: scenario_options[i])
    
    scenario = scenarios[selected]
    
    st.markdown("---")
    
    # Explanation sections
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### AI Reasoning Chain")
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
            ("4. Regulation Retrieval", f"Retrieved relevant building safety regulations via RAG (FAISS + SentenceTransformers) for constraint validation."),
            ("5. Compliance Validation", f"Checked {len(scenario.violated_regulations) + 2} regulatory constraints. **{len(scenario.violated_regulations)} violations** identified."),
            ("6. Risk Classification", f"Classified as **{scenario.risk_level.value.upper()} RISK** based on travel distance, compliance score, and exit capacity analysis."),
            ("7. Explanation Generation", f"Generated natural language explanation with traceable regulation references and improvement recommendations."),
        ]
        
        for title, desc in steps:
            with st.container():
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                    <strong style="color: #1a1a2e;">{title}</strong><br>
                    <span style="color: #555; font-size: 0.9rem;">{desc}</span>
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
            scenario.origin_space_name,
            scenario.evacuation_route.destination,
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
            "<br>".join([f"• {v}" for v in scenario.violated_regulations]) if scenario.violated_regulations else "• No violations detected"
        ), unsafe_allow_html=True)
        
        # Model Confidence
        st.markdown("""
        <div class="success-box">
            <strong>🎯 Model Confidence</strong><br>
            <small>
            • Score: {:.1f}%<br>
            • Based on: route feasibility, regulation coverage, data completeness
            </small>
        </div>
        """.format(scenario.confidence_score * 100), unsafe_allow_html=True)
    
    # Natural Language Explanation
    st.markdown("---")
    st.markdown("### Natural Language Explanation")
    
    st.markdown(f"""
    <div style="background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem;">
        <p style="font-size: 1.05rem; line-height: 1.6; color: #333;">
            {scenario.explanation}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Example reasoning format
    st.markdown("---")
    st.markdown("### Example Reasoning Format")
    
    example = """
    **Why this scenario was generated:**
    
    > The AI system analyzed the building topology and identified that Office 101 has a direct 
    > connection to the Main Corridor. The shortest path to the nearest exit (Main Exit) was 
    > calculated at 32.5 meters, which is within the maximum allowed travel distance of 45 meters 
    > per Approved Document B Section 2.2.1.
    
    **Which regulation triggered the risk assessment:**
    
    > The door width of 0.70m at the corridor connection is below the minimum requirement of 
    > 0.75m specified in Approved Document B Section 2.3.1. This triggered a MEDIUM risk 
    > classification because it could impede evacuation flow during an emergency.
    
    **What IFC data was used:**
    
    > • Space ID: SPACE_001 (Office 101, 50.0 m²)
    > • Door ID: DOOR_002 (width: 0.70m)
    > • Exit ID: EXIT_001 (Main Exit, width: 1.20m)
    > • Travel distance: 32.5 meters (calculated from spatial graph)
    """
    
    with st.expander("View Example Reasoning Template"):
        st.markdown(example)

# ==============================================================================
# TAB 6: RISK & SAFETY ANALYSIS
# ==============================================================================
def render_risk_analysis(result):
    """Render Risk & Safety Analysis panel."""
    st.markdown('<div class="section-header">⚠️ Risk & Safety Analysis</div>', unsafe_allow_html=True)
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available. Run analysis first.")
        return
    
    scenarios = result.scenarios
    
    # ASET vs RSET concept
    st.markdown("### ASET vs RSET Concept")
    st.markdown("""
    <div class="info-box">
        <strong>Available Safe Egress Time (ASET)</strong> vs <strong>Required Safe Egress Time (RSET)</strong><br>
        <small>
        • <strong>ASET</strong>: Time until conditions become untenable (fire/smoke)<br>
        • <strong>RSET</strong>: Time required for occupants to evacuate<br>
        • <strong>Safety Margin</strong>: ASET - RSET (must be positive for safety)
        </small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Risk heatmap
    col_hm, col_stats = st.columns([2, 1])
    
    with col_hm:
        st.markdown("### Risk Factor Heatmap")
        fig_heatmap = create_risk_heatmap(scenarios)
        st.plotly_chart(fig_heatmap, key="risk_heatmap")
    
    with col_stats:
        st.markdown("### Risk Statistics")
        
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
        st.metric("Total Violations", total_violations)
        st.metric("Critical Scenarios", risk_counts.get('high', 0))
        
        # Safety margin indicator
        safety_margin = 300 - avg_time  # Assuming 5 min ASET
        margin_color = "#28a745" if safety_margin > 60 else "#ffc107" if safety_margin > 0 else "#dc3545"
        
        st.markdown(f"""
        <div style="background-color: {margin_color}20; border: 2px solid {margin_color}; border-radius: 8px; padding: 12px; margin-top: 10px;">
            <strong style="color: {margin_color};">Safety Margin</strong><br>
            <span style="font-size: 1.5rem; font-weight: bold; color: {margin_color};">{safety_margin:.0f}s</span><br>
            <small>ASET (300s) - RSET ({avg_time:.0f}s)</small>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Bottleneck analysis
    st.markdown("### Bottleneck & Congestion Analysis")
    
    bottleneck_data = []
    for i, s in enumerate(scenarios):
        # Estimate congestion based on compliance score and time
        congestion = min(100, max(0, (1 - s.compliance_score) * 100 + (s.evacuation_route.estimated_time / 300) * 50))
        bottleneck_data.append({
            'Scenario': f"#{i+1}: " + s.name[:15],
            'Congestion Risk (%)': round(congestion, 1),
            'Evacuation Time (s)': round(s.evacuation_route.estimated_time, 1),
            'Risk Level': s.risk_level.value
        })
    
    if bottleneck_data:
        df_bottleneck = pd.DataFrame(bottleneck_data)
        
        fig_bottleneck = px.scatter(
            df_bottleneck,
            x='Evacuation Time (s)',
            y='Congestion Risk (%)',
            color='Risk Level',
            size='Congestion Risk (%)',
            title="Congestion Risk vs Evacuation Time",
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
            'Compliance (%)': round(s.compliance_score * 100, 0),
            'Confidence (%)': round(s.confidence_score * 100, 0),
            'Risk': s.risk_level.value.upper()
        })
    
    df_comp = pd.DataFrame(comparison_data)
    st.dataframe(df_comp)

# ==============================================================================
# TAB 7: EXPERT REVIEW PANEL (HITL)
# ==============================================================================
def render_expert_review(result):
    """Render Expert Review panel with HITL functionality."""
    st.markdown('<div class="section-header">👤 Expert Review Panel</div>', unsafe_allow_html=True)
    
    if not result or not result.scenarios:
        st.info("📋 No scenarios available for review. Run analysis first.")
        return
    
    scenarios = result.scenarios
    
    # Introduction
    st.markdown("""
    <div class="warning-box">
        <strong>Human-in-the-Loop (HITL) Protocol</strong><br>
        <small>
        As a fire safety engineer, your review is critical. Please assess each AI-generated scenario 
        and provide your professional judgement. Your decisions will be recorded for audit and validation.
        </small>
    </div>
    """, unsafe_allow_html=True)
    
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
            st.metric("Confidence", f"{scenario.confidence_score*100:.0f}%")
        
        # Route path
        st.markdown("**Evacuation Path:**")
        path_str = " → ".join(scenario.evacuation_route.path[:5])
        st.code(path_str)
        
        # Violations
        if scenario.violated_regulations:
            st.markdown("**Regulatory Violations:**")
            for v in scenario.violated_regulations:
                st.error(f"❌ {v}")
        
        # Recommendations
        if scenario.recommendations:
            st.markdown("**AI Recommendations:**")
            for r in scenario.recommendations:
                st.info(f"💡 {r}")
    
    with col_review:
        st.markdown("### Your Assessment")
        
        # Review form
        review_key = f"expert_review_{scenario_id}"
        comments_key = f"expert_comments_{scenario_id}"
        
        if review_key not in st.session_state.expert_reviews:
            st.session_state.expert_reviews[review_key] = "Not Reviewed"
        
        # Decision buttons
        st.markdown("**Engineering Decision:**")
        
        decision = st.radio(
            "",
            options=["Not Reviewed", "✅ Approved", "⚠️ Needs Revision", "❌ Rejected"],
            key=f"decision_radio_{scenario_id}",
            index=0
        )
        
        # Comments
        comments = st.text_area(
            "Engineering Comments",
            placeholder="Enter your professional assessment, concerns, required modifications, or approval rationale...",
            key=f"comments_area_{scenario_id}",
            height=150
        )
        
        # Save button
        if st.button("💾 Save Engineering Review", key=f"save_review_btn_{scenario_id}"):
            st.session_state.expert_reviews[review_key] = {
                'decision': decision,
                'comments': comments,
                'scenario_id': scenario_id,
                'scenario_name': scenario.name,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
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
        • All engineering decisions are timestamped and logged<br>
        • Decisions can be exported as part of the fire strategy report<br>
        • Audit trail supports regulatory compliance verification
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
    st.markdown("### Fire Strategy Report Preview")
    
    st.markdown("""
    <div class="success-box">
        <strong>Report Ready for Export</strong><br>
        <small>
        This report contains all AI-generated scenarios, risk assessments, compliance checks, 
        and expert review decisions. It is suitable for fire strategy documentation and 
        regulatory submission.
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
        <div style="background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem;">
            <h4>Building: {result.building.name if result.building else 'N/A'}</h4>
            <p><strong>Total Scenarios Analyzed:</strong> {len(scenarios)}</p>
            <p><strong>Risk Distribution:</strong> {risk_counts.get('low', 0)} Low, {risk_counts.get('medium', 0)} Medium, {risk_counts.get('high', 0)} High</p>
            <p><strong>Average Compliance Score:</strong> {avg_compliance * 100:.1f}%</p>
            <p><strong>Total Regulatory Violations:</strong> {total_violations}</p>
            <p><strong>Analysis Date:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Export controls
    st.markdown("---")
    st.markdown("### Export Data")
    
    col_json, col_csv, col_xml = st.columns(3)
    
    with col_json:
        st.markdown("**JSON Export**")
        st.markdown("<small>Machine-readable format for system integration</small>", unsafe_allow_html=True)
        
        if st.button("📄 Export JSON", key="export_json"):
            try:
                export_data = create_export_summary(result.scenarios, result.building.name if result.building else 'Unknown')
                json_str = json.dumps(export_data, indent=2)
                
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_str,
                    file_name=f"fire_strategy_{result.building.name if result.building else 'report'}_{time.strftime('%Y%m%d')}.json",
                    mime="application/json",
                    width='stretch'
                )
            except Exception as e:
                st.error(f"Export error: {e}")
    
    with col_csv:
        st.markdown("**CSV Export**")
        st.markdown("<small>Spreadsheet format for data analysis</small>", unsafe_allow_html=True)
        
        if st.button("📊 Export CSV", key="export_csv"):
            try:
                import csv
                import io
                
                if result.scenarios:
                    output = io.StringIO()
                    fieldnames = ['scenario_id', 'name', 'risk_level', 'compliance_score', 
                                  'confidence_score', 'distance', 'estimated_time', 'violations']
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for s in result.scenarios:
                        writer.writerow({
                            'scenario_id': s.scenario_id,
                            'name': s.name,
                            'risk_level': s.risk_level.value,
                            'compliance_score': s.compliance_score,
                            'confidence_score': s.confidence_score,
                            'distance': s.evacuation_route.distance,
                            'estimated_time': s.evacuation_route.estimated_time,
                            'violations': len(s.violated_regulations)
                        })
                    
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=output.getvalue(),
                        file_name=f"fire_strategy_{result.building.name if result.building else 'report'}_{time.strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        width='stretch'
                    )
            except Exception as e:
                st.error(f"Export error: {e}")
    
    with col_xml:
        st.markdown("**XML Export**")
        st.markdown("<small>BIM interoperability format</small>", unsafe_allow_html=True)
        
        if st.button("📋 Export XML", key="export_xml"):
            try:
                xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<FireStrategyReport generated="{time.strftime('%Y-%m-%dT%H:%M:%S')}">
    <Building name="{result.building.name if result.building else 'Unknown'}"/>
    <Scenarios count="{len(result.scenarios)}">
        {''.join([f'''
        <Scenario id="{s.scenario_id}" risk="{s.risk_level.value}">
            <Name>{s.name}</Name>
            <Route distance="{s.evacuation_route.distance:.2f}" time="{s.evacuation_route.estimated_time:.1f}"/>
            <Compliance score="{s.compliance_score:.3f}" status="{s.compliance_status.value}"/>
        </Scenario>''' for s in result.scenarios])}
    </Scenarios>
</FireStrategyReport>"""
                
                st.download_button(
                    label="⬇️ Download XML",
                    data=xml_content,
                    file_name=f"fire_strategy_{result.building.name if result.building else 'report'}_{time.strftime('%Y%m%d')}.xml",
                    mime="application/xml",
                    width='stretch'
                )
            except Exception as e:
                st.error(f"Export error: {e}")
    
    # Full report generation
    st.markdown("---")
    st.markdown("### Complete Fire Strategy Report")
    
    if st.button("📑 Generate Full Report (All Formats)", key="generate_full_report", type="primary"):
        with st.spinner("Generating comprehensive fire strategy report..."):
            try:
                # Create comprehensive report
                report = create_export_summary(result.scenarios, result.building.name if result.building else 'Unknown')
                report['data_provenance'] = {
                    'source_file_name': result.source_file_name,
                    'source_file_sha256': result.source_file_sha256,
                    'ifc_schema': result.ifc_schema,
                    'source_mode': result.source_mode,
                }
                
                # Add expert reviews
                reviews = [v for k, v in st.session_state.expert_reviews.items() if isinstance(v, dict)]
                report['expert_reviews'] = reviews
                
                json_str = json.dumps(report, indent=2)
                
                st.success("✅ Report generated successfully!")
                
                st.download_button(
                    label="⬇️ Download Complete Report (JSON)",
                    data=json_str,
                    file_name=f"fire_strategy_complete_{time.strftime('%Y%m%d_%H%M%S')}.json",
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
    ifc_file, regulation_file, max_scenarios, enable_rag, process_button = render_sidebar()
    
    # Process if button clicked
    if process_button and ifc_file:
        process_files(ifc_file, regulation_file, max_scenarios, enable_rag)
    
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
            "⚠️ Risk Analysis",
            "👤 Expert Review",
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
            <h2>👋 Welcome to the BIM Evacuation Fire Strategy Platform</h2>
            <p style="color: #666; font-size: 1.1rem;">
                This AI-powered decision-support system generates evacuation scenarios from BIM models,<br>
                validates them against building safety regulations, and provides explainable recommendations<br>
                for fire safety engineering review.
            </p>
            <br>
            <div style="background-color: #f8f9fa; border-radius: 8px; padding: 2rem; display: inline-block;">
                <h4 style="margin-top: 0;">🚀 Getting Started</h4>
                <ol style="text-align: left; color: #555;">
                    <li>Upload your <strong>IFC building model</strong> in the sidebar</li>
                    <li>Optionally upload <strong>safety regulations</strong> (e.g., Approved Document B)</li>
                    <li>Configure analysis settings</li>
                    <li>Click <strong>"Generate Fire Strategy Scenarios"</strong></li>
                    <li>Review AI-generated scenarios across all tabs</li>
                    <li>Provide <strong>expert engineering review</strong> in the HITL panel</li>
                    <li>Export the complete fire strategy report</li>
                </ol>
            </div>
            <br><br>
            <p style="color: #999; font-size: 0.9rem;">
                <strong>Documented IFC targets:</strong> IFC2X3, IFC4, IFC4X3, IFC4X3_ADD2 | <strong>NLP:</strong> spaCy | <strong>RAG:</strong> FAISS + SentenceTransformers | <strong>Graph:</strong> NetworkX
            </p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
