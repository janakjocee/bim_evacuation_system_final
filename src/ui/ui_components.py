"""
UI components and visualization helpers for the Streamlit interface.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from src.utils.helpers import RiskLevel, ComplianceStatus
from src.scenario.scenario_generator import EvacuationScenario


def render_metric_card(title: str, value: str, subtitle: str = "", color: str = "#1f77b4"):
    """Render a metric card with custom styling."""
    st.markdown(f"""
    <div style="
        background-color: var(--app-panel, #f8f9fa);
        border-left: 5px solid {color};
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    ">
        <p style="margin: 0; color: var(--app-muted, #666); font-size: 0.85rem; text-transform: uppercase;">{title}</p>
        <p style="margin: 0; color: var(--app-heading, #333); font-size: 1.8rem; font-weight: bold;">{value}</p>
        {f'<p style="margin: 0; color: var(--app-muted, #777); font-size: 0.8rem;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def get_risk_color(risk_level: RiskLevel) -> str:
    """Get color for risk level."""
    colors = {
        RiskLevel.LOW: "#28a745",
        RiskLevel.MEDIUM: "#ffc107",
        RiskLevel.HIGH: "#dc3545"
    }
    return colors.get(risk_level, "#6c757d")


def get_risk_badge(risk_level: RiskLevel) -> str:
    """Get styled risk badge HTML."""
    color = get_risk_color(risk_level)
    return (
        f'<span style="background:{color};color:white;padding:5px 12px;'
        f'border-radius:999px;font-size:.75rem;font-weight:700;text-transform:uppercase;">'
        f'{risk_level.value}</span>'
    )


def get_compliance_badge(status: ComplianceStatus) -> str:
    """Get styled compliance badge HTML."""
    colors = {
        ComplianceStatus.COMPLIANT: ("#28a745", "✓ Compliant"),
        ComplianceStatus.NON_COMPLIANT: ("#dc3545", "✗ Non-Compliant"),
        ComplianceStatus.PARTIAL: ("#ffc107", "◐ Partial")
    }
    color, label = colors.get(status, ("#6c757d", "? Unknown"))
    return (
        f'<span style="background:{color};color:white;padding:5px 12px;'
        f'border-radius:999px;font-size:.75rem;font-weight:700;">{label}</span>'
    )


def create_risk_pie_chart(scenarios: List[EvacuationScenario]) -> go.Figure:
    """Create risk distribution pie chart."""
    risk_counts = {'low': 0, 'medium': 0, 'high': 0}
    for s in scenarios:
        risk_counts[s.risk_level.value] = risk_counts.get(s.risk_level.value, 0) + 1
    
    colors = ['#28a745', '#ffc107', '#dc3545']
    labels = [k.upper() for k in risk_counts.keys()]
    values = list(risk_counts.values())
    
    fig = px.pie(
        values=values,
        names=labels,
        title="Risk Level Distribution",
        color=labels,
        color_discrete_map={
            'LOW': '#28a745',
            'MEDIUM': '#ffc107',
            'HIGH': '#dc3545'
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
    """Create scenario confidence bar chart."""
    df = pd.DataFrame([
        {
            'Scenario': f"#{i+1}: " + (s.name[:25] + '...' if len(s.name) > 25 else s.name),
            'Confidence': s.confidence_score * 100,
            'Compliance': s.compliance_score * 100,
            'Risk': s.risk_level.value
        }
        for i, s in enumerate(scenarios)
    ])
    
    fig = px.bar(
        df,
        x='Scenario',
        y=['Confidence', 'Compliance'],
        barmode='group',
        title="Scenario Confidence vs Compliance Scores",
        color_discrete_map={'Confidence': '#1f77b4', 'Compliance': '#ff7f0e'}
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
    
    colors = {'low': '#28a745', 'medium': '#ffc107', 'high': '#dc3545'}
    bar_colors = [colors.get(r, '#6c757d') for r in df['Risk']]
    
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

    colors = {"space": "#1f77b4", "exit": "#28a745", "door": "#ff7f0e"}

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
                color=colors.get(node_type, "#6c757d"),
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
    """Create risk heatmap for scenarios."""
    data = []
    for i, s in enumerate(scenarios):
        risk_value = {'low': 1, 'medium': 2, 'high': 3}.get(s.risk_level.value, 0)
        data.append({
            'Scenario': f"#{i+1}: " + (s.name[:15] + '...' if len(s.name) > 15 else s.name),
            'Distance Risk': min(s.evacuation_route.distance / 45, 3),
            'Time Risk': min(s.evacuation_route.estimated_time / 150, 3),
            'Compliance Risk': (1 - s.compliance_score) * 3,
            'Overall Risk': risk_value
        })
    
    df = pd.DataFrame(data)
    
    fig = px.imshow(
        df.set_index('Scenario').T,
        title="Risk Factor Heatmap",
        color_continuous_scale=['#28a745', '#ffc107', '#dc3545'],
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
        ComplianceStatus.COMPLIANT: '#28a745',
        ComplianceStatus.NON_COMPLIANT: '#dc3545',
        ComplianceStatus.PARTIAL: '#ffc107'
    }.get(scenario.compliance_status, '#6c757d')
    
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #e0e0e0;
            border-left: 5px solid {risk_color};
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            background-color: var(--app-panel-strong, white);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <h4 style="margin: 0; color: var(--app-heading, #333);">#{index + 1} {scenario.name}</h4>
                <div>
                    <span style="background-color: {risk_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; margin-right: 8px;">
                        {scenario.risk_level.value.upper()}
                    </span>
                    <span style="background-color: {compliance_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;">
                        {scenario.compliance_status.value}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Distance", f"{scenario.evacuation_route.distance:.1f}m")
        with col2:
            st.metric("Time", f"{scenario.evacuation_route.estimated_time:.1f}s")
        with col3:
            st.metric("Compliance", f"{scenario.compliance_score * 100:.0f}%")
        with col4:
            st.metric("Confidence", f"{scenario.confidence_score * 100:.0f}%")


def render_explanation_panel(scenario: EvacuationScenario):
    """Render explainability panel for a scenario."""
    st.markdown("### 🧠 AI Reasoning Chain")
    
    # Reasoning steps
    steps = [
        f"1. **Origin Analysis**: Selected '{scenario.origin_space_name}' as origin point",
        f"2. **Route Calculation**: Computed shortest path to nearest exit ({scenario.evacuation_route.distance:.1f}m)",
        f"3. **Compliance Check**: Validated against {len(scenario.violated_regulations) + 2} regulatory constraints",
        f"4. **Risk Assessment**: Classified as **{scenario.risk_level.value.upper()}** risk based on travel distance and compliance",
        f"5. **Confidence Score**: {scenario.confidence_score * 100:.1f}% based on route feasibility and regulation coverage"
    ]
    
    for step in steps:
        st.markdown(f"<div style='padding: 4px 0;'>{step}</div>", unsafe_allow_html=True)
    
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
        st.markdown("### ⚠️ Triggered Regulations")
        for reg in scenario.violated_regulations:
            st.error(f"**{reg}**: This constraint was violated, contributing to risk classification")
    else:
        st.success("✓ All regulatory constraints satisfied")
    
    # Natural Language Explanation
    st.markdown("### 📝 Natural Language Explanation")
    st.info(scenario.explanation)


def render_expert_review_controls(scenario: EvacuationScenario, scenario_id: str):
    """Render expert review controls for a scenario."""
    st.markdown("### 👤 Expert Review")
    
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
            options=["Not Reviewed", "✓ Approved", "⚠ Needs Revision", "✗ Rejected"],
            key=review_key,
            index=0 if st.session_state[review_key] == "Not Reviewed" else 
                  ["Not Reviewed", "✓ Approved", "⚠ Needs Revision", "✗ Rejected"].index(st.session_state[review_key])
        )
    
    with col2:
        comments = st.text_area(
            "Review Comments",
            placeholder="Enter engineering assessment, concerns, or recommendations...",
            key=comments_key,
            value=st.session_state[comments_key]
        )
    
    if st.button("💾 Save Review", key=f"save_review_{scenario_id}"):
        st.session_state[review_key] = status
        st.session_state[comments_key] = comments
        st.success(f"Review saved: {status}")
    
    # Show review history
    if status != "Not Reviewed":
        st.markdown(f"""
        <div style="background-color: var(--app-panel, #f8f9fa); color: var(--app-text, #222); padding: 10px; border-radius: 5px; margin-top: 10px;">
            <strong>Current Status:</strong> {status}<br>
            <strong>Comments:</strong> {comments if comments else 'No comments'}
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
        "report_title": "BIM Evacuation Fire Strategy Report",
        "generated_for": building_name,
        "total_scenarios": len(scenarios),
        "risk_distribution": risk_counts,
        "total_regulatory_violations": total_violations,
        "average_compliance_score": round(avg_compliance, 3),
        "average_confidence_score": round(avg_confidence, 3),
        "executive_summary": f"""
            This report presents {len(scenarios)} evacuation scenarios generated from BIM analysis.
            Risk Distribution: {risk_counts.get('low', 0)} Low, {risk_counts.get('medium', 0)} Medium, {risk_counts.get('high', 0)} High.
            Average Compliance: {avg_compliance * 100:.1f}%. Average Confidence: {avg_confidence * 100:.1f}%.
            {"All scenarios require engineering review." if risk_counts.get('high', 0) > 0 else "Scenarios meet basic safety requirements."}
        """,
        "scenarios": [s.to_dict() for s in scenarios]
    }
