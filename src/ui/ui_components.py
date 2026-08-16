"""
UI components and visualization helpers for the Streamlit interface.
"""
import html

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from src.utils.helpers import RiskLevel, ComplianceStatus
from src.scenario.scenario_generator import EvacuationScenario
from src.ui.theme import ACCENT, RISK_COLORS, STATUS_COLORS
from src.utils.model_transparency import ACADEMIC_USE_NOTICE, screening_index_semantics


def render_metric_card(title: str, value: str, subtitle: str = "", color: str = ACCENT):
    """Render a metric card with custom styling."""
    safe_title = html.escape(str(title))
    safe_value = html.escape(str(value))
    safe_subtitle = html.escape(str(subtitle))
    st.markdown(f"""
    <div class="metric-card" style="--metric-accent:{color};">
        <p class="metric-card__label">{safe_title}</p>
        <p class="metric-card__value">{safe_value}</p>
        {f'<p class="metric-card__subtitle">{safe_subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def get_risk_color(risk_level: RiskLevel) -> str:
    """Get color for risk level."""
    colors = {
        RiskLevel.LOW: RISK_COLORS["low"],
        RiskLevel.MEDIUM: RISK_COLORS["medium"],
        RiskLevel.HIGH: RISK_COLORS["high"],
    }
    return colors.get(risk_level, STATUS_COLORS["unknown"])


def get_risk_badge(risk_level: RiskLevel) -> str:
    """Get a styled screening-priority badge."""
    color = get_risk_color(risk_level)
    return (
        f'<span style="background:{color};color:white;padding:5px 12px;'
        f'border-radius:999px;font-size:.75rem;font-weight:700;text-transform:uppercase;">'
        f'{risk_level.value} priority</span>'
    )


def get_compliance_badge(status: ComplianceStatus) -> str:
    """Describe the outcome of implemented prototype checks without legal claims."""
    colors = {
        ComplianceStatus.COMPLIANT: (STATUS_COLORS["pass"], "✓ Checks Passed"),
        ComplianceStatus.NON_COMPLIANT: (STATUS_COLORS["fail"], "✗ Check Findings"),
        ComplianceStatus.PARTIAL: (STATUS_COLORS["warn"], "◐ Partial Checks"),
        ComplianceStatus.REQUIRES_REVIEW: (STATUS_COLORS["review"], "⚠ Review Required"),
        ComplianceStatus.INSUFFICIENT_DATA: (STATUS_COLORS["insufficient"], "◌ Insufficient Evidence"),
        ComplianceStatus.UNKNOWN: (STATUS_COLORS["unknown"], "? Unknown"),
    }
    color, label = colors.get(status, (STATUS_COLORS["unknown"], "? Unknown"))
    return (
        f'<span style="background:{color};color:white;padding:5px 12px;'
        f'border-radius:999px;font-size:.75rem;font-weight:700;">{label}</span>'
    )


def get_check_outcome_label(status: ComplianceStatus) -> str:
    """Return plain text for the implemented-check outcome."""
    return {
        ComplianceStatus.COMPLIANT: "Checks Passed",
        ComplianceStatus.NON_COMPLIANT: "Check Findings",
        ComplianceStatus.PARTIAL: "Partial Checks",
        ComplianceStatus.REQUIRES_REVIEW: "Review Required",
        ComplianceStatus.INSUFFICIENT_DATA: "Insufficient Evidence",
        ComplianceStatus.UNKNOWN: "Unknown",
    }.get(status, "Unknown")


def create_risk_pie_chart(scenarios: List[EvacuationScenario]) -> go.Figure:
    """Create the backward-compatible screening-priority distribution chart."""
    risk_counts = {'low': 0, 'medium': 0, 'high': 0}
    for s in scenarios:
        risk_counts[s.risk_level.value] = risk_counts.get(s.risk_level.value, 0) + 1
    
    labels = [k.upper() for k in risk_counts.keys()]
    values = list(risk_counts.values())
    
    fig = px.pie(
        values=values,
        names=labels,
        title="Screening Priority Distribution",
        color=labels,
        color_discrete_map={
            'LOW': RISK_COLORS['low'],
            'MEDIUM': RISK_COLORS['medium'],
            'HIGH': RISK_COLORS['high'],
        },
        hole=0.4
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def create_scenario_bar_chart(scenarios: List[EvacuationScenario]) -> go.Figure:
    """Compare evidence confidence with the implemented-check pass rate."""
    df = pd.DataFrame([
        {
            'Scenario': f"#{i+1}: " + (s.name[:25] + '...' if len(s.name) > 25 else s.name),
            'Evidence Confidence': s.confidence_score * 100,
            'Implemented Checks Passed': s.compliance_score * 100,
            'Screening Priority': s.risk_level.value,
        }
        for i, s in enumerate(scenarios)
    ])
    
    fig = px.bar(
        df,
        x='Scenario',
        y=['Evidence Confidence', 'Implemented Checks Passed'],
        barmode='group',
        title="Evidence Confidence vs Implemented Checks Passed",
        color_discrete_map={
            'Evidence Confidence': ACCENT,
            'Implemented Checks Passed': RISK_COLORS['medium'],
        },
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=-0.3)
    )
    return fig


def create_route_comparison_chart(scenarios: List[EvacuationScenario]) -> go.Figure:
    """Create route distance/time comparison chart."""
    df = pd.DataFrame([
        {
            'Scenario': f"#{i+1}: " + (s.name[:20] + '...' if len(s.name) > 20 else s.name),
            'Distance (m)': s.evacuation_route.distance,
            'Time (s)': s.evacuation_route.estimated_time,
            'Risk': s.risk_level.value
        }
        for i, s in enumerate(scenarios)
    ])
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Evacuation Distance', 'Evacuation Time'),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    bar_colors = [RISK_COLORS.get(r, STATUS_COLORS['unknown']) for r in df['Risk']]
    
    fig.add_trace(
        go.Bar(x=df['Scenario'], y=df['Distance (m)'], marker_color=bar_colors, name='Distance'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=df['Scenario'], y=df['Time (s)'], marker_color=bar_colors, name='Time'),
        row=1, col=2
    )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def create_network_graph_viz(building_data) -> go.Figure:
    """Create interactive network graph visualization."""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    positions: Dict[str, tuple] = {}

    if getattr(building_data, "spaces", None):
        for i, (space_id, space) in enumerate(building_data.spaces.items()):
            try:
                if getattr(space, "bounding_box", None):
                    minimum, maximum = space.bounding_box
                    position = (
                        (minimum.x + maximum.x) / 2,
                        (minimum.y + maximum.y) / 2,
                    )
                else:
                    position = (i * 2, 0)
                positions[space_id] = position
                nodes.append({
                    "id": space_id,
                    "label": space.name,
                    "type": "space",
                    "x": position[0],
                    "y": position[1],
                    "size": min(max(getattr(space, "area", 0) / 10, 8), 28)
                })
            except Exception:
                continue

    if getattr(building_data, "exits", None):
        for i, (exit_id, exit_door) in enumerate(building_data.exits.items()):
            try:
                position = (exit_door.location.x, exit_door.location.y)
                positions[exit_id] = position
                nodes.append({
                    "id": exit_id,
                    "label": exit_door.name,
                    "type": "exit",
                    "x": position[0],
                    "y": position[1],
                    "size": 20
                })
            except Exception:
                continue

    for door_id, door in getattr(building_data, "doors", {}).items():
        if door_id in getattr(building_data, "exits", {}):
            continue
        position = (door.location.x, door.location.y)
        positions[door_id] = position
        nodes.append({
            "id": door_id,
            "label": door.name,
            "type": "door",
            "x": position[0],
            "y": position[1],
            "size": 8,
        })
        for space_id in getattr(door, "connected_spaces", []):
            if space_id in positions:
                edges.append({"from": positions[space_id], "to": position})

    for exit_id, exit_door in getattr(building_data, "exits", {}).items():
        for space_id in getattr(exit_door, "connected_spaces", []):
            if space_id in positions and exit_id in positions:
                edges.append({"from": positions[space_id], "to": positions[exit_id]})

    node_df = pd.DataFrame(nodes)

    fig = go.Figure()

    # If no nodes or missing expected columns, return an empty plot with a helpful message
    if node_df.empty or "type" not in node_df.columns:
        fig.update_layout(
            title="Building Connectivity Graph",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=300,
            annotations=[
                dict(
                    text="No building topology data available.",
                    showarrow=False,
                    x=0.5,
                    y=0.5,
                    xref='paper',
                    yref='paper'
                )
            ]
        )
        return fig

    edge_x: List[float] = []
    edge_y: List[float] = []
    for edge in edges:
        edge_x.extend([edge["from"][0], edge["to"][0], None])
        edge_y.extend([edge["from"][1], edge["to"][1], None])
    if edge_x:
        fig.add_trace(go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1, color="#adb5bd"),
            hoverinfo="skip",
            showlegend=False,
        ))

    colors = {
        "space": ACCENT,
        "exit": RISK_COLORS["low"],
        "door": RISK_COLORS["medium"],
    }

    # Add a scatter trace for each node type
    for node_type in node_df["type"].unique():
        subset = node_df[node_df["type"] == node_type]
        show_labels = len(node_df) <= 35 or node_type == "exit"
        fig.add_trace(go.Scatter(
            x=subset["x"],
            y=subset["y"],
            mode='markers+text' if show_labels else 'markers',
            name=node_type.capitalize(),
            text=subset["label"],
            textposition='top center',
            marker=dict(
                size=subset["size"],
                color=colors.get(node_type, STATUS_COLORS["unknown"]),
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{text}</b><br>Type: ' + node_type.capitalize() + '<extra></extra>'
        ))

    # Configure the layout
    fig.update_layout(
        title="Building Connectivity Graph",
        showlegend=True,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        hovermode="closest",
    )
    return fig


def create_risk_heatmap(scenarios: List[EvacuationScenario]) -> go.Figure:
    """Create a 0-3 screening-indicator heatmap for scenarios."""
    data = []
    for i, s in enumerate(scenarios):
        risk_value = {'low': 1, 'medium': 2, 'high': 3}.get(s.risk_level.value, 0)
        data.append({
            'Scenario': f"#{i+1}: " + (s.name[:15] + '...' if len(s.name) > 15 else s.name),
            'Distance Indicator': min(s.evacuation_route.distance / 45, 1) * 3,
            'Time Indicator': min(s.evacuation_route.estimated_time / 150, 1) * 3,
            'Check-Finding Indicator': (1 - s.compliance_score) * 3,
            'Overall Priority': risk_value,
        })
    
    df = pd.DataFrame(data)
    
    fig = px.imshow(
        df.set_index('Scenario').T,
        title="Screening Indicator Heatmap",
        color_continuous_scale=[
            RISK_COLORS['low'],
            RISK_COLORS['medium'],
            RISK_COLORS['high'],
        ],
        aspect='auto'
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    return fig


def render_scenario_card(scenario: EvacuationScenario, index: int):
    """Render a scenario card with full details."""
    risk_color = get_risk_color(scenario.risk_level)
    compliance_color = {
        ComplianceStatus.COMPLIANT: STATUS_COLORS['pass'],
        ComplianceStatus.NON_COMPLIANT: STATUS_COLORS['fail'],
        ComplianceStatus.PARTIAL: STATUS_COLORS['warn'],
        ComplianceStatus.REQUIRES_REVIEW: STATUS_COLORS['review'],
        ComplianceStatus.INSUFFICIENT_DATA: STATUS_COLORS['insufficient'],
        ComplianceStatus.UNKNOWN: STATUS_COLORS['unknown'],
    }.get(scenario.compliance_status, STATUS_COLORS['unknown'])
    
    with st.container():
        st.markdown(f"""
        <div class="scenario-card" style="--scenario-accent:{risk_color};">
            <span class="scenario-kicker">Scenario #{index + 1}</span>
            <h3>{html.escape(str(scenario.name))}</h3>
            <p class="scenario-card__meta">
                <span style="background:{risk_color};color:#fff;padding:4px 10px;border-radius:999px;font-weight:700;">
                    {scenario.risk_level.value.upper()} PRIORITY
                </span>
                <span style="background:{compliance_color};color:#fff;padding:4px 10px;border-radius:999px;font-weight:700;">
                    {get_check_outcome_label(scenario.compliance_status)}
                </span>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Distance", f"{scenario.evacuation_route.distance:.1f}m")
        with col2:
            st.metric("Time", f"{scenario.evacuation_route.estimated_time:.1f}s")
        with col3:
            st.metric("Checks Passed", f"{scenario.compliance_score * 100:.0f}%")
        with col4:
            st.metric("Evidence Confidence", f"{scenario.confidence_score * 100:.0f}%")


def render_explanation_panel(scenario: EvacuationScenario):
    """Render explainability panel for a scenario."""
    st.markdown("### 🧠 Deterministic Decision Trace")
    
    # Reasoning steps
    steps = [
        f"1. **Origin Analysis**: Selected '{scenario.origin_space_name}' as origin point",
        f"2. **Route Calculation**: Computed shortest path to nearest exit ({scenario.evacuation_route.distance:.1f}m)",
        f"3. **Implemented Checks**: Evaluated {len(scenario.violated_regulations) + 2} prototype constraints",
        f"4. **Screening Priority**: Classified as **{scenario.risk_level.value.upper()}** using the full deterministic factor set",
        f"5. **Evidence Confidence**: {scenario.confidence_score * 100:.1f}% based on IFC measurement and route-source quality"
    ]
    
    for step in steps:
        st.markdown(step)
    
    # IFC Data Used
    st.markdown("### 📊 IFC Data Used")
    st.markdown(f"""
    - **Origin Element/Space**: {scenario.origin_space_name} (ID: {scenario.origin_space_id})
    - **Destination**: Exit via {scenario.evacuation_route.destination}
    - **Path Length**: {len(scenario.evacuation_route.path)} nodes
    - **Travel Distance**: {scenario.evacuation_route.distance:.2f} meters
    - **Estimated Time**: {scenario.evacuation_route.estimated_time:.1f} seconds
    """)
    
    # Regulation Triggers
    if scenario.violated_regulations:
        st.markdown("### ⚠️ Prototype Check Findings")
        for reg in scenario.violated_regulations:
            st.error(f"**{reg}**: This finding contributed to the screening-priority classification")
    else:
        st.info("No conflict was detected by the active prototype checks. This does not establish statutory compliance or fire safety.")
    
    # Natural Language Explanation
    st.markdown("### 📝 Natural Language Explanation")
    st.info(scenario.explanation)


def render_expert_review_controls(scenario: EvacuationScenario, scenario_id: str):
    """Render expert review controls for a scenario."""
    st.markdown("### 👤 Research Review Record")
    
    # Review status
    review_key = f"review_status_{scenario_id}"
    comments_key = f"review_comments_{scenario_id}"
    
    if review_key not in st.session_state:
        st.session_state[review_key] = "Not Reviewed"
    if comments_key not in st.session_state:
        st.session_state[comments_key] = ""
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        status = st.radio(
            "Decision",
            options=["Not Reviewed", "✓ Accepted for research follow-up", "⚠ Needs Revision", "✗ Rejected"],
            key=review_key,
            index=0 if st.session_state[review_key] == "Not Reviewed" else 
                  ["Not Reviewed", "✓ Accepted for research follow-up", "⚠ Needs Revision", "✗ Rejected"].index(st.session_state[review_key])
        )
    
    with col2:
        comments = st.text_area(
            "Review Comments",
            placeholder="Record research assessment, evidence concerns, or recommended follow-up...",
            key=comments_key,
            value=st.session_state[comments_key]
        )
    
    if st.button("💾 Save Review", key=f"save_review_{scenario_id}"):
        st.session_state[review_key] = status
        st.session_state[comments_key] = comments
        st.success(f"Review saved: {status}")
    
    # Show review history
    if status != "Not Reviewed":
        safe_status = html.escape(str(status))
        safe_comments = html.escape(str(comments)) if comments else "No comments"
        st.markdown(f"""
        <div style="background-color: var(--app-panel, #f8f9fa); color: var(--app-text, #222); padding: 10px; border-radius: 5px; margin-top: 10px;">
            <strong>Current Status:</strong> {safe_status}<br>
            <strong>Comments:</strong> {safe_comments}
        </div>
        """, unsafe_allow_html=True)


def create_export_summary(scenarios: List[EvacuationScenario], building_name: str) -> Dict[str, Any]:
    """Create exportable summary report."""
    risk_counts = {'low': 0, 'medium': 0, 'high': 0}
    for s in scenarios:
        risk_counts[s.risk_level.value] = risk_counts.get(s.risk_level.value, 0) + 1
    
    total_violations = sum(len(s.violated_regulations) for s in scenarios)
    avg_compliance = sum(s.compliance_score for s in scenarios) / len(scenarios) if scenarios else 0
    avg_confidence = sum(s.confidence_score for s in scenarios) / len(scenarios) if scenarios else 0
    
    return {
        "report_title": "BIM Evacuation Screening Evidence Report",
        "report_type": "research_screening_evidence_not_approval",
        "academic_use_notice": ACADEMIC_USE_NOTICE,
        "score_semantics": screening_index_semantics(),
        "generated_for": building_name,
        "total_scenarios": len(scenarios),
        "screening_priority_distribution": risk_counts,
        "total_prototype_check_findings": total_violations,
        "average_implemented_checks_passed": round(avg_compliance, 3),
        "average_evidence_confidence": round(avg_confidence, 3),
        "executive_summary": f"""
            This report presents {len(scenarios)} evacuation scenarios generated from BIM analysis.
            Screening-Priority Distribution: {risk_counts.get('low', 0)} Low, {risk_counts.get('medium', 0)} Medium, {risk_counts.get('high', 0)} High.
            Average Implemented Checks Passed: {avg_compliance * 100:.1f}%. Average Evidence Confidence: {avg_confidence * 100:.1f}%.
            All scenarios require qualified review. A lower screening priority or the absence of detected conflicts does not establish safety or statutory compliance.
        """,
    }
